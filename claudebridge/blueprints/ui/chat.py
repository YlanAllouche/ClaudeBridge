from flask import current_app, request

from claudebridge.blueprints.dependencies import (
    get_accounts_manager,
    get_config_manager,
)
from claudebridge.services.claude_service import ClaudeService
from claudebridge.services.ui import create_chat_page, create_layout

from . import ui_bp


@ui_bp.route("/chat", methods=["GET"])
def ui_chat():
    config_manager = get_config_manager()
    accounts_manager = get_accounts_manager()

    frontend_token_value = current_app.config.get("frontend_token_value")
    chat_token = frontend_token_value

    claude_service = ClaudeService(config_manager, accounts_manager)
    models_data = claude_service.list_models()
    models = models_data.get("data", [])

    content = create_chat_page(models, chat_token)

    if request.headers.get("HX-Request"):
        return str(content)

    return str(create_layout(content, "Chat - ClaudeBridge", "chat"))
