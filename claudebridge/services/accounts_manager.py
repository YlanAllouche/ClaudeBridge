"""
Handles storage, retrieval, and lifecycle of OAuth accounts
"""

# NOTE: This mat still bear some of the previous multi-account setup

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import logger


class AccountsManager:
    def __init__(self, accounts_file: Optional[str] = None, oauth_manager=None):
        if accounts_file:
            self.accounts_file = accounts_file
        else:
            config_dir = Path.home() / ".config" / "claudebridge"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.accounts_file = str(config_dir / "accounts.json")

        self.accounts = {"accounts": []}
        self.oauth_manager = oauth_manager
        self.load_accounts()

    def load_accounts(self) -> Dict[str, Any]:
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, "r") as f:
                    self.accounts = json.load(f)

                    logger.info(f"Accounts loaded from {self.accounts_file}")
            except Exception as e:
                logger.error(f"Error loading accounts: {e}, using defaults")
                self.accounts = {"accounts": []}
        else:
            self.accounts = {"accounts": []}
            logger.info(f"No accounts file found, starting fresh")

        return self.accounts

    def save_accounts(self) -> None:
        try:
            with open(self.accounts_file, "w") as f:
                json.dump(self.accounts, f, indent=2)
            logger.info(f"Accounts saved to {self.accounts_file}")
        except Exception as e:
            logger.info(f"Error saving accounts: {e}")

    def get_all_accounts(self) -> List[Dict[str, Any]]:
        return self.accounts.get("accounts", [])

    def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        for account in self.accounts.get("accounts", []):
            if account.get("account_id") == account_id:
                return account
        return None

    def add_account(
        self,
        account_name: str,
        access_token: str,
        refresh_token: str,
        expires_at: int,
        account_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        account = {
            "account_id": str(uuid.uuid4()),
            "account_name": account_name,
            "priority": len(self.accounts.get("accounts", [])) + 1,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "connected": True,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "last_success_at": None,
            "last_failure_at": None,
            "last_ooq_5h_at": None,
            "last_ooq_7d_at": None,
            "ooq_5h_status": "allowed",
            "ooq_5h_reset_at": None,
            "ooq_7d_status": "allowed",
            "ooq_7d_reset_at": None,
            "web_session_key": None,
            "web_session_key_error": None,
            "web_session_key_updated_at": None,
        }

        # TODO: Need to confirm that everyone gets the same fields - especially organization (required to build the websession url to poll)
        if account_metadata:
            account["metadata"] = account_metadata

            if "account" in account_metadata:
                account["anthropic_account_uuid"] = account_metadata["account"].get(
                    "uuid"
                )
                account["email"] = account_metadata["account"].get("email_address")

            if "organization" in account_metadata:
                account["organization_uuid"] = account_metadata["organization"].get(
                    "uuid"
                )
                account["organization_name"] = account_metadata["organization"].get(
                    "name"
                )

        self.accounts["accounts"].append(account)
        self.save_accounts()

        logger.info(f"Added new account: {account_name} ({account['account_id']})")
        return account

    def update_account_tokens(
        self, account_id: str, access_token: str, refresh_token: str, expires_at: int
    ) -> bool:
        account = self.get_account_by_id(account_id)
        if not account:
            return False

        account["access_token"] = access_token
        account["refresh_token"] = refresh_token
        account["expires_at"] = expires_at
        account["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        account["connected"] = True

        self.save_accounts()
        logger.info(
            f"Updated tokens for account: {account['account_name']} ({account_id})"
        )
        return True

    def disconnect_account(self, account_id: str) -> bool:
        account = self.get_account_by_id(account_id)
        if not account:
            return False

        account["connected"] = False
        account["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        self.save_accounts()
        logger.info(f"Disconnected account: {account['account_name']} ({account_id})")
        return True

    def delete_account(self, account_id: str) -> bool:
        original_count = len(self.accounts["accounts"])
        self.accounts["accounts"] = [
            acc
            for acc in self.accounts["accounts"]
            if acc.get("account_id") != account_id
        ]

        if len(self.accounts["accounts"]) < original_count:
            self.save_accounts()
            logger.info(f"Deleted account: {account_id}")
            return True

        return False

    def update_account_name(self, account_id: str, new_name: str) -> bool:
        account = self.get_account_by_id(account_id)
        if not account:
            return False

        account["account_name"] = new_name
        account["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        self.save_accounts()
        logger.info(f"Updated account name to: {new_name} ({account_id})")
        return True

    # FIX: Single account system does not need a priority anymore
    def update_account_priority(self, account_id: str, priority: int) -> bool:
        account = self.get_account_by_id(account_id)
        if not account:
            return False

        account["priority"] = priority
        account["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        self.save_accounts()
        logger.info(f"Updated account priority to: {priority} ({account_id})")
        return True

    def get_active_account(self) -> Optional[Dict[str, Any]]:
        connected_accounts = [
            acc
            for acc in self.accounts.get("accounts", [])
            if acc.get("connected", False)
        ]

        if not connected_accounts:
            return None

        connected_accounts.sort(key=lambda x: x.get("priority", 999))
        return connected_accounts[0]

    def get_valid_access_token(self, account_id: Optional[str] = None) -> Optional[str]:
        if account_id:
            account = self.get_account_by_id(account_id)
            if not account:
                return None
            accounts_to_check = [account]
        else:
            active_account = self.get_active_account()
            if not active_account:
                return None
            accounts_to_check = [active_account]

        for account in accounts_to_check:
            if not account.get("connected", False):
                continue

            current_time = int(time.time())
            expires_at = account.get("expires_at", 0)

            if current_time < (expires_at - 300):
                return account.get("access_token")

            if self.oauth_manager and account.get("refresh_token"):
                try:
                    logger.debug(
                        f"Token expired for account {account['account_id']}, refreshing..."
                    )
                    new_tokens = self.oauth_manager.refresh_access_token(
                        account["refresh_token"]
                    )

                    self.update_account_tokens(
                        account_id=account["account_id"],
                        access_token=new_tokens["access_token"],
                        refresh_token=new_tokens["refresh_token"],
                        expires_at=new_tokens["expires_at"],
                    )

                    logger.info(f"Token refreshed for account {account['account_id']}")
                    return new_tokens["access_token"]
                except Exception as e:
                    logger.warning(
                        f"Failed to refresh token for account {account['account_id']}: {e}"
                    )
                    return None

        return None

    def is_any_account_connected(self) -> bool:
        return any(
            acc.get("connected", False) for acc in self.accounts.get("accounts", [])
        )

    def record_success(self, account_id: str) -> None:
        """Record successful request for an account"""
        account = self.get_account_by_id(account_id)
        if not account:
            return

        current_time = int(time.time())
        account["last_success_at"] = current_time
        account["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if account.get("ooq_5h_status") == "rejected":
            if current_time >= account.get("ooq_5h_reset_at", 0):
                account["ooq_5h_status"] = "allowed"
                account["ooq_5h_reset_at"] = None
                logger.info(f"Account {account_id} 5h quota restored")

        if account.get("ooq_7d_status") == "rejected":
            if current_time >= account.get("ooq_7d_reset_at", 0):
                account["ooq_7d_status"] = "allowed"
                account["ooq_7d_reset_at"] = None
                logger.info(f"Account {account_id} 7d quota restored")

        self.save_accounts()

    def record_failure(self, account_id: str) -> None:
        """Record failed request (non-quota) for an account"""
        account = self.get_account_by_id(account_id)
        if not account:
            return

        account["last_failure_at"] = int(time.time())
        account["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.save_accounts()

    def record_out_of_quota(self, account_id: str, response_headers: dict) -> None:
        """Record out-of-quota error and parse Anthropic headers"""
        account = self.get_account_by_id(account_id)
        if not account:
            logger.info(f"Cannot record OOQ for unknown account: {account_id}")
            return

        timestamp = int(time.time())

        ooq_5h_status = response_headers.get("anthropic-ratelimit-unified-5h-status")
        ooq_5h_reset = response_headers.get("anthropic-ratelimit-unified-5h-reset")

        if ooq_5h_status:
            account["ooq_5h_status"] = ooq_5h_status
            if ooq_5h_status == "rejected":
                account["last_ooq_5h_at"] = timestamp
                account["ooq_5h_reset_at"] = int(ooq_5h_reset) if ooq_5h_reset else None
                logger.warning(
                    f"Account {account_id} hit 5h quota limit",
                    reset_at=account["ooq_5h_reset_at"],
                )

        ooq_7d_status = response_headers.get("anthropic-ratelimit-unified-7d-status")
        ooq_7d_reset = response_headers.get("anthropic-ratelimit-unified-7d-reset")

        if ooq_7d_status:
            account["ooq_7d_status"] = ooq_7d_status
            if ooq_7d_status == "rejected":
                account["last_ooq_7d_at"] = timestamp
                account["ooq_7d_reset_at"] = int(ooq_7d_reset) if ooq_7d_reset else None
                logger.warning(
                    f"Account {account_id} hit 7d quota limit",
                    reset_at=account["ooq_7d_reset_at"],
                )

        account["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.save_accounts()

    def get_ooq_timer_status(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get OOQ timer status in UI"""
        account = self.get_account_by_id(account_id)
        if not account:
            return None

        current_time = int(time.time())
        result = {"account_id": account_id, "ooq_5h": None, "ooq_7d": None}

        if account.get("ooq_5h_status") == "rejected" and account.get(
            "ooq_5h_reset_at"
        ):
            time_remaining = account["ooq_5h_reset_at"] - current_time
            if time_remaining > 0:
                result["ooq_5h"] = {
                    "status": "countdown",
                    "seconds_remaining": time_remaining,
                    "reset_at": account["ooq_5h_reset_at"],
                }
            else:
                result["ooq_5h"] = {
                    "status": "ready",
                    "seconds_remaining": 0,
                    "reset_at": account["ooq_5h_reset_at"],
                }
        elif account.get("ooq_5h_status") == "allowed":
            result["ooq_5h"] = {"status": "allowed"}

        if account.get("ooq_7d_status") == "rejected" and account.get(
            "ooq_7d_reset_at"
        ):
            time_remaining = account["ooq_7d_reset_at"] - current_time
            if time_remaining > 0:
                result["ooq_7d"] = {
                    "status": "countdown",
                    "seconds_remaining": time_remaining,
                    "reset_at": account["ooq_7d_reset_at"],
                }
            else:
                result["ooq_7d"] = {
                    "status": "ready",
                    "seconds_remaining": 0,
                    "reset_at": account["ooq_7d_reset_at"],
                }
        elif account.get("ooq_7d_status") == "allowed":
            result["ooq_7d"] = {"status": "allowed"}

        return result

    def is_account_in_quota(self, account_id: str) -> bool:
        """Check if account can be used (ready/!OOQ)"""
        account = self.get_account_by_id(account_id)
        if not account or not account.get("connected", False):
            return False

        current_time = int(time.time())

        if account.get("ooq_5h_status") == "rejected":
            reset_at = account.get("ooq_5h_reset_at", 0)
            if current_time < reset_at:
                logger.debug(f"Account {account_id} still in 5h quota cooldown")
                return False

        if account.get("ooq_7d_status") == "rejected":
            reset_at = account.get("ooq_7d_reset_at", 0)
            if current_time < reset_at:
                logger.debug(f"Account {account_id} still in 7d quota cooldown")
                return False

        return True

    def update_web_session_key(
        self, account_id: str, session_key: Optional[str]
    ) -> bool:
        """Update web session key for an account"""
        account = self.get_account_by_id(account_id)
        if not account:
            return False

        old_session_key = account.get("web_session_key")
        account["web_session_key"] = session_key
        account["web_session_key_error"] = None
        account["web_session_key_updated_at"] = (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) if session_key else None
        )
        account["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        self.save_accounts()

        if session_key:
            action = "replaced" if old_session_key else "added"
            logger.info(
                f"Web session key {action} for account: {account['account_name']} ({account_id})"
            )
            logger.trace(
                f"Web session key updated",
                account_id=account_id,
                account_name=account["account_name"],
                key_preview=session_key[:20] + "...",
                has_org_uuid=bool(account.get("organization_uuid")),
            )
        else:
            logger.info(
                f"Web session key removed for account: {account['account_name']} ({account_id})"
            )
            logger.trace(
                f"Web session key removed",
                account_id=account_id,
                account_name=account["account_name"],
            )
        return True

    def update_web_session_key_error(
        self, account_id: str, error: Optional[str]
    ) -> bool:
        """Update web session key error for an account"""
        account = self.get_account_by_id(account_id)
        if not account:
            return False

        account["web_session_key_error"] = error
        account["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        self.save_accounts()
        return True
