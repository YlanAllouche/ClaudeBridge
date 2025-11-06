import time

from flask import request

from claudebridge.services.claude_service import ClaudeService
from claudebridge.services.logger import logger
from claudebridge.services.ui import create_layout
from claudebridge.services.ui.models import (
    create_model_row,
    create_models_page,
    create_models_table,
)

from ..dependencies import get_accounts_manager, get_config_manager
from . import ui_bp


@ui_bp.route("/models", methods=["GET"])
def ui_models():
    config_manager = get_config_manager()

    all_models = config_manager.get_all_models_with_status()
    models_data = {"data": all_models}

    content = create_models_page(models_data, config_manager)

    if request.headers.get("HX-Request"):
        return str(content)

    return str(create_layout(content, "Models - ClaudeBridge", "models"))


@ui_bp.route("/models/block", methods=["POST"])
def block_model():
    config_manager = get_config_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    model_id = data.get("model_id")

    if model_id:
        config_manager.add_blocked_model(model_id)

        models_data = config_manager.get_all_models_with_status()
        custom_models = config_manager.config.get("models", {}).get("custom", [])
        blocked_models = config_manager.config.get("models", {}).get("blocked", [])
        blocked_ids = set(blocked_models)

        all_models = []
        for model in models_data:
            all_models.append(
                {
                    "id": model["id"],
                    "created": model.get("created", 0),
                    "status": "blocked" if model["id"] in blocked_ids else "available",
                    "type": "base",
                }
            )
        for model in custom_models:
            all_models.append(
                {
                    "id": model["id"],
                    "created": model.get("created", 0),
                    "status": "custom",
                    "type": "custom",
                }
            )

        return str(create_models_table(all_models))

    return "Model ID required", 400


@ui_bp.route("/models/unblock", methods=["POST"])
def unblock_model():
    config_manager = get_config_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    model_id = data.get("model_id")

    if model_id:
        config_manager.remove_blocked_model(model_id)

        models_data = config_manager.get_all_models_with_status()
        custom_models = config_manager.config.get("models", {}).get("custom", [])
        blocked_models = config_manager.config.get("models", {}).get("blocked", [])
        blocked_ids = set(blocked_models)

        all_models = []
        for model in models_data:
            all_models.append(
                {
                    "id": model["id"],
                    "created": model.get("created", 0),
                    "status": "blocked" if model["id"] in blocked_ids else "available",
                    "type": "base",
                }
            )
        for model in custom_models:
            all_models.append(
                {
                    "id": model["id"],
                    "created": model.get("created", 0),
                    "status": "custom",
                    "type": "custom",
                }
            )

        return str(create_models_table(all_models))

    return "Model ID required", 400


@ui_bp.route("/models/custom/remove", methods=["POST"])
def delete_custom_model():
    config_manager = get_config_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    model_id = data.get("model_id")

    if model_id:
        config_manager.remove_custom_model(model_id)

        models_data = config_manager.get_all_models_with_status()
        custom_models = config_manager.config.get("models", {}).get("custom", [])
        blocked_models = config_manager.config.get("models", {}).get("blocked", [])
        blocked_ids = set(blocked_models)

        all_models = []
        for model in models_data:
            all_models.append(
                {
                    "id": model["id"],
                    "created": model.get("created", 0),
                    "status": "blocked" if model["id"] in blocked_ids else "available",
                    "type": "base",
                }
            )
        for model in custom_models:
            all_models.append(
                {
                    "id": model["id"],
                    "created": model.get("created", 0),
                    "status": "custom",
                    "type": "custom",
                }
            )

        return str(create_models_table(all_models))

    return "Model ID required", 400


@ui_bp.route("/models/custom/add", methods=["POST"])
def add_custom_model():
    config_manager = get_config_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    model_id = data.get("model_id", "").strip()

    if not model_id:
        return "Model ID required", 400

    model_config = {
        "id": model_id,
        "object": "model",
        "created": int(time.time()),
        "owned_by": "custom",
    }

    config_manager.add_custom_model(model_config)

    models_data = config_manager.get_all_models_with_status()
    custom_models = config_manager.config.get("models", {}).get("custom", [])
    blocked_models = config_manager.config.get("models", {}).get("blocked", [])
    blocked_ids = set(blocked_models)

    all_models = []
    for model in models_data:
        all_models.append(
            {
                "id": model["id"],
                "created": model.get("created", 0),
                "status": "blocked" if model["id"] in blocked_ids else "available",
                "type": "base",
            }
        )
    for model in custom_models:
        all_models.append(
            {
                "id": model["id"],
                "created": model.get("created", 0),
                "status": "custom",
                "type": "custom",
            }
        )

    return str(create_models_table(all_models))


@ui_bp.route("/models/test", methods=["POST"])
def test_model():
    config_manager = get_config_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    model_id = data.get("model_id")

    if not model_id:
        return "Model ID required", 400

    frontend_token_info = next(
        (t for t in config_manager.get_all_tokens() if t.get("name") == "frontend"),
        None,
    )

    if not frontend_token_info:
        return "Frontend token not found", 500

    frontend_token = frontend_token_info.get("token")

    try:
        import requests

        base_url = request.host_url.rstrip('/')
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {frontend_token}",
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": "hello"}],
            },
            timeout=30,
        )

        test_succeeded = response.status_code == 200

    except Exception as e:
        logger.error(f"Model test failed: {e}")
        test_succeeded = False

    blocked_models = config_manager.config.get("models", {}).get("blocked", [])
    custom_models = config_manager.config.get("models", {}).get("custom", [])

    if model_id in blocked_models:
        status = "blocked"
    elif any(m.get("id") == model_id for m in custom_models):
        status = "custom"
    else:
        status = "available"

    models_list = config_manager.get_all_models_with_status()
    model = next((m for m in models_list if m["id"] == model_id), None)

    if not model:
        model = next((m for m in custom_models if m.get("id") == model_id), None)
        if not model:
            return "Model not found", 404

    model_dict = {
        "id": model_id,
        "created": model.get("created", 0) if isinstance(model, dict) else 0,
        "status": status,
        "type": "custom" if status == "custom" else "base",
    }

    test_result = "success" if test_succeeded else "error"
    rows = create_model_row(model_dict, 0, test_result=test_result)
    return "".join(str(row) for row in rows)


@ui_bp.route("/models/cost/set", methods=["POST"])
def set_model_cost():
    config_manager = get_config_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    model_id = data.get("model_id", "").strip()
    input_cost = data.get("input_cost", "").strip()
    output_cost = data.get("output_cost", "").strip()

    if not model_id or not input_cost or not output_cost:
        return "Model ID and costs required", 400

    try:
        input_cost_float = float(input_cost)
        output_cost_float = float(output_cost)
    except ValueError:
        return "Invalid cost values", 400

    config_manager.set_model_cost(model_id, input_cost_float, output_cost_float)

    models_data = config_manager.get_all_models_with_status()
    custom_models = config_manager.config.get("models", {}).get("custom", [])
    blocked_models = config_manager.config.get("models", {}).get("blocked", [])
    blocked_ids = set(blocked_models)

    all_models = []
    for model in models_data:
        all_models.append(
            {
                "id": model["id"],
                "created": model.get("created", 0),
                "status": "blocked" if model["id"] in blocked_ids else "available",
                "type": "base",
            }
        )
    for model in custom_models:
        all_models.append(
            {
                "id": model["id"],
                "created": model.get("created", 0),
                "status": "custom",
                "type": "custom",
            }
        )

    return str(create_models_table(all_models))
