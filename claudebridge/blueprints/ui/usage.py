from flask import request

from claudebridge.blueprints.dependencies import (
    get_accounts_manager,
    get_metrics_manager,
    get_web_session_poller,
)
from claudebridge.services.ui import create_layout, create_usage_page
from claudebridge.services.ui.usage import (
    create_usage_content,
    create_web_session_stats_content,
)

from . import ui_bp


@ui_bp.route("/usage", methods=["GET"])
def ui_usage():
    metrics_manager = get_metrics_manager()
    accounts_manager = get_accounts_manager()
    web_session_poller = get_web_session_poller()

    metrics_summary = metrics_manager.get_metrics_summary()
    active_account = accounts_manager.get_active_account()
    web_usage_data = (
        web_session_poller.get_usage_data(active_account["account_id"])
        if active_account
        else None
    )
    account_name = active_account.get("account_name") if active_account else None
    content = create_usage_page(metrics_summary, web_usage_data, account_name)

    if request.headers.get("HX-Request"):
        return str(content)

    return str(create_layout(content, "Usage - ClaudeBridge", "usage"))


@ui_bp.route("/usage/content", methods=["GET"])
def ui_usage_content():
    metrics_manager = get_metrics_manager()
    accounts_manager = get_accounts_manager()
    web_session_poller = get_web_session_poller()

    metrics_summary = metrics_manager.get_metrics_summary()
    active_account = accounts_manager.get_active_account()
    web_usage_data = (
        web_session_poller.get_usage_data(active_account["account_id"])
        if active_account
        else None
    )
    account_name = active_account.get("account_name") if active_account else None
    return str(create_usage_content(metrics_summary, web_usage_data, account_name))


@ui_bp.route("/usage/real", methods=["GET"])
def ui_usage_real():
    metrics_manager = get_metrics_manager()
    accounts_manager = get_accounts_manager()
    web_session_poller = get_web_session_poller()

    metrics_summary = metrics_manager.get_metrics_summary()
    active_account = accounts_manager.get_active_account()

    if not active_account or not active_account.get("web_session_key"):
        return ""

    web_usage_data = web_session_poller.get_usage_data(active_account["account_id"])

    if not web_usage_data:
        return ""

    return str(create_web_session_stats_content(web_usage_data, metrics_summary))
