import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from .logger import logger

# TODO: Refactor remnant from the inferred session bounds era


class MetricsManager:
    def __init__(self, config_dir: Optional[Path] = None, config_manager=None):
        if config_dir is None:
            config_dir = Path.home() / ".config" / "claudebridge"

        self.metrics_file = config_dir / "metrics.json"
        self.config_manager = config_manager

        self.request_counter = 0
        self.last_checkpoint_counter = 0
        self.checkpoint_lock = threading.Lock()

        self.data = {
            "version": "3.0",
            "global": {
                "requests": {"success": 0, "error": 0, "ooq": 0},
                "tokens_by_model": {},
                "requests_by_user": {},
                "errors_by_type": {},
            },
            "current_7d_period": None,
            "past_7d_periods": [],
        }

        self._load_checkpoint()
        self._start_checkpoint_thread()

    def _load_checkpoint(self):
        if not self.metrics_file.exists():
            logger.info("No metrics checkpoint found, starting fresh")
            return

        try:
            with open(self.metrics_file, "r") as f:
                checkpoint = json.load(f)

            version = checkpoint.get("version", "unknown")
            logger.info(f"Loading metrics checkpoint (version {version})")

            if version == "3.0":
                if "current_7d_period" not in checkpoint:
                    checkpoint["current_7d_period"] = None
                if "past_7d_periods" not in checkpoint:
                    checkpoint["past_7d_periods"] = []
                if "global" not in checkpoint:
                    checkpoint["global"] = {
                        "requests": {"success": 0, "error": 0, "ooq": 0},
                        "tokens_by_model": {},
                        "requests_by_user": {},
                        "errors_by_type": {},
                    }

                self.data = checkpoint
                logger.info("Loaded v3.0 checkpoint successfully")
            else:
                logger.warning(
                    f"Incompatible checkpoint version {version}, starting fresh"
                )

        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}, starting fresh")

    # FIX: can this race condition?
    def _validate_data_structure(self) -> bool:
        """Validate data structure integrity before writing"""
        try:
            required_keys = [
                "version",
                "global",
                "current_7d_period",
                "past_7d_periods",
            ]
            for key in required_keys:
                if key not in self.data:
                    logger.error(f"Data validation failed: missing key '{key}'")
                    return False

            if not isinstance(self.data["past_7d_periods"], list):
                logger.error("Data validation failed: past_7d_periods is not a list")
                return False

            if self.data.get("version") != "3.0":
                logger.error(
                    f"Data validation failed: incorrect version '{self.data.get('version')}'"
                )
                return False

            logger.trace("Data structure validation passed")
            return True
        except Exception as e:
            logger.error(f"Data validation exception: {e}")
            return False

    def _save_checkpoint(self):
        logger.trace(
            f"_save_checkpoint called: request_counter={self.request_counter}, has_7d_period={self.data['current_7d_period'] is not None}, has_5h_session={self.data['current_7d_period'] and self.data['current_7d_period'].get('current_5h_session') is not None}"
        )

        with self.checkpoint_lock:
            try:
                if not self._validate_data_structure():
                    logger.error("Aborting checkpoint save: data validation failed")
                    return

                logger.trace(
                    f"Data structure to write: {json.dumps(self.data, indent=2)}"
                )

                self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

                logger.trace(f"Writing to {self.metrics_file}")

                with open(self.metrics_file, "w") as f:
                    json.dump(self.data, f, indent=2)

                file_size = self.metrics_file.stat().st_size
                logger.trace(f"Write completed: file_size={file_size} bytes")
                logger.debug(
                    f"Metrics checkpoint saved: {self.request_counter} requests processed"
                )

            except Exception as e:
                logger.trace(
                    f"Write failed! Current data state: version={self.data.get('version')}, has_7d={self.data.get('current_7d_period') is not None}, global_requests={self.data.get('global', {}).get('requests')}"
                )
                logger.error(f"Error saving checkpoint: {e}")

    def _start_checkpoint_thread(self):
        import os

        # Skip checkpoint thread in Flask reloader parent process
        # The parent process doesn't handle requests, only watches for file changes
        # This prevents duplicate writes to metrics.json from both parent and child
        if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            logger.debug("Skipping checkpoint thread (Flask reloader parent process)")
            return

        # FIX: can this race condition?
        def checkpoint_worker():
            last_save = time.time()
            while True:
                time.sleep(1)

                current_time = time.time()
                time_since_save = current_time - last_save
                requests_since_save = (
                    self.request_counter - self.last_checkpoint_counter
                )

                should_save = time_since_save >= 10 or requests_since_save >= 5

                if should_save:
                    trigger_reason = "time" if time_since_save >= 10 else "requests"
                    logger.trace(
                        f"Checkpoint triggered by {trigger_reason}: time_since_save={time_since_save:.1f}s, requests_since_save={requests_since_save}"
                    )
                    self._save_checkpoint()
                    last_save = current_time
                    self.last_checkpoint_counter = self.request_counter

        thread = threading.Thread(target=checkpoint_worker, daemon=True)
        thread.start()
        logger.debug("Checkpoint thread started")

    def log_request(
        self,
        status: Literal["success", "error", "ooq"],
        model: str,
        account_id: str,
        user_token: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        error_type: Optional[str] = None,
        response_headers: Optional[dict] = None,
    ):
        timestamp = int(time.time())

        logger.info(
            f"Request logged: status={status}, model={model}, user={user_token}, "
            f"tokens={input_tokens + output_tokens}"
        )

        if status == "error" and error_type:
            logger.trace(f"Error details: type={error_type}")

        if status == "ooq" and response_headers:
            logger.trace(f"OOQ headers: {response_headers}")

        self._update_global_stats(
            status, model, user_token, input_tokens, output_tokens, error_type
        )

        # First ensure period and session exist
        self._ensure_7d_period(timestamp)
        self._ensure_5h_session(timestamp)

        # Then update their bounds from headers (and mark for rollover if needed)
        if response_headers:
            self._update_session_bounds_from_headers(timestamp, response_headers)

            # Check again for rollover after updating bounds
            self._ensure_7d_period(timestamp)
            self._ensure_5h_session(timestamp)

        # Handle OOQ-specific logic
        if status == "ooq" and response_headers:
            self._handle_ooq(timestamp, response_headers)

        # Update session stats for both success and OOQ requests
        if status in ["success", "ooq"]:
            self._update_session_stats(
                model, user_token, input_tokens, output_tokens, status
            )

        self.request_counter += 1

    def _update_global_stats(
        self,
        status: str,
        model: str,
        user_token: str,
        input_tokens: int,
        output_tokens: int,
        error_type: Optional[str],
    ):
        self.data["global"]["requests"][status] += 1

        if status == "success":
            if model not in self.data["global"]["tokens_by_model"]:
                self.data["global"]["tokens_by_model"][model] = {
                    "input": 0,
                    "output": 0,
                }

            self.data["global"]["tokens_by_model"][model]["input"] += input_tokens
            self.data["global"]["tokens_by_model"][model]["output"] += output_tokens

        if user_token not in self.data["global"]["requests_by_user"]:
            self.data["global"]["requests_by_user"][user_token] = {
                "success": 0,
                "error": 0,
                "ooq": 0,
            }

        self.data["global"]["requests_by_user"][user_token][status] += 1

        if status == "error" and error_type:
            if error_type not in self.data["global"]["errors_by_type"]:
                self.data["global"]["errors_by_type"][error_type] = 0
            self.data["global"]["errors_by_type"][error_type] += 1

    def _ensure_7d_period(self, timestamp: int):
        if self.data["current_7d_period"] is None:
            logger.debug(f"Starting new 7d period at {timestamp}")
            self._start_new_7d_period(timestamp)
            return

        period = self.data["current_7d_period"]

        # Check if Anthropic indicated a window rollover
        if period.get("_needs_rollover"):
            period["termination_reason"] = "rollover"
            new_reset = period.get("_new_reset")
            logger.debug(
                f"Anthropic rolled 7d window, archiving and starting new one with reset={new_reset}"
            )
            self._archive_7d_period()
            self._start_new_7d_period(timestamp, reset_timestamp=new_reset)
            return

        end_timestamp = period.get("end_confirmed") or period.get("end_inferred")

        if end_timestamp and timestamp >= end_timestamp:
            # Only set termination_reason to 'natural' if not already set (e.g., by OOQ)
            if period.get("termination_reason") is None:
                period["termination_reason"] = "natural"
            logger.debug(
                f"7d period expired (time-based), archiving and starting new one"
            )
            self._archive_7d_period()
            self._start_new_7d_period(timestamp)

    def _start_new_7d_period(
        self, timestamp: int, reset_timestamp: Optional[int] = None
    ):
        if reset_timestamp:
            period_id = f"7d_{reset_timestamp}"
            start = reset_timestamp - (7 * 24 * 60 * 60)
            end_inferred = reset_timestamp
            end_confirmed = reset_timestamp
            logger.trace(
                f"Creating new 7d period from reset: {period_id}, start={start}, end={reset_timestamp}"
            )
        else:
            period_id = f"7d_{timestamp}_pending"
            start = timestamp
            end_inferred = timestamp + (7 * 24 * 60 * 60)
            end_confirmed = None
            logger.trace(f"Creating new 7d period (pending reset): {period_id}")

        self.data["current_7d_period"] = {
            "period_id": period_id,
            "start": start,
            "end_inferred": end_inferred,
            "end_confirmed": end_confirmed,
            "termination_reason": None,
            "requests": {"success": 0, "error": 0, "ooq": 0},
            "tokens_by_model": {},
            "tokens_by_user": {},
            "current_5h_session": None,
            "past_5h_sessions": [],
        }

        logger.info(
            f"New 7d period started: {period_id}, start={start}, end={end_inferred}"
        )
        logger.trace(
            f"7d period structure: {json.dumps(self.data['current_7d_period'], indent=2)}"
        )

    def _archive_7d_period(self):
        if self.data["current_7d_period"] is None:
            logger.trace("_archive_7d_period: no current period to archive")
            return

        period = self.data["current_7d_period"]
        logger.trace(
            f"Archiving 7d period: {period['period_id']}, has_5h_session={period['current_5h_session'] is not None}, past_sessions_count={len(period['past_5h_sessions'])}"
        )

        if period["current_5h_session"] is not None:
            logger.trace(
                f"Moving current 5h session to past: {period['current_5h_session']['session_id']}"
            )
            period["past_5h_sessions"].append(period["current_5h_session"])
            period["current_5h_session"] = None

        self.data["past_7d_periods"].insert(0, period)

        logger.info(
            f"Archived 7d period: {period['period_id']}, total_past_periods={len(self.data['past_7d_periods'])}"
        )

    def _ensure_5h_session(self, timestamp: int):
        if self.data["current_7d_period"] is None:
            return

        period = self.data["current_7d_period"]

        # TODO: Not entire sure this is needed
        # Check if Anthropic indicated a window rollover
        current_session = period.get("current_5h_session") or {}
        # FIX: Could this be none?
        if current_session.get("_needs_rollover"):
            session = period["current_5h_session"]
            session["termination_reason"] = "rollover"
            new_reset = session.get("_new_reset")
            logger.debug(
                f"Anthropic rolled 5h window, archiving and starting new one with reset={new_reset}"
            )
            self._archive_5h_session()
            self._start_new_5h_session(timestamp, reset_timestamp=new_reset)
            return

        if period.get("current_5h_session") is None:
            logger.debug(f"Starting new 5h session at {timestamp}")
            self._start_new_5h_session(timestamp)
            return

        session = period["current_5h_session"]

        end_timestamp = session.get("end_confirmed") or session.get("end_inferred")

        if end_timestamp and timestamp >= end_timestamp:
            # Only set termination_reason to 'natural' if not already set (e.g., by OOQ)
            if session.get("termination_reason") is None:
                session["termination_reason"] = "natural"
            logger.debug(
                f"5h session expired (time-based), archiving and starting new one"
            )
            self._archive_5h_session()
            self._start_new_5h_session(timestamp)

    def _start_new_5h_session(
        self, timestamp: int, reset_timestamp: Optional[int] = None
    ):
        if self.data["current_7d_period"] is None:
            logger.trace("_start_new_5h_session: no current 7d period")
            return

        if reset_timestamp:
            session_id = f"5h_{reset_timestamp}"
            start = reset_timestamp - (5 * 60 * 60)
            end_inferred = reset_timestamp
            end_confirmed = reset_timestamp
            logger.trace(
                f"Creating new 5h session from reset: {session_id}, start={start}, end={reset_timestamp}"
            )
        else:
            session_id = f"5h_{timestamp}_pending"
            start = timestamp
            end_inferred = timestamp + (5 * 60 * 60)
            end_confirmed = None
            logger.trace(f"Creating new 5h session (pending reset): {session_id}")

        self.data["current_7d_period"]["current_5h_session"] = {
            "session_id": session_id,
            "start": start,
            "end_inferred": end_inferred,
            "end_confirmed": end_confirmed,
            "termination_reason": None,
            "requests": {"success": 0, "error": 0, "ooq": 0},
            "tokens_by_model": {},
            "tokens_by_user": {},
        }

        logger.info(
            f"New 5h session started: {session_id}, start={start}, end={end_inferred}"
        )
        logger.trace(
            f"5h session structure: {json.dumps(self.data['current_7d_period']['current_5h_session'], indent=2)}"
        )

    def _archive_5h_session(self):
        if self.data["current_7d_period"] is None:
            logger.trace("_archive_5h_session: no current 7d period")
            return

        period = self.data["current_7d_period"]

        if period["current_5h_session"] is None:
            logger.trace("_archive_5h_session: no current 5h session to archive")
            return

        session = period["current_5h_session"]
        logger.trace(
            f"Archiving 5h session: {session['session_id']}, requests={session['requests']}"
        )

        period["past_5h_sessions"].insert(0, session)
        period["current_5h_session"] = None

        logger.info(
            f"Archived 5h session: {session['session_id']}, total_past_sessions={len(period['past_5h_sessions'])}"
        )

    def _update_session_bounds_from_headers(
        self, timestamp: int, response_headers: dict
    ):
        """Update session bounds from Anthropic's servers's headers on ANY response (200, 429, etc.)"""
        # NOTE: Don't try to DRY this
        reset_5h = response_headers.get("anthropic-ratelimit-unified-5h-reset")
        status_5h = response_headers.get("anthropic-ratelimit-unified-5h-status")
        reset_7d = response_headers.get("anthropic-ratelimit-unified-7d-reset")
        status_7d = response_headers.get("anthropic-ratelimit-unified-7d-status")

        logger.trace(
            f"Updating bounds from headers: reset_5h={reset_5h}, status_5h={status_5h}, reset_7d={reset_7d}, status_7d={status_7d}"
        )

        # Update 5h session bounds
        if reset_5h:
            reset_5h_ts = int(reset_5h)
            if self.data["current_7d_period"] and self.data["current_7d_period"].get(
                "current_5h_session"
            ):
                session = self.data["current_7d_period"]["current_5h_session"]
                stored_reset = session.get("end_confirmed")
                session_id = session.get("session_id")

                logger.trace(
                    f"5h session update: stored_reset={stored_reset}, new_reset={reset_5h_ts}, session_id={session_id}"
                )

                if stored_reset is None:
                    # First time getting confirmed reset - update ID from pending to reset-based
                    if session_id and session_id.endswith("_pending"):
                        new_session_id = f"5h_{reset_5h_ts}"
                        calculated_start = reset_5h_ts - (5 * 60 * 60)
                        session["session_id"] = new_session_id
                        session["start"] = calculated_start
                        session["end_inferred"] = reset_5h_ts
                        logger.info(
                            f"5h session ID updated: {session_id} → {new_session_id}, start recalculated: {calculated_start}"
                        )
                    session["end_confirmed"] = reset_5h_ts
                    logger.debug(f"5h session confirmed: reset at {reset_5h_ts}")
                elif stored_reset != reset_5h_ts:
                    # Different reset time = Anthropic rolled the window = need new session
                    logger.info(
                        f"5h window rolled by Anthropic: {stored_reset} → {reset_5h_ts}"
                    )
                    logger.trace(f"Marking session for rollover: {session_id}")
                    session["_needs_rollover"] = True
                    session["_new_reset"] = reset_5h_ts
                else:
                    logger.trace(f"5h session confirmed (same reset): {reset_5h_ts}")

        # Update 7d period bounds
        if reset_7d:
            reset_7d_ts = int(reset_7d)
            if self.data["current_7d_period"]:
                period = self.data["current_7d_period"]
                stored_reset = period.get("end_confirmed")
                period_id = period.get("period_id")

                logger.trace(
                    f"7d period update: stored_reset={stored_reset}, new_reset={reset_7d_ts}, period_id={period_id}"
                )

                if stored_reset is None:
                    # First time getting confirmed reset - update ID from pending to reset-based
                    if period_id and period_id.endswith("_pending"):
                        new_period_id = f"7d_{reset_7d_ts}"
                        calculated_start = reset_7d_ts - (7 * 24 * 60 * 60)
                        period["period_id"] = new_period_id
                        period["start"] = calculated_start
                        period["end_inferred"] = reset_7d_ts
                        logger.info(
                            f"7d period ID updated: {period_id} → {new_period_id}, start recalculated: {calculated_start}"
                        )
                    period["end_confirmed"] = reset_7d_ts
                    logger.debug(f"7d period confirmed: reset at {reset_7d_ts}")
                elif stored_reset != reset_7d_ts:
                    # Different reset time = Anthropic rolled the window = need new period
                    logger.info(
                        f"7d window rolled by Anthropic: {stored_reset} → {reset_7d_ts}"
                    )
                    logger.trace(f"Marking period for rollover: {period_id}")
                    period["_needs_rollover"] = True
                    period["_new_reset"] = reset_7d_ts
                else:
                    logger.trace(f"7d period confirmed (same reset): {reset_7d_ts}")

    def _handle_ooq(self, timestamp: int, response_headers: dict):
        """Handle OOQ status and mark termination reason"""
        ooq_5h_status = response_headers.get("anthropic-ratelimit-unified-5h-status")
        ooq_7d_status = response_headers.get("anthropic-ratelimit-unified-7d-status")

        if ooq_5h_status == "rejected":
            # Mark 5h session as terminated due to OOQ
            if self.data["current_7d_period"] and self.data["current_7d_period"].get(
                "current_5h_session"
            ):
                session = self.data["current_7d_period"]["current_5h_session"]
                if session.get("termination_reason") is None:
                    session["termination_reason"] = "ooq_5h"

                    # Track time elapsed when OOQ hit (how fast we hit the limit)
                    session_start = session.get("start", timestamp)
                    time_elapsed = timestamp - session_start
                    session["ooq_timestamp"] = timestamp
                    session["time_elapsed_at_ooq"] = time_elapsed

                    logger.warning(
                        f"5h session terminated: Out of quota after {time_elapsed}s"
                    )

        if ooq_7d_status == "rejected":
            # Mark 7d period as terminated due to OOQ
            if self.data["current_7d_period"]:
                period = self.data["current_7d_period"]
                if period.get("termination_reason") is None:
                    period["termination_reason"] = "ooq_7d"

                    # Track time elapsed when OOQ hit (how fast we hit the limit)
                    period_start = period.get("start", timestamp)
                    time_elapsed = timestamp - period_start
                    period["ooq_timestamp"] = timestamp
                    period["time_elapsed_at_ooq"] = time_elapsed

                    logger.warning(
                        f"7d period terminated: Out of quota after {time_elapsed}s"
                    )

                # If 7d OOQ, also mark the 5h session (it's implicitly terminated too)
                if period.get("current_5h_session"):
                    session = period["current_5h_session"]
                    if session.get("termination_reason") is None:
                        session["termination_reason"] = "ooq_7d"

                        # Track 5h session's own elapsed time when 7d OOQ hit
                        session_start = session.get("start", timestamp)
                        time_elapsed = timestamp - session_start
                        session["ooq_timestamp"] = timestamp
                        session["time_elapsed_at_ooq"] = time_elapsed

    def _update_session_stats(
        self,
        model: str,
        user_token: str,
        input_tokens: int,
        output_tokens: int,
        status: str = "success",
    ):
        if self.data["current_7d_period"] is None:
            return

        period = self.data["current_7d_period"]

        # Increment request counter for the appropriate status
        period["requests"][status] += 1

        # Only track tokens for successful requests (OOQ responses may not have tokens)
        if status == "success":
            if model not in period["tokens_by_model"]:
                period["tokens_by_model"][model] = {"input": 0, "output": 0}
            period["tokens_by_model"][model]["input"] += input_tokens
            period["tokens_by_model"][model]["output"] += output_tokens

            if user_token not in period["tokens_by_user"]:
                period["tokens_by_user"][user_token] = {"input": 0, "output": 0}
            period["tokens_by_user"][user_token]["input"] += input_tokens
            period["tokens_by_user"][user_token]["output"] += output_tokens

        session = period.get("current_5h_session")
        if session is None:
            return

        # Increment request counter for the appropriate status
        session["requests"][status] += 1

        # Only track tokens for successful requests
        if status == "success":
            if model not in session["tokens_by_model"]:
                session["tokens_by_model"][model] = {
                    "input": 0,
                    "output": 0,
                    "cost_input": 0,
                    "cost_output": 0,
                }
            session["tokens_by_model"][model]["input"] += input_tokens
            session["tokens_by_model"][model]["output"] += output_tokens

            # Calculate and update costs
            if self.config_manager:
                costs = self.config_manager.get_model_cost(model)
                if costs:
                    cost_input = (input_tokens / 1_000_000) * costs["input"]
                    cost_output = (output_tokens / 1_000_000) * costs["output"]
                    session["tokens_by_model"][model]["cost_input"] += cost_input
                    session["tokens_by_model"][model]["cost_output"] += cost_output

            if user_token not in session["tokens_by_user"]:
                session["tokens_by_user"][user_token] = {"input": 0, "output": 0}
            session["tokens_by_user"][user_token]["input"] += input_tokens
            session["tokens_by_user"][user_token]["output"] += output_tokens

    # TODO: Is this still needed?
    def get_metrics_summary(self) -> Dict[str, Any]:
        current_time = int(time.time())

        summary = {
            "global": self.data["global"],
            "current_7d_period": None,
            "past_7d_periods": [],
        }

        if self.data["current_7d_period"]:
            period = self.data["current_7d_period"].copy()

            end_timestamp = period.get("end_confirmed") or period.get("end_inferred")
            time_remaining = (
                max(0, end_timestamp - current_time) if end_timestamp else 0
            )

            # Prioritize termination_reason over time-based status
            termination_reason = period.get("termination_reason")
            if termination_reason == "ooq_7d" and time_remaining > 0:
                period["status"] = "ooq_7d"
            elif time_remaining > 0:
                period["status"] = "active"
            else:
                period["status"] = "ready"

            period["time_remaining"] = time_remaining

            if period["current_5h_session"]:
                session = period["current_5h_session"].copy()
                session_end = session.get("end_confirmed") or session.get(
                    "end_inferred"
                )
                session_time_remaining = (
                    max(0, session_end - current_time) if session_end else 0
                )

                # Prioritize termination_reason over time-based status
                session_termination = session.get("termination_reason")
                period_is_ooq_7d = period["status"] == "ooq_7d"

                if session_termination == "ooq_5h" and session_time_remaining > 0:
                    session["status"] = "ooq_5h"
                    session["time_remaining"] = session_time_remaining
                elif (
                    session_termination == "ooq_7d" or period_is_ooq_7d
                ) and session_time_remaining > 0:
                    # 5h session inherits 7d limitation
                    session["status"] = "ooq_7d"
                    session["time_remaining"] = session_time_remaining
                elif (
                    period["status"] == "ready"
                    and period.get("end_confirmed")
                    and session_time_remaining > 0
                ):
                    # 7d period expired but 5h session still has time (blocked by 7d)
                    session["status"] = "blocked_by_7d"
                    session["time_remaining"] = time_remaining
                elif session_time_remaining > 0:
                    session["status"] = "active"
                    session["time_remaining"] = session_time_remaining
                else:
                    session["status"] = "ready"
                    session["time_remaining"] = 0

                period["current_5h_session"] = session

            summary["current_7d_period"] = period

        for past_period in self.data["past_7d_periods"]:
            summary["past_7d_periods"].append(past_period)

        return summary

    # ================
    # FIX: Might be partially implemented as the rate-limiting feature is a remnant from the first version
    def track_rate_limit(self, token_name: str, limit_type: str):
        logger.warning(f"Rate limit exceeded: token={token_name}, type={limit_type}")

    def update_active_tokens(self, count: int):
        logger.debug(f"Active tokens updated: {count}")

    # ================

    # TODO: Is this still needed?
    def get_metrics_dict(self) -> Dict[str, Any]:
        return {
            "requests_breakdown": self.data["global"]["requests"],
            "tokens": {
                "input": {
                    f"global.{model}": data["input"]
                    for model, data in self.data["global"]["tokens_by_model"].items()
                },
                "output": {
                    f"global.{model}": data["output"]
                    for model, data in self.data["global"]["tokens_by_model"].items()
                },
            },
            "errors": self.data["global"]["errors_by_type"],
            "active_tokens": 0,
        }

    def shutdown(self):
        logger.info("Saving final metrics checkpoint...")
        self._save_checkpoint()
