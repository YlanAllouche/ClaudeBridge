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

    def clear_error(self, account_id: str):
        if account_id in self.errors:
            del self.errors[account_id]
            logger.info(f"Cleared web session error for account {account_id}")

    def _should_poll(self, account_id: str) -> bool:
        account = self.accounts_manager.get_account_by_id(account_id)
        if not account:
            return False

        if not account.get("web_session_key"):
            return False

        if not account.get("organization_uuid"):
            return False

        if account_id in self.errors:
            return False

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
            logger.debug(
                f"Polling web session usage for account {account_id}", org_uuid=org_uuid
            )
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 403:
                error_msg = "Session expired or invalid (403 Forbidden)"
                self.errors[account_id] = error_msg
                logger.info(
                    f"Web session polling failed for account {account_id}: {error_msg}"
                )
                logger.debug(f"Web session 403 response body: {response.text}")
                return

            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}"
                self.errors[account_id] = error_msg
                logger.info(
                    f"Web session polling failed for account {account_id}: {error_msg}"
                )
                logger.debug(f"Web session error response body: {response.text}")
                return

            try:
                data = response.json()
                self.usage_data[account_id] = {
                    "five_hour": data.get("five_hour"),
                    "seven_day": data.get("seven_day"),
                    "seven_day_oauth_apps": data.get("seven_day_oauth_apps"),
                    "seven_day_opus": data.get("seven_day_opus"),
                    "last_updated": int(time.time()),
                }

                self.last_poll[account_id] = int(time.time())

                if account_id in self.errors:
                    del self.errors[account_id]

                logger.trace(
                    f"Web session usage polled successfully for account {account_id}",
                    five_hour_util=data.get("five_hour", {}).get("utilization"),
                    seven_day_util=data.get("seven_day", {}).get("utilization"),
                    full_response=data,
                )

            except Exception as e:
                error_msg = f"JSON parse error: {str(e)}"
                self.errors[account_id] = error_msg
                logger.info(
                    f"Web session polling failed for account {account_id}: {error_msg}"
                )
                logger.debug(
                    f"Web session parse error - response text: {response.text}"
                )

        except requests.exceptions.Timeout:
            error_msg = "Request timeout"
            self.errors[account_id] = error_msg
            logger.info(
                f"Web session polling failed for account {account_id}: {error_msg}"
            )

        except Exception as e:
            error_msg = f"Network error: {str(e)}"
            self.errors[account_id] = error_msg
            logger.info(
                f"Web session polling failed for account {account_id}: {error_msg}"
            )
            logger.debug(f"Web session network error details: {str(e)}")

    def _polling_loop(self):
        while self.running:
            try:
                accounts = self.accounts_manager.get_all_accounts()

                for account in accounts:
                    account_id = account.get("account_id")
                    if not account_id:
                        continue

                    if self._should_poll(account_id):
                        self._poll_usage(account_id)

            except Exception as e:
                logger.error(f"Error in web session polling loop: {e}")

            time.sleep(60)
