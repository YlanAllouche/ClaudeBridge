import json
import time

from flask import Response, g, jsonify, request

from claudebridge.services.anthropic_oauth_client import (
    AnthropicAPIError,
    AnthropicOAuthClient,
)
from claudebridge.services.claude_service import ClaudeService
from claudebridge.services.logger import logger

from ..dependencies import (
    get_accounts_manager,
    get_active_account_id,
    get_config_manager,
    get_metrics_manager,
    get_rate_limiter,
    verify_api_token,
)
from . import api_bp

# TODO: consider DRY-ing or keeping the redundancy for clea separation betwen the OpenAI logic and the Anthropic one.
# TODO: P1: split this


@api_bp.route("/v1/chat/completions", methods=["OPTIONS"])
@api_bp.route("/v1/messages", methods=["OPTIONS"])
@api_bp.route("/v1/models", methods=["OPTIONS"])
def handle_preflight():
    return "", 200


@api_bp.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    start_time = time.time()
    config_manager = get_config_manager()
    accounts_manager = get_accounts_manager()
    metrics_manager = get_metrics_manager()
    rate_limiter = get_rate_limiter()

    try:
        auth_error = verify_api_token()
        if auth_error:
            return auth_error

        token_name = g.token_name
        token_info = g.token_info

        data = request.get_json()

        if not data:
            metrics_manager.log_request(
                "error",
                "unknown",
                get_active_account_id(),
                token_name,
                error_type="invalid_request",
            )
            return jsonify({"error": "No JSON data provided"}), 400

        messages = data.get("messages", [])
        stream = data.get("stream", False)
        model = data.get("model", "claude-4-5-sonnet")
        tools = data.get("tools")
        tool_choice = data.get("tool_choice")

        name_mapping = {}
        reverse_name_mapping = {}
        if tools:
            tools, name_mapping = AnthropicOAuthClient.rename_tools_for_anthropic(tools)
            reverse_name_mapping = {v: k for k, v in name_mapping.items()}

        if tool_choice and isinstance(tool_choice, dict):
            if tool_choice.get("function"):
                func_name = tool_choice["function"].get("name")
                if func_name and func_name in reverse_name_mapping:
                    tool_choice["function"]["name"] = reverse_name_mapping[func_name]

        logger.debug(
            f"[OPENAI] Model: '{model}' | Stream: {stream} | Tools: {bool(tools)} | Auth: Bearer | Token: {token_name}"
        )
        logger.trace(f"[OPENAI] Incoming request headers: {dict(request.headers)}")
        logger.trace(f"[OPENAI] Incoming request body: {data}")

        if not messages:
            metrics_manager.log_request(
                "error",
                model,
                get_active_account_id(),
                token_name,
                error_type="invalid_request",
            )
            return jsonify({"error": "No messages provided"}), 400

        rate_limits = token_info.get("rate_limits")
        allowed, limit_type, headers = rate_limiter.check_limits(
            token_name, rate_limits, token_count=0
        )

        if not allowed:
            metrics_manager.track_rate_limit(token_name, limit_type or "unknown")
            metrics_manager.log_request(
                "error",
                model,
                get_active_account_id(),
                token_name,
                error_type="rate_limit_exceeded",
            )
            response = jsonify(
                {
                    "error": {
                        "message": f"Rate limit exceeded: {limit_type}",
                        "type": "rate_limit_error",
                        "limit_type": limit_type,
                    }
                }
            )
            response.status_code = 429
            if headers:
                for key, value in headers.items():
                    response.headers[key] = value
            return response

        default_system = {
            "role": "system",
            "content": "You are Claude Code, Anthropic's official CLI for Claude.",
        }

        user_system_messages = [msg for msg in messages if msg.get("role") == "system"]
        non_system_messages = [msg for msg in messages if msg.get("role") != "system"]

        if user_system_messages:
            combined_content = default_system["content"]
            for msg in user_system_messages:
                combined_content += "\n\n" + msg.get("content", "")
            default_system["content"] = combined_content

        messages = [default_system] + non_system_messages

        claude_service = ClaudeService(config_manager, accounts_manager)

        anthropic_tools = None
        anthropic_tool_choice = None
        if tools:
            anthropic_tools = AnthropicOAuthClient.convert_openai_tools_to_anthropic(
                tools
            )
            if tool_choice:
                anthropic_tool_choice = (
                    AnthropicOAuthClient.convert_openai_tool_choice_to_anthropic(
                        tool_choice
                    )
                )

        if stream:
            account_id = get_active_account_id()

            def generate_with_tracking():
                try:
                    usage_data = None
                    response_headers = {}

                    for chunk_data, chunk_usage in claude_service.chat_stream(
                        messages,
                        model,
                        tools=anthropic_tools,
                        tool_choice=anthropic_tool_choice,
                        name_mapping=name_mapping,
                    ):
                        if chunk_usage:
                            if isinstance(chunk_usage, tuple):
                                usage_data, response_headers = chunk_usage
                            else:
                                usage_data = chunk_usage
                        yield chunk_data

                    input_tokens = 0
                    output_tokens = 0
                    if usage_data:
                        input_tokens = (
                            getattr(usage_data, "input_tokens", 0)
                            if hasattr(usage_data, "input_tokens")
                            else usage_data.get("input_tokens", 0)
                        )
                        output_tokens = (
                            getattr(usage_data, "output_tokens", 0)
                            if hasattr(usage_data, "output_tokens")
                            else usage_data.get("output_tokens", 0)
                        )

                    metrics_manager.log_request(
                        "success",
                        model,
                        account_id,
                        token_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        response_headers=response_headers,
                    )
                    accounts_manager.record_success(account_id)

                except AnthropicAPIError as e:
                    logger.error(f"Anthropic API error during streaming: {str(e)}")

                    if e.status_code == 429:
                        response_headers = (
                            e.response_headers if hasattr(e, "response_headers") else {}
                        )
                        metrics_manager.log_request(
                            "ooq",
                            model,
                            account_id,
                            token_name,
                            response_headers=response_headers,
                        )
                        accounts_manager.record_out_of_quota(
                            account_id, response_headers
                        )

                        error_event = f'data: {json.dumps({"error": {"message": e.error_message, "type": "rate_limit_error", "code": "rate_limit_error"}})}\n\n'
                        yield error_event
                    else:
                        metrics_manager.log_request(
                            "error",
                            model,
                            account_id,
                            token_name,
                            error_type="api_error",
                        )
                        error_event = f'data: {json.dumps({"error": {"message": e.error_message, "type": "api_error", "code": str(e.status_code or "unknown")}})}\n\n'
                        yield error_event

                except Exception as e:
                    logger.error(f"Streaming error: {str(e)}")
                    metrics_manager.log_request(
                        "error",
                        model,
                        account_id,
                        token_name,
                        error_type="stream_error",
                    )
                    error_event = f'data: {json.dumps({"error": {"message": str(e), "type": "internal_error"}})}\n\n'
                    yield error_event

            return Response(
                generate_with_tracking(),
                mimetype="text/event-stream",
                headers={"Cache-Control": "no-cache"},
            )
        else:
            response_data = claude_service.chat(
                messages,
                model,
                tools=anthropic_tools,
                tool_choice=anthropic_tool_choice,
                name_mapping=name_mapping,
            )

            duration = time.time() - start_time
            prompt_tokens = response_data.get("usage", {}).get("prompt_tokens", 0)
            completion_tokens = response_data.get("usage", {}).get(
                "completion_tokens", 0
            )
            total_tokens = prompt_tokens + completion_tokens

            rate_limiter.record_request(token_name, total_tokens)

            account_id = get_active_account_id()

            response_headers = response_data.get("_response_headers", {})

            metrics_manager.log_request(
                "success",
                model,
                account_id,
                token_name,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                response_headers=response_headers,
            )
            accounts_manager.record_success(account_id)

            if "_response_headers" in response_data:
                del response_data["_response_headers"]

            response = jsonify(response_data)
            if headers:
                for key, value in headers.items():
                    response.headers[key] = value
            return response

    except AnthropicAPIError as e:
        model_requested = (
            data.get("model", "unknown") if "data" in locals() else "unknown"
        )
        msg_count = len(data.get("messages", [])) if "data" in locals() else 0
        token_name = g.get("token_name", "unknown")
        account_id = get_active_account_id()

        logger.error(
            "Anthropic API Error in chat_completions",
            model=model_requested,
            status_code=e.status_code,
            error_type=e.error_type,
        )

        openai_error_type = "api_error"
        http_status = e.status_code or 500

        if e.status_code == 429:
            openai_error_type = "rate_limit_error"

            response_headers = (
                e.response_headers if hasattr(e, "response_headers") else {}
            )
            metrics_manager.log_request(
                "ooq",
                model_requested,
                account_id,
                token_name,
                response_headers=response_headers,
            )
            accounts_manager.record_out_of_quota(account_id, response_headers)

        elif e.status_code == 401:
            openai_error_type = "authentication_error"
            metrics_manager.log_request(
                "error",
                model_requested,
                account_id,
                token_name,
                error_type="unauthorized",
            )
            accounts_manager.record_failure(account_id)
        elif e.status_code == 403:
            if (
                e.error_type == "permission_error"
                or "quota" in str(e.error_message).lower()
                or "subscription" in str(e.error_message).lower()
            ):
                openai_error_type = "insufficient_quota"
                http_status = 429
                metrics_manager.log_request(
                    "error",
                    model_requested,
                    account_id,
                    token_name,
                    error_type="quota_exceeded",
                )
            else:
                openai_error_type = "permission_error"
                metrics_manager.log_request(
                    "error",
                    model_requested,
                    account_id,
                    token_name,
                    error_type="forbidden",
                )
            accounts_manager.record_failure(account_id)
        elif e.status_code == 400:
            openai_error_type = "invalid_request_error"
            metrics_manager.log_request(
                "error",
                model_requested,
                account_id,
                token_name,
                error_type="invalid_request",
            )
            accounts_manager.record_failure(account_id)
        elif e.status_code == 529:
            openai_error_type = "service_unavailable"
            http_status = 503
            metrics_manager.log_request(
                "error",
                model_requested,
                account_id,
                token_name,
                error_type="overloaded",
            )
            accounts_manager.record_failure(account_id)
        else:
            metrics_manager.log_request(
                "error",
                model_requested,
                account_id,
                token_name,
                error_type="server_error",
            )
            accounts_manager.record_failure(account_id)

        return (
            jsonify(
                {
                    "error": {
                        "message": e.error_message,
                        "type": openai_error_type,
                        "code": openai_error_type,
                    }
                }
            ),
            http_status,
        )

    except Exception as e:
        model_requested = "unknown"
        msg_count = 0
        try:
            if "data" in locals() and data:
                model_requested = data.get("model", "unknown")
                msg_count = len(data.get("messages", []))
        except:
            pass
        logger.error(f"[OPENAI] Unexpected Error: {str(e)}")
        logger.info(f"   Request: model={model_requested}, messages={msg_count}")

        metrics_manager.log_request(
            "error",
            model_requested,
            get_active_account_id(),
            g.get("token_name", "unknown"),
            error_type="internal_server_error",
        )
        return (
            jsonify(
                {
                    "error": {
                        "message": str(e),
                        "type": "api_error",
                        "code": "internal_error",
                    }
                }
            ),
            500,
        )


@api_bp.route("/v1/messages", methods=["POST"])
def messages_create():
    start_time = time.time()
    config_manager = get_config_manager()
    accounts_manager = get_accounts_manager()
    metrics_manager = get_metrics_manager()
    rate_limiter = get_rate_limiter()

    try:
        auth_error = verify_api_token()
        if auth_error:
            return auth_error

        token_name = g.token_name
        token_info = g.token_info

        data = request.get_json()

        if not data:
            metrics_manager.log_request(
                "error",
                "unknown",
                get_active_account_id(),
                token_name,
                error_type="invalid_request",
            )
            return (
                jsonify(
                    {
                        "error": {
                            "type": "invalid_request_error",
                            "message": "No JSON data provided",
                        }
                    }
                ),
                400,
            )

        messages = data.get("messages", [])
        stream = data.get("stream", False)
        model = data.get("model", "claude-3-5-sonnet-20241022")
        max_tokens = data.get("max_tokens", 4096)

        logger.debug(
            f"[ANTHROPIC] Model: '{model}' | Stream: {stream} | Auth: x-api-key | Token: {token_name}"
        )
        logger.trace(f"[ANTHROPIC] Incoming request headers: {dict(request.headers)}")
        logger.trace(f"[ANTHROPIC] Incoming request body: {data}")

        if not messages:
            metrics_manager.log_request(
                "error",
                model,
                get_active_account_id(),
                token_name,
                error_type="invalid_request",
            )
            return (
                jsonify(
                    {
                        "error": {
                            "type": "invalid_request_error",
                            "message": "messages is required",
                        }
                    }
                ),
                400,
            )

        rate_limits = token_info.get("rate_limits")
        allowed, limit_type, headers = rate_limiter.check_limits(
            token_name, rate_limits, token_count=0
        )

        if not allowed:
            metrics_manager.track_rate_limit(token_name, limit_type or "unknown")
            metrics_manager.log_request(
                "error",
                model,
                get_active_account_id(),
                token_name,
                error_type="rate_limit_exceeded",
            )
            response = jsonify(
                {
                    "error": {
                        "type": "rate_limit_error",
                        "message": f"Rate limit exceeded: {limit_type}",
                    }
                }
            )
            response.status_code = 429
            if headers:
                for key, value in headers.items():
                    response.headers[key] = value
            return response

        claude_service = ClaudeService(config_manager, accounts_manager)

        kwargs = {}
        for key in [
            "system",
            "temperature",
            "top_p",
            "top_k",
            "stop_sequences",
            "metadata",
            "tools",
        ]:
            if key in data:
                kwargs[key] = data[key]

        kwargs["max_tokens"] = max_tokens

        if config_manager.config.get("spoof_on_anthropic", False):
            spoof_system = "You are Claude Code, Anthropic's official CLI for Claude."
            if "system" in kwargs:
                if isinstance(kwargs["system"], str):
                    kwargs["system"] = spoof_system + "\n\n" + kwargs["system"]
                elif isinstance(kwargs["system"], list):
                    kwargs["system"] = [
                        {"type": "text", "text": spoof_system}
                    ] + kwargs["system"]
            else:
                kwargs["system"] = spoof_system

        if stream:
            account_id = get_active_account_id()

            def generate_with_tracking():
                try:
                    usage_data = None
                    response_headers = {}

                    for line, line_usage in claude_service.messages_create(
                        messages, model, stream=True, **kwargs
                    ):
                        if line_usage:
                            if isinstance(line_usage, tuple):
                                usage_data, response_headers = line_usage
                            else:
                                usage_data = line_usage
                        yield line

                    input_tokens = (
                        usage_data.get("input_tokens", 0) if usage_data else 0
                    )
                    output_tokens = (
                        usage_data.get("output_tokens", 0) if usage_data else 0
                    )

                    metrics_manager.log_request(
                        "success",
                        model,
                        account_id,
                        token_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        response_headers=response_headers,
                    )
                    accounts_manager.record_success(account_id)

                except AnthropicAPIError as e:
                    logger.error(f"Anthropic API error during streaming: {str(e)}")

                    if e.status_code == 429:
                        response_headers = (
                            e.response_headers if hasattr(e, "response_headers") else {}
                        )
                        metrics_manager.log_request(
                            "ooq",
                            model,
                            account_id,
                            token_name,
                            response_headers=response_headers,
                        )
                        accounts_manager.record_out_of_quota(
                            account_id, response_headers
                        )

                        error_event = f'event: error\ndata: {json.dumps({"type": "error", "error": {"type": "rate_limit_error", "message": e.error_message}})}\n\n'
                        yield error_event
                    else:
                        metrics_manager.log_request(
                            "error",
                            model,
                            account_id,
                            token_name,
                            error_type="api_error",
                        )
                        error_event = f'event: error\ndata: {json.dumps({"type": "error", "error": {"type": e.error_type or "api_error", "message": e.error_message}})}\n\n'
                        yield error_event

                except Exception as e:
                    logger.error(f"Streaming error: {str(e)}")
                    metrics_manager.log_request(
                        "error",
                        model,
                        account_id,
                        token_name,
                        error_type="stream_error",
                    )
                    error_event = f'event: error\ndata: {json.dumps({"error": {"type": "api_error", "message": str(e)}})}\n\n'
                    yield error_event

            return Response(
                generate_with_tracking(),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "anthropic-version": "2023-06-01",
                },
            )
        else:
            response_data = claude_service.messages_create(
                messages, model, stream=False, **kwargs
            )

            duration = time.time() - start_time
            prompt_tokens = response_data.get("usage", {}).get("input_tokens", 0)
            completion_tokens = response_data.get("usage", {}).get("output_tokens", 0)
            total_tokens = prompt_tokens + completion_tokens

            rate_limiter.record_request(token_name, total_tokens)

            account_id = get_active_account_id()

            response_headers = response_data.get("_response_headers", {})

            metrics_manager.log_request(
                "success",
                model,
                account_id,
                token_name,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                response_headers=response_headers,
            )
            accounts_manager.record_success(account_id)

            if "_response_headers" in response_data:
                del response_data["_response_headers"]

            response = jsonify(response_data)
            response.headers["anthropic-version"] = "2023-06-01"
            if headers:
                for key, value in headers.items():
                    response.headers[key] = value
            return response

    except AnthropicAPIError as e:
        model_requested = (
            data.get("model", "unknown") if "data" in locals() else "unknown"
        )
        msg_count = len(data.get("messages", [])) if "data" in locals() else 0
        token_name = g.get("token_name", "unknown")
        account_id = get_active_account_id()

        logger.error(
            "Anthropic API Error in messages",
            model=model_requested,
            status_code=e.status_code,
            error_type=e.error_type,
        )

        if e.status_code == 429:
            response_headers = (
                e.response_headers if hasattr(e, "response_headers") else {}
            )
            metrics_manager.log_request(
                "ooq",
                model_requested,
                account_id,
                token_name,
                response_headers=response_headers,
            )
            accounts_manager.record_out_of_quota(account_id, response_headers)
        elif e.status_code == 403:
            if (
                "quota" in str(e.error_message).lower()
                or "subscription" in str(e.error_message).lower()
            ):
                metrics_manager.log_request(
                    "error",
                    model_requested,
                    account_id,
                    token_name,
                    error_type="quota_exceeded",
                )
            else:
                metrics_manager.log_request(
                    "error",
                    model_requested,
                    account_id,
                    token_name,
                    error_type="forbidden",
                )
            accounts_manager.record_failure(account_id)
        elif e.status_code == 401:
            metrics_manager.log_request(
                "error",
                model_requested,
                account_id,
                token_name,
                error_type="unauthorized",
            )
            accounts_manager.record_failure(account_id)
        elif e.status_code == 400:
            metrics_manager.log_request(
                "error",
                model_requested,
                account_id,
                token_name,
                error_type="invalid_request",
            )
            accounts_manager.record_failure(account_id)
        elif e.status_code == 529:
            metrics_manager.log_request(
                "error",
                model_requested,
                account_id,
                token_name,
                error_type="overloaded",
            )
            accounts_manager.record_failure(account_id)
        else:
            metrics_manager.log_request(
                "error",
                model_requested,
                account_id,
                token_name,
                error_type="server_error",
            )
            accounts_manager.record_failure(account_id)

        return (
            jsonify(
                {
                    "type": "error",
                    "error": {
                        "type": e.error_type or "api_error",
                        "message": e.error_message,
                    },
                }
            ),
            e.status_code or 500,
        )

    except Exception as e:
        logger.error(f"[ANTHROPIC] Unexpected Error: {str(e)}")
        logger.info(
            f"   Request: model={data.get('model') if 'data' in locals() else 'unknown'}, messages={len(data.get('messages', [])) if 'data' in locals() else 0}"
        )
        model_requested = data.get("model") if "data" in locals() else "unknown"
        metrics_manager.log_request(
            "error",
            model_requested,
            get_active_account_id(),
            g.get("token_name", "unknown"),
            error_type="internal_server_error",
        )
        return (
            jsonify(
                {"type": "error", "error": {"type": "api_error", "message": str(e)}}
            ),
            500,
        )


@api_bp.route("/v1/models", methods=["GET"])
def list_models():
    config_manager = get_config_manager()
    accounts_manager = get_accounts_manager()
    metrics_manager = get_metrics_manager()

    try:
        auth_error = verify_api_token()
        if auth_error:
            return auth_error

        claude_service = ClaudeService(config_manager, accounts_manager)
        models_data = claude_service.list_models()

        auth_type = g.get("auth_type", "bearer")

        if auth_type == "x-api-key":
            anthropic_models = []
            for model in models_data.get("data", []):
                anthropic_models.append(
                    {
                        "type": "model",
                        "id": model["id"],
                        "display_name": model["id"],
                        "created_at": model.get("created", 0),
                    }
                )
            return jsonify({"data": anthropic_models, "has_more": False})
        else:
            return jsonify(models_data)
    except Exception as e:
        metrics_manager.log_request(
            "error",
            "unknown",
            get_active_account_id(),
            g.get("token_name", "unknown"),
            error_type="internal_server_error",
        )
        return jsonify({"error": str(e)}), 500
