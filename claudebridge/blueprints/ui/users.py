from flask import request

from claudebridge.blueprints.dependencies import get_config_manager, get_metrics_manager
from claudebridge.services.ui import create_layout, create_users_page
from claudebridge.services.ui.users import create_users_table

from . import ui_bp


@ui_bp.route("/users", methods=["GET"])
def ui_users():
    config_manager = get_config_manager()
    metrics_manager = get_metrics_manager()

    tokens = config_manager.get_all_tokens()
    user_stats = metrics_manager.data.get("users", {})

    content = create_users_page(tokens, user_stats)

    if request.headers.get("HX-Request"):
        return str(content)

    return str(create_layout(content, "Users - ClaudeBridge", "users"))


@ui_bp.route("/users/add", methods=["POST"])
def add_user():
    config_manager = get_config_manager()
    metrics_manager = get_metrics_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    name = data.get("name", "").strip()

    if not name:
        return "Name required", 400

    token = config_manager.add_api_token(name)

    tokens = config_manager.get_all_tokens()
    user_stats = metrics_manager.data.get("users", {})

    return str(create_users_table(tokens, user_stats))


@ui_bp.route("/users/delete", methods=["POST"])
def delete_user():
    config_manager = get_config_manager()
    metrics_manager = get_metrics_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    token = data.get("token")

    if not token:
        return "Token required", 400

    success = config_manager.revoke_api_token(token)

    if success:
        tokens = config_manager.get_all_tokens()
        user_stats = metrics_manager.data.get("users", {})
        return str(create_users_table(tokens, user_stats))
    else:
        return "Token not found", 404


@ui_bp.route("/users/regenerate", methods=["POST"])
def regenerate_user_token():
    config_manager = get_config_manager()
    metrics_manager = get_metrics_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    old_token = data.get("token")
    name = data.get("name")

    if not old_token or not name:
        return "Token and name required", 400

    config_manager.revoke_api_token(old_token)
    config_manager.add_api_token(name)

    tokens = config_manager.get_all_tokens()
    user_stats = metrics_manager.data.get("users", {})

    return str(create_users_table(tokens, user_stats))


@ui_bp.route("/users/rate-limits", methods=["POST"])
def update_rate_limits():
    config_manager = get_config_manager()
    metrics_manager = get_metrics_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    token = data.get("token")
    name = data.get("name")

    if not token:
        return "Token required", 400

    tokens = config_manager.get_all_tokens()

    for token_entry in tokens:
        if token_entry.get("token") == token:
            rate_limits = {}

            try:
                if data.get("requests_per_minute"):
                    rate_limits["requests_per_minute"] = int(
                        data.get("requests_per_minute")
                    )
                if data.get("requests_per_hour"):
                    rate_limits["requests_per_hour"] = int(
                        data.get("requests_per_hour")
                    )
                if data.get("requests_per_day"):
                    rate_limits["requests_per_day"] = int(data.get("requests_per_day"))
                if data.get("tokens_per_minute"):
                    rate_limits["tokens_per_minute"] = int(
                        data.get("tokens_per_minute")
                    )
                if data.get("tokens_per_day"):
                    rate_limits["tokens_per_day"] = int(data.get("tokens_per_day"))
            except ValueError:
                return "Invalid number format", 400

            if rate_limits:
                token_entry["rate_limits"] = rate_limits
            elif "rate_limits" in token_entry:
                del token_entry["rate_limits"]

            config_manager.save_config()

            tokens = config_manager.get_all_tokens()
            user_stats = metrics_manager.data.get("users", {})
            return str(create_users_table(tokens, user_stats))

    return "Token not found", 404


@ui_bp.route("/users/rate-limits/remove", methods=["POST"])
def remove_rate_limits():
    config_manager = get_config_manager()
    metrics_manager = get_metrics_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    token = data.get("token")

    if not token:
        return "Token required", 400

    tokens = config_manager.get_all_tokens()

    for token_entry in tokens:
        if token_entry.get("token") == token:
            if "rate_limits" in token_entry:
                del token_entry["rate_limits"]
                config_manager.save_config()

                tokens = config_manager.get_all_tokens()
                user_stats = metrics_manager.data.get("users", {})
                return str(create_users_table(tokens, user_stats))
            else:
                return "No rate limits to remove", 400

    return "Token not found", 404


@ui_bp.route("/reveal-token/<int:index>", methods=["GET"])
def reveal_token(index):
    config_manager = get_config_manager()
    tokens = config_manager.get_all_tokens()
    if 0 <= index < len(tokens):
        token_value = tokens[index].get("token", "")
        return f'<code id="token-{index}" style="background: #f3f4f6; padding: 0.5rem 1rem; border-radius: 4px; font-family: monospace;">{token_value}</code>'
    return "Token not found", 404
