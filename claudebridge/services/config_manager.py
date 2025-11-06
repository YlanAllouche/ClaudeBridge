import hashlib
import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .logger import logger

# TODO: need a rewrite, some overlap
# TODO: consider only storing the hash of the admin password


class ConfigManager:
    def __init__(
        self, config_file: Optional[str] = None, models_file: Optional[str] = None
    ):
        config_dir = Path.home() / ".config" / "claudebridge"
        config_dir.mkdir(parents=True, exist_ok=True)

        if config_file:
            self.config_file = config_file
        else:
            self.config_file = str(config_dir / "config.json")

        if models_file:
            self.models_file = models_file
        else:
            app_dir = Path(__file__).parent.parent
            self.models_file = str(app_dir / "static" / "models.json")

        self.config = {}
        self.base_models = []
        self.last_modified = 0
        self.reload_callbacks = []
        self.watch_thread = None

        self.load_base_models()
        self.load_config()
        self.ensure_config()

    def load_base_models(self) -> None:
        if os.path.exists(self.models_file):
            with open(self.models_file, "r") as f:
                self.base_models = json.load(f)
        else:
            logger.debug(
                f"Warning: {self.models_file} not found, using empty model list"
            )
            self.base_models = []

    def load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)
                    self.last_modified = os.path.getmtime(self.config_file)
                    logger.info(f"Config loaded from {self.config_file}")
            except Exception as e:
                logger.info(f"Error loading config: {e}, using defaults")
                self.config = self.get_default_config()
        else:
            self.config = self.get_default_config()

        return self.config

    def reload(self) -> bool:
        if not os.path.exists(self.config_file):
            return False

        current_mtime = os.path.getmtime(self.config_file)
        if current_mtime > self.last_modified:
            logger.info("Config file changed, reloading...")
            self.load_config()

            for callback in self.reload_callbacks:
                try:
                    callback(self)
                except Exception as e:
                    logger.info(f"Error in config reload callback: {e}")

            return True
        return False

    def register_reload_callback(
        self, callback: Callable[["ConfigManager"], None]
    ) -> None:
        self.reload_callbacks.append(callback)

    def start_watch(self, interval: int = 2) -> None:
        if self.watch_thread is not None:
            logger.info("Config watcher already running")
            return

        def watch_worker():
            logger.info(f"Config watcher started (checking every {interval}s)")
            while True:
                time.sleep(interval)
                try:
                    self.reload()
                except Exception as e:
                    logger.info(f"Error checking config file: {e}")

        self.watch_thread = threading.Thread(target=watch_worker, daemon=True)
        self.watch_thread.start()

    def stop_watch(self) -> None:
        if self.watch_thread:
            logger.info("Config watcher stopped")
            self.watch_thread = None

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "ui_auth": {"enabled": True, "password": None},
            "models": {"blocked": [], "custom": [], "cost_overrides": {}},
            "api_tokens": {"enabled": False, "tokens": []},
            "metrics_endpoint_enabled": False,
            "spoof_on_anthropic": False,
        }

    def ensure_config(self) -> None:
        password_info = self.get_ui_password()

        if password_info["source"] == "none":
            generated_password = self.generate_password()
            self.config["ui_auth"]["enabled"] = True
            self.config["ui_auth"]["password"] = generated_password
            self.save_config()
            print(f"=" * 60)
            logger.info(f"GENERATED UI PASSWORD: {generated_password}")
            logger.info(f"Password saved to {self.config_file}")
            logger.info(
                f"You can disable password protection by setting DISABLE_UI_PASSWORD=true"
            )
            print(f"=" * 60)

    def save_config(self) -> None:
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
            self.last_modified = os.path.getmtime(self.config_file)
            logger.info(f"Config saved to {self.config_file}")
        except Exception as e:
            logger.info(f"Error saving config: {e}")

    def generate_password(self, length: int = 16) -> str:
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def get_ui_password(self) -> Dict[str, Any]:
        disable_env = os.environ.get("DISABLE_UI_PASSWORD", "").lower()
        if disable_env in ("true", "1", "yes"):
            return {"password": None, "source": "env_disabled"}

        env_password = os.environ.get("UI_PASSWORD")
        if env_password:
            return {"password": env_password, "source": "env"}

        if not self.config.get("ui_auth", {}).get("enabled", True):
            return {"password": None, "source": "config_disabled"}

        config_password = self.config.get("ui_auth", {}).get("password")
        if config_password:
            return {"password": config_password, "source": "config"}

        return {"password": None, "source": "none"}

    def set_ui_password(self, password: Optional[str] = None) -> str:
        """Set UI password. If None, generates a random one. Returns the password."""
        if password is None or password.strip() == "":
            password = self.generate_password()

        if "ui_auth" not in self.config:
            self.config["ui_auth"] = {}

        self.config["ui_auth"]["enabled"] = True
        self.config["ui_auth"]["password"] = password
        self.save_config()

        return password

    def verify_ui_password(self, provided_password: str) -> bool:
        password_info = self.get_ui_password()

        if password_info["password"] is None:
            return True

        return provided_password == password_info["password"]

    def is_ui_password_enabled(self) -> bool:
        password_info = self.get_ui_password()
        return password_info["password"] is not None

    def normalize_custom_model(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in model_config:
            raise ValueError("Custom model must have 'id' field")

        normalized = {
            "id": model_config["id"],
            "object": model_config.get("object", "model"),
            "created": model_config.get("created", int(time.time())),
            "owned_by": model_config.get("owned_by", "anthropic"),
        }

        if "input_cost_per_million" in model_config:
            normalized["input_cost_per_million"] = model_config[
                "input_cost_per_million"
            ]
        if "output_cost_per_million" in model_config:
            normalized["output_cost_per_million"] = model_config[
                "output_cost_per_million"
            ]

        return normalized

    def get_models(self) -> List[Dict[str, Any]]:
        blocked = set(self.config.get("models", {}).get("blocked", []))

        available_models = [m for m in self.base_models if m["id"] not in blocked]

        custom_models_raw = self.config.get("models", {}).get("custom", [])
        custom_models = []
        for model_config in custom_models_raw:
            try:
                custom_models.append(self.normalize_custom_model(model_config))
            except Exception as e:
                logger.info(f"Error normalizing custom model {model_config}: {e}")

        return available_models + custom_models

    def get_all_models_with_status(self) -> List[Dict[str, Any]]:
        """Get all models including blocked ones, for UI display"""
        blocked = set(self.config.get("models", {}).get("blocked", []))

        # Return ALL base models regardless of blocked status
        all_models = self.base_models.copy()

        custom_models_raw = self.config.get("models", {}).get("custom", [])
        for model_config in custom_models_raw:
            try:
                all_models.append(self.normalize_custom_model(model_config))
            except Exception as e:
                logger.info(f"Error normalizing custom model {model_config}: {e}")

        return all_models

    def add_blocked_model(self, model_id: str) -> None:
        if "models" not in self.config:
            self.config["models"] = {"blocked": [], "custom": []}
        if "blocked" not in self.config["models"]:
            self.config["models"]["blocked"] = []

        if model_id not in self.config["models"]["blocked"]:
            self.config["models"]["blocked"].append(model_id)
            self.save_config()

    def remove_blocked_model(self, model_id: str) -> None:
        if model_id in self.config.get("models", {}).get("blocked", []):
            self.config["models"]["blocked"].remove(model_id)
            self.save_config()

    def add_custom_model(self, model_config: Dict[str, Any]) -> None:
        normalized = self.normalize_custom_model(model_config)

        if "models" not in self.config:
            self.config["models"] = {"blocked": [], "custom": []}
        if "custom" not in self.config["models"]:
            self.config["models"]["custom"] = []

        existing_ids = [m["id"] for m in self.config["models"]["custom"]]
        if normalized["id"] not in existing_ids:
            self.config["models"]["custom"].append(normalized)
            self.save_config()

    def remove_custom_model(self, model_id: str) -> None:
        if "models" in self.config and "custom" in self.config["models"]:
            self.config["models"]["custom"] = [
                m for m in self.config["models"]["custom"] if m["id"] != model_id
            ]
            self.save_config()

    def hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def verify_api_token(self, provided_token: str) -> Optional[Dict[str, Any]]:
        if not self.config.get("api_tokens", {}).get("enabled", False):
            return None

        for token_entry in self.config.get("api_tokens", {}).get("tokens", []):
            if token_entry.get("token") == provided_token:
                return token_entry
            elif token_entry.get("token_hash") == self.hash_token(provided_token):
                return token_entry

        return None

    def get_all_tokens(self) -> list:
        return self.config.get("api_tokens", {}).get("tokens", [])

    def add_api_token(self, name: str) -> str:
        token = f"sk-ant-api03-{secrets.token_urlsafe(64)}"

        if "api_tokens" not in self.config:
            self.config["api_tokens"] = {"enabled": False, "tokens": []}
        if "tokens" not in self.config["api_tokens"]:
            self.config["api_tokens"]["tokens"] = []

        token_entry = {
            "token": token,
            "name": name,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        self.config["api_tokens"]["tokens"].append(token_entry)
        self.save_config()

        return token

    def revoke_api_token(self, token: str) -> bool:
        if "api_tokens" in self.config and "tokens" in self.config["api_tokens"]:
            original_count = len(self.config["api_tokens"]["tokens"])
            self.config["api_tokens"]["tokens"] = [
                t
                for t in self.config["api_tokens"]["tokens"]
                if t.get("token") != token and t.get("token_hash") != token
            ]

            if len(self.config["api_tokens"]["tokens"]) < original_count:
                self.save_config()
                return True

        return False

    def get_model_cost(self, model_id: str) -> Optional[Dict[str, float]]:
        """Get cost per million tokens for a model (input and output)

        Returns 'input' and 'output' keys, or None if no cost available.
        Checks overrides first (previous user input), then base models.
        """
        cost_overrides = self.config.get("models", {}).get("cost_overrides", {})

        if model_id in cost_overrides:
            override = cost_overrides[model_id]
            return {
                "input": override.get("input_cost_per_million"),
                "output": override.get("output_cost_per_million"),
            }

        for model in self.base_models:
            if model["id"] == model_id:
                input_cost = model.get("input_cost_per_million")
                output_cost = model.get("output_cost_per_million")
                if input_cost is not None and output_cost is not None:
                    return {"input": input_cost, "output": output_cost}

        for model in self.config.get("models", {}).get("custom", []):
            if model["id"] == model_id:
                input_cost = model.get("input_cost_per_million")
                output_cost = model.get("output_cost_per_million")
                if input_cost is not None and output_cost is not None:
                    return {"input": input_cost, "output": output_cost}

        return None

    def set_model_cost(
        self, model_id: str, input_cost: float, output_cost: float
    ) -> None:
        """Set cost override for a model in config.json"""
        if "models" not in self.config:
            self.config["models"] = {"blocked": [], "custom": [], "cost_overrides": {}}
        if "cost_overrides" not in self.config["models"]:
            self.config["models"]["cost_overrides"] = {}

        self.config["models"]["cost_overrides"][model_id] = {
            "input_cost_per_million": input_cost,
            "output_cost_per_million": output_cost,
        }

        self.save_config()
        logger.info(
            f"Set cost override for {model_id}: ${input_cost}/${output_cost} per million tokens"
        )

    def remove_model_cost_override(self, model_id: str) -> bool:
        """Remove cost override for a model"""
        cost_overrides = self.config.get("models", {}).get("cost_overrides", {})

        if model_id in cost_overrides:
            del self.config["models"]["cost_overrides"][model_id]
            self.save_config()
            logger.info(f"Removed cost override for {model_id}")
            return True

        return False
