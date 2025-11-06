import json
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .logger import logger

# TODO: Need rework: mostly a remnant from metrics working in a completely different and probably need to be safer when writing
# PERF: Worry about concurrent write


class RateLimiter:
    def __init__(self, state_file: Optional[Path] = None):
        if state_file is None:
            config_dir = Path.home() / ".config" / "claudebridge"
            config_dir.mkdir(parents=True, exist_ok=True)
            state_file = config_dir / "rate_limits.json"

        self.state_file = state_file
        self.windows = {}
        self.save_lock = threading.Lock()

        self._load_state()
        self._start_save_thread()

    def _get_token_windows(self, token_name: str) -> Dict[str, deque]:
        if token_name not in self.windows:
            self.windows[token_name] = {
                "requests_minute": deque(),
                "requests_hour": deque(),
                "requests_day": deque(),
                "tokens_minute": deque(),
                "tokens_day": deque(),
            }
        return self.windows[token_name]

    def _clean_window(self, window: deque, max_age: int) -> None:
        current_time = time.time()
        while window and window[0][0] < current_time - max_age:
            window.popleft()

    def _count_in_window(self, window: deque, max_age: int) -> int:
        self._clean_window(window, max_age)
        return sum(count for _, count in window)

    def check_limits(
        self,
        token_name: str,
        rate_limits: Optional[Dict[str, int]],
        token_count: int = 0,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        if not rate_limits:
            return True, None, None

        windows = self._get_token_windows(token_name)
        current_time = time.time()

        limits_config = {
            "requests_per_minute": ("requests_minute", 60, 1),
            "requests_per_hour": ("requests_hour", 3600, 1),
            "requests_per_day": ("requests_day", 86400, 1),
            "tokens_per_minute": ("tokens_minute", 60, token_count),
            "tokens_per_day": ("tokens_day", 86400, token_count),
        }

        headers = {}

        for limit_key, (window_key, max_age, increment) in limits_config.items():
            limit = rate_limits.get(limit_key)

            if limit is None:
                continue

            window = windows[window_key]
            current_usage = self._count_in_window(window, max_age)

            limit_type = limit_key.replace("_per_", "-").replace("_", "-")
            headers[f"X-RateLimit-Limit-{limit_type.title()}"] = str(limit)
            headers[f"X-RateLimit-Remaining-{limit_type.title()}"] = str(
                max(0, limit - current_usage)
            )

            reset_time = int(current_time + max_age)
            headers[f"X-RateLimit-Reset-{limit_type.title()}"] = str(reset_time)

            if current_usage + increment > limit:
                return False, limit_key, headers

        return True, None, headers

    def record_request(self, token_name: str, token_count: int = 0) -> None:
        windows = self._get_token_windows(token_name)
        current_time = time.time()

        windows["requests_minute"].append((current_time, 1))
        windows["requests_hour"].append((current_time, 1))
        windows["requests_day"].append((current_time, 1))

        if token_count > 0:
            windows["tokens_minute"].append((current_time, token_count))
            windows["tokens_day"].append((current_time, token_count))

    def get_usage_stats(self, token_name: str) -> Dict[str, int]:
        if token_name not in self.windows:
            return {
                "requests_per_minute": 0,
                "requests_per_hour": 0,
                "requests_per_day": 0,
                "tokens_per_minute": 0,
                "tokens_per_day": 0,
            }

        windows = self.windows[token_name]

        return {
            "requests_per_minute": self._count_in_window(
                windows["requests_minute"], 60
            ),
            "requests_per_hour": self._count_in_window(windows["requests_hour"], 3600),
            "requests_per_day": self._count_in_window(windows["requests_day"], 86400),
            "tokens_per_minute": self._count_in_window(windows["tokens_minute"], 60),
            "tokens_per_day": self._count_in_window(windows["tokens_day"], 86400),
        }

    def _load_state(self) -> None:
        if not self.state_file.exists():
            logger.info("No rate limit state found, starting fresh")
            return

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)

            current_time = time.time()

            for token_name, token_state in state.get("tokens", {}).items():
                self.windows[token_name] = {
                    "requests_minute": deque(),
                    "requests_hour": deque(),
                    "requests_day": deque(),
                    "tokens_minute": deque(),
                    "tokens_day": deque(),
                }

                # FIX: Please stop
                for window_key, entries in token_state.items():
                    if window_key in self.windows[token_name]:
                        for timestamp, count in entries:
                            if (
                                window_key == "requests_minute"
                                and current_time - timestamp < 60
                            ):
                                self.windows[token_name][window_key].append(
                                    (timestamp, count)
                                )
                            elif (
                                window_key == "requests_hour"
                                and current_time - timestamp < 3600
                            ):
                                self.windows[token_name][window_key].append(
                                    (timestamp, count)
                                )
                            elif (
                                window_key == "requests_day"
                                and current_time - timestamp < 86400
                            ):
                                self.windows[token_name][window_key].append(
                                    (timestamp, count)
                                )
                            elif (
                                window_key == "tokens_minute"
                                and current_time - timestamp < 60
                            ):
                                self.windows[token_name][window_key].append(
                                    (timestamp, count)
                                )
                            elif (
                                window_key == "tokens_day"
                                and current_time - timestamp < 86400
                            ):
                                self.windows[token_name][window_key].append(
                                    (timestamp, count)
                                )

            logger.info(f"Rate limit state loaded from {self.state_file}")
            logger.info(f"  Loaded windows for {len(self.windows)} tokens")

        except Exception as e:
            logger.info(f"Error loading rate limit state: {e}, starting fresh")

    def _save_state(self) -> None:
        with self.save_lock:
            try:
                state = {
                    "last_saved": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "tokens": {},
                }

                current_time = time.time()

                for token_name, windows in self.windows.items():
                    state["tokens"][token_name] = {}

                    for window_key, window in windows.items():
                        entries = [(ts, count) for ts, count in window]

                        if window_key in ["requests_minute", "tokens_minute"]:
                            entries = [
                                (ts, count)
                                for ts, count in entries
                                if current_time - ts < 60
                            ]
                        elif window_key == "requests_hour":
                            entries = [
                                (ts, count)
                                for ts, count in entries
                                if current_time - ts < 3600
                            ]
                        elif window_key in ["requests_day", "tokens_day"]:
                            entries = [
                                (ts, count)
                                for ts, count in entries
                                if current_time - ts < 86400
                            ]

                        if entries:
                            state["tokens"][token_name][window_key] = entries

                with open(self.state_file, "w") as f:
                    json.dump(state, f, indent=2)

                logger.info(f"Rate limit state saved ({len(self.windows)} tokens)")

            except Exception as e:
                logger.info(f"Error saving rate limit state: {e}")

    def _start_save_thread(self) -> None:
        def save_worker():
            while True:
                time.sleep(300)
                self._save_state()

        thread = threading.Thread(target=save_worker, daemon=True)
        thread.start()

    def shutdown(self) -> None:
        logger.info("Saving final rate limit state...")
        self._save_state()
