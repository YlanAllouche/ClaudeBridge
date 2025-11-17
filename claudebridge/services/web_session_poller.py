"""
Web Session Poller for Claude.ai usage endpoint
Polls organization usage data to get real 5h/7d utilization in percentages
"""

import threading
import time
from typing import Any, Dict, Optional

import requests

from .logger import logger

# TODO: Detect when blocked by Cloudflare vs something else


class WebSessionPoller:
    def __init__(self, accounts_manager):
        self.accounts_manager = accounts_manager
        self.last_poll = {}
        self.usage_data = {}
        self.errors = {}
        self.polling_thread = None
        self.running = False
        self.poll_interval = 300
        self.error_cooloff_duration = 300  # 5 minutes cool-off after error
        self.last_error_time = {}  # Track when error first occurred
        self.last_retry_attempt_time = (
            {}
        )  # Track when we last tried to retry after error

    def start(self):
        if self.running:
            logger.warning("WebSessionPoller already running")
            return

        self.running = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        logger.info("WebSessionPoller started")

    def stop(self):
        self.running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=5)
        logger.info("WebSessionPoller stopped")

    def get_usage_data(self, account_id: str) -> Optional[Dict[str, Any]]:
        return self.usage_data.get(account_id)

    def get_error(self, account_id: str) -> Optional[str]:
        return self.errors.get(account_id)

    def get_error_since(self, account_id: str) -> Optional[int]:
        return self.last_error_time.get(account_id)

    def clear_error(self, account_id: str):
        if account_id in self.errors:
            del self.errors[account_id]
            if account_id in self.last_error_time:
                del self.last_error_time[account_id]
            logger.info(f"Cleared web session error for account {account_id}")

    def _mark_error(self, account_id: str, error_msg: str):
        current_time = int(time.time())

        if account_id not in self.errors:
            self.last_error_time[account_id] = current_time
            logger.trace(
                f"Web session error FIRST OCCURRED for account {account_id}: {error_msg}",
                error_since=current_time,
                cooloff_duration=self.error_cooloff_duration,
            )
        else:
            logger.trace(
                f"Web session error PERSISTS for account {account_id}: {error_msg}",
                error_since=self.last_error_time.get(account_id),
                will_retry_in_seconds=self.error_cooloff_duration
                - (current_time - self.last_error_time.get(account_id, 0)),
            )

        self.errors[account_id] = error_msg

        if account_id in self.usage_data:
            self.usage_data[account_id]["is_stale"] = True
            self.usage_data[account_id]["error"] = error_msg
            self.usage_data[account_id]["error_since"] = self.last_error_time[
                account_id
            ]
            logger.trace(
                f"Marked web session data as STALE for account {account_id}",
                last_update_age_seconds=current_time
                - self.usage_data[account_id].get("last_updated", 0),
            )
        else:
            logger.trace(
                f"No existing data to mark stale for account {account_id} (first poll failed)"
            )

    def _should_poll(self, account_id: str) -> bool:
        account = self.accounts_manager.get_account_by_id(account_id)
        if not account:
            return False

        if not account.get("web_session_key"):
            return False

        if not account.get("organization_uuid"):
            return False

        if account_id in self.errors:
            last_error_time = self.last_error_time.get(account_id, 0)
            current_time = int(time.time())
            time_since_error = current_time - last_error_time

            if time_since_error < self.error_cooloff_duration:
                return False

            logger.trace(
                f"Web session error cool-off expired for account {account_id}",
                time_since_error=time_since_error,
                cooloff_duration=self.error_cooloff_duration,
            )
            return True

        last_poll_time = self.last_poll.get(account_id, 0)
        if int(time.time()) - last_poll_time < self.poll_interval:
            return False

        return True

    def _poll_usage(self, account_id: str):
        account = self.accounts_manager.get_account_by_id(account_id)
        if not account:
            return

        session_key = account.get("web_session_key")
        org_uuid = account.get("organization_uuid")

        if not session_key or not org_uuid:
            return

        url = f"https://claude.ai/api/organizations/{org_uuid}/usage"
        headers = {
            "Cookie": f"sessionKey={session_key}",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        }

        try:
            logger.trace(
                f"Polling web session usage for account {account_id}",
                org_uuid=org_uuid,
                session_key_preview=session_key[:20] + "...",
            )
            response = requests.get(url, headers=headers, timeout=10)

            logger.trace(
                f"Web session poll response received",
                account_id=account_id,
                status_code=response.status_code,
                content_length=len(response.text),
            )

            if response.status_code == 403:
                error_msg = "Session expired or invalid (403 Forbidden)"
                self._mark_error(account_id, error_msg)
                logger.info(
                    f"Web session polling failed for account {account_id}: {error_msg}"
                )
                logger.trace(f"Web session 403 response body: {response.text}")
                return

            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}"
                self._mark_error(account_id, error_msg)
                logger.info(
                    f"Web session polling failed for account {account_id}: {error_msg}"
                )
                logger.trace(f"Web session error response body: {response.text}")
                return

            try:
                data = response.json()
                current_time = int(time.time())
                self.usage_data[account_id] = {
                    "five_hour": data.get("five_hour"),
                    "seven_day": data.get("seven_day"),
                    "seven_day_oauth_apps": data.get("seven_day_oauth_apps"),
                    "seven_day_opus": data.get("seven_day_opus"),
                    "last_updated": current_time,
                    "is_stale": False,
                    "error": None,
                }

                self.last_poll[account_id] = current_time

                # Clear error state on successful poll
                if account_id in self.errors:
                    del self.errors[account_id]
                if account_id in self.last_error_time:
                    del self.last_error_time[account_id]

                logger.trace(
                    f"Web session usage polled successfully for account {account_id}",
                    five_hour_util=data.get("five_hour", {}).get("utilization"),
                    seven_day_util=data.get("seven_day", {}).get("utilization"),
                    full_response=data,
                )

            except Exception as e:
                error_msg = f"JSON parse error: {str(e)}"
                self._mark_error(account_id, error_msg)
                logger.info(
                    f"Web session polling failed for account {account_id}: {error_msg}"
                )
                logger.trace(
                    f"Web session parse error - response text: {response.text}"
                )

        except requests.exceptions.Timeout:
            error_msg = "Request timeout"
            self._mark_error(account_id, error_msg)
            logger.info(
                f"Web session polling failed for account {account_id}: {error_msg}"
            )

        except Exception as e:
            error_msg = f"Network error: {str(e)}"
            self._mark_error(account_id, error_msg)
            logger.info(
                f"Web session polling failed for account {account_id}: {error_msg}"
            )
            logger.trace(f"Web session network error details: {str(e)}")

    def _polling_loop(self):
        while self.running:
            try:
                accounts = self.accounts_manager.get_all_accounts()
                logger.trace(
                    f"Web session polling loop tick - {len(accounts)} accounts to check"
                )

                for account in accounts:
                    account_id = account.get("account_id")
                    if not account_id:
                        continue

                    account_name = account.get("account_name", "unknown")

                    if self._should_poll(account_id):
                        logger.trace(
                            f"Web session polling SHOULD POLL for account {account_name}",
                            account_id=account_id,
                            has_key=bool(account.get("web_session_key")),
                            has_org_uuid=bool(account.get("organization_uuid")),
                            has_error=account_id in self.errors,
                        )
                        self._poll_usage(account_id)
                    else:
                        reason = "unknown"
                        if not account.get("web_session_key"):
                            reason = "no_session_key"
                        elif not account.get("organization_uuid"):
                            reason = "no_org_uuid"
                        elif account_id in self.errors:
                            reason = f"error_state: {self.errors[account_id]}"
                        elif (
                            int(time.time()) - self.last_poll.get(account_id, 0)
                            < self.poll_interval
                        ):
                            reason = "rate_limited"

                        logger.trace(
                            f"Web session polling SKIPPED for account {account_name}",
                            account_id=account_id,
                            reason=reason,
                        )

            except Exception as e:
                logger.error(f"Error in web session polling loop: {e}")
                logger.trace(
                    f"Web session polling loop error details: {e}", exc_info=True
                )

            time.sleep(60)
