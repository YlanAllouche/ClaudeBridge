from flask import Response, jsonify, request

from ..dependencies import (
    get_accounts_manager,
    get_config_manager,
    get_metrics_manager,
    get_web_session_poller,
)
from . import api_bp

# NOTE: Consider keeping even when prometheus exporter is disabled


@api_bp.route("/health", methods=["OPTIONS", "GET"])
def health():
    if request.method == "OPTIONS":
        return "", 200
    return jsonify({"status": "healthy"})


@api_bp.route("/metrics", methods=["GET"])
def metrics():
    config_manager = get_config_manager()
    metrics_manager = get_metrics_manager()
    accounts_manager = get_accounts_manager()
    web_session_poller = get_web_session_poller()

    if not config_manager.config.get("metrics_endpoint_enabled", False):
        return jsonify({"error": "Metrics endpoint is disabled"}), 403

    from claudebridge.services.prometheus_exporter import format_prometheus_metrics

    summary = metrics_manager.get_metrics_summary()
    active_account = accounts_manager.get_active_account()
    web_usage_data = (
        web_session_poller.get_usage_data(active_account["account_id"])
        if active_account
        else None
    )
    account_name = active_account.get("account_name") if active_account else None
    prometheus_output = format_prometheus_metrics(summary, web_usage_data, account_name)

    return Response(prometheus_output, mimetype="text/plain")
