import os

import pyhtml as p
import pyhtml_cem.webawesome.components as wa
from flask import request

from claudebridge.blueprints.dependencies import get_config_manager
from claudebridge.services.ui import create_layout, create_settings_page

from . import ui_bp


@ui_bp.route("/settings", methods=["GET"])
def ui_settings():
    config_manager = get_config_manager()
    content = create_settings_page(config_manager)

    if request.headers.get("HX-Request"):
        return str(content)

    return str(create_layout(content, "Settings - ClaudeBridge", "settings"))


@ui_bp.route("/settings/password", methods=["POST"])
def update_ui_password():
    config_manager = get_config_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    new_password = data.get("password", "").strip()

    password_info = config_manager.get_ui_password()
    # NOTE: Not sure this matters
    if password_info["source"] == "env":
        return "Password is set via environment variable and cannot be changed", 403

    actual_password = config_manager.set_ui_password(
        new_password if new_password else None
    )

    if not new_password:
        return f"Password updated to: {actual_password}", 200

    return "", 200


@ui_bp.route("/settings/spoof-toggle", methods=["POST"])
def toggle_spoof():
    config_manager = get_config_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    enabled = data.get("enabled")

    if isinstance(enabled, str):
        enabled = enabled.lower() in ["true", "1", "yes"]

    config_manager.config["spoof_on_anthropic"] = bool(enabled)
    config_manager.save_config()

    return str(
        p.span(
            wa.badge(
                "Enabled" if enabled else "Disabled",
                variant="success" if enabled else "neutral",
            ),
            id="spoof-status-badge",
        )
    )


@ui_bp.route("/settings/metrics-toggle", methods=["POST"])
def toggle_metrics():
    config_manager = get_config_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    enabled = data.get("enabled")

    if isinstance(enabled, str):
        enabled = enabled.lower() in ["true", "1", "yes"]

    config_manager.config["metrics_endpoint_enabled"] = bool(enabled)
    config_manager.save_config()

    return str(
        p.span(
            wa.badge(
                "Enabled" if enabled else "Disabled",
                variant="success" if enabled else "neutral",
            ),
            id="metrics-status-badge",
        )
    )


@ui_bp.route("/reveal-key", methods=["GET"])
def reveal_api_key():
    api_key = os.getenv("ANTHROPIC_API_KEY", "Not configured")
    return f'<code id="api-key-display" style="background: #f3f4f6; padding: 0.5rem 1rem; border-radius: 4px; font-family: monospace; display: inline-block;">{api_key}</code>'
