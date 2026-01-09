import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from .anthropic_oauth_client import AnthropicAPIError, AnthropicOAuthClient
from .config_manager import ConfigManager
from .logger import logger
from .oauth_manager import OAuthManager

# TODO: Need a rewrite - remnants from faking browser session era


class ClaudeService:
    def __init__(
        self, config_manager: Optional[ConfigManager] = None, accounts_manager=None
    ):
        self.accounts_manager = accounts_manager
        self.config_manager = config_manager or ConfigManager()

        access_token = None
        if self.accounts_manager:
            access_token = self.accounts_manager.get_valid_access_token()

        if not access_token:
            env_token = os.getenv("CLAUDE_OAUTH_TOKEN")
            if env_token:
                logger.debug("Using token from environment variable")
                self.client = AnthropicOAuthClient(env_token)
            else:
                raise ValueError(
                    "No valid OAuth token found. Please authenticate first."
                )
        else:
            logger.debug("Using token from accounts manager with fetch wrapper")
            self.client = AnthropicOAuthClient(self.accounts_manager)

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-4-5-sonnet",
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        name_mapping: Optional[dict] = None,
    ) -> Dict[str, Any]:
        try:
            kwargs = {}
            if tools:
                kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

            response = self.client.completion(
                model=model, messages=messages, stream=False, **kwargs
            )

            usage = getattr(response, "usage", None)
            message = response.choices[0].message

            # Build message dict
            message_dict = {"role": "assistant", "content": message.content}

            # Add tool_calls if present
            if hasattr(message, "tool_calls") and message.tool_calls:
                message_dict["tool_calls"] = message.tool_calls
                if name_mapping:
                    message_dict["tool_calls"] = (
                        AnthropicOAuthClient.restore_tool_names_from_anthropic(
                            message_dict["tool_calls"], name_mapping
                        )
                    )

            result = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": message_dict,
                        "finish_reason": (
                            "tool_calls"
                            if hasattr(message, "tool_calls") and message.tool_calls
                            else "stop"
                        ),
                    }
                ],
                "usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                },
            }

            # Attach headers if available
            if hasattr(response, "headers"):
                result["_response_headers"] = response.headers
                logger.debug(
                    f"Attached headers to response: {list(response.headers.keys()) if response.headers else 'None'}"
                )
            else:
                logger.warning("Response object has no headers attribute")

            return result

        except AnthropicAPIError:
            raise
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-3-5-sonnet-20241022",
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        name_mapping: Optional[dict] = None,
    ) -> Generator[tuple, None, None]:
        try:
            kwargs = {}
            if tools:
                kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

            response = self.client.completion(
                model=model, messages=messages, stream=True, **kwargs
            )

            chat_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            created = int(datetime.now().timestamp())

            usage_data = None
            response_headers = {}
            has_tool_calls = False
            tool_call_buffer = {}

            for chunk in response:
                if hasattr(chunk, "usage") and chunk.usage:
                    usage_data = chunk.usage

                if hasattr(chunk, "headers") and chunk.headers:
                    response_headers = chunk.headers

                if hasattr(chunk, "event_data") and chunk.event_data:
                    event_type = chunk.event_data.get("type")

                    if event_type == "content_block_start":
                        content_block = chunk.event_data.get("content_block", {})
                        if content_block.get("type") == "tool_use":
                            has_tool_calls = True
                            index = chunk.event_data.get("index", 0)
                            tool_name = content_block.get("name", "")
                            if name_mapping and tool_name in name_mapping:
                                tool_name = name_mapping[tool_name]
                            tool_call_buffer[index] = {
                                "id": content_block.get(
                                    "id", f"call_{uuid.uuid4().hex[:8]}"
                                ),
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": "",
                                },
                            }
                            chunk_data = {
                                "id": chat_id,
                                "object": "chat.completion.chunk",
                                "created": created,
                                "model": model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {
                                            "tool_calls": [
                                                {
                                                    "index": index,
                                                    "id": tool_call_buffer[index]["id"],
                                                    "type": "function",
                                                    "function": {
                                                        "name": tool_call_buffer[index][
                                                            "function"
                                                        ]["name"],
                                                        "arguments": "",
                                                    },
                                                }
                                            ]
                                        },
                                        "finish_reason": None,
                                    }
                                ],
                            }
                            yield (f"data: {json.dumps(chunk_data)}\n\n", None)

                    elif event_type == "content_block_delta":
                        delta = chunk.event_data.get("delta", {})
                        if delta.get("type") == "input_json_delta":
                            index = chunk.event_data.get("index", 0)
                            partial_json = delta.get("partial_json", "")
                            if index in tool_call_buffer:
                                tool_call_buffer[index]["function"][
                                    "arguments"
                                ] += partial_json
                                chunk_data = {
                                    "id": chat_id,
                                    "object": "chat.completion.chunk",
                                    "created": created,
                                    "model": model,
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {
                                                "tool_calls": [
                                                    {
                                                        "index": index,
                                                        "function": {
                                                            "arguments": partial_json
                                                        },
                                                    }
                                                ]
                                            },
                                            "finish_reason": None,
                                        }
                                    ],
                                }
                                yield (f"data: {json.dumps(chunk_data)}\n\n", None)

                if chunk.choices[0].delta.content:
                    chunk_data = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": chunk.choices[0].delta.content},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield (f"data: {json.dumps(chunk_data)}\n\n", None)

            final_chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "tool_calls" if has_tool_calls else "stop",
                    }
                ],
            }
            yield (f"data: {json.dumps(final_chunk)}\n\n", None)
            yield (f"data: [DONE]\n\n", (usage_data, response_headers))

        except AnthropicAPIError:
            raise
        except Exception as e:
            error_chunk = {
                "error": {"message": f"Claude API error: {str(e)}", "type": "api_error"}
            }
            yield (f"data: {json.dumps(error_chunk)}\n\n", None)

    def list_models(self) -> Dict[str, Any]:
        claude_models = self.config_manager.get_models()

        return {"object": "list", "data": claude_models}

    def messages_create(
        self,
        messages: List[Dict[str, Any]],
        model: str = "claude-4-5-sonnet",
        stream: bool = False,
        **kwargs,
    ) -> Any:
        """
        Native Anthropic Messages API format
        Returns raw Anthropic response
        """
        try:
            response = self.client.messages_create(
                model=model, messages=messages, stream=stream, **kwargs
            )
            return response
        except AnthropicAPIError:
            raise
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")
