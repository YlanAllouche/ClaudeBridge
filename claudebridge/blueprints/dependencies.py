from flask import current_app, g, jsonify, request


def get_config_manager():
    return current_app.config["config_manager"]


def get_accounts_manager():
    return current_app.config["accounts_manager"]


def get_oauth_manager():
    return current_app.config["oauth_manager"]


def get_metrics_manager():
    return current_app.config["metrics_manager"]


def get_rate_limiter():
    return current_app.config["rate_limiter"]


def get_web_session_poller():
    return current_app.config["web_session_poller"]


def get_active_account_id() -> str:
    accounts_manager = get_accounts_manager()
    active_account = accounts_manager.get_active_account()
    if active_account:
        return active_account["account_id"]
    return "default"


def verify_api_token():
    config_manager = get_config_manager()
    metrics_manager = get_metrics_manager()

    auth_header = request.headers.get("Authorization", "")
    api_key_header = request.headers.get("x-api-key", "")

    if not config_manager.config.get("api_tokens", {}).get("enabled", False):
        g.token_name = "anonymous"
        g.token_info = {"name": "anonymous"}
        g.auth_type = "none"
        return None

    token = None
    auth_type = None

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        auth_type = "bearer"
    elif api_key_header:
        token = api_key_header
        auth_type = "x-api-key"
    else:
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token_info = config_manager.verify_api_token(token)

    if not token_info:
        metrics_manager.log_request(
            "error",
            "unknown",
            get_active_account_id(),
            g.get("token_name", "unknown"),
            error_type="unknown_error",
        )
        return jsonify({"error": "Invalid API token"}), 401

    g.token_name = token_info["name"]
    g.token_info = token_info
    g.auth_type = auth_type
    return None
