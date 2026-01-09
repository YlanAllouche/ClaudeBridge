"""
Custom Anthropic OAuth client for direct API communication
Uses the OAuth fetch wrapper for transparent token management
"""

# TODO:: P1 - Entirely refactor


import json
import uuid
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

import requests

from .logger import logger
from .oauth_fetch_wrapper import OAuthFetchWrapper
from .oauth_manager import OAuthManager


class AnthropicAPIError(Exception):
    """Custom exception for Anthropic API errors with detailed information"""

    def __init__(self, error_info: Dict[str, Any]):
        self.status_code = error_info.get("status_code")
        self.error_type = error_info.get("error_type")
        self.error_message = error_info.get("error_message")
        self.raw_response = error_info.get("raw_response")
        self.error_json = error_info.get("error_json")
        self.response_headers = error_info.get("response_headers", {})

        super().__init__(
            f"Anthropic API error ({self.status_code}): {self.error_message}"
        )


class AnthropicOAuthClient:
    """
    Direct Anthropic API client using OAuth Bearer token authentication
    Uses OAuth fetch wrapper for transparent token management
    """

    @staticmethod
    def convert_openai_tools_to_anthropic(
        openai_tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Convert OpenAI function/tool format to Anthropic tool format

        OpenAI format:
        {
          "type": "function",
          "function": {
            "name": "get_weather",
            "description": "Get weather",
            "parameters": {...}
          }
        }

        Anthropic format:
        {
          "name": "get_weather",
          "description": "Get weather",
          "input_schema": {...}
        }
        """
        if not openai_tools:
            return []

        anthropic_tools = []
        for tool in openai_tools:
            if tool.get("type") == "function":
                func = tool["function"]
                anthropic_tools.append(
                    {
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "input_schema": func.get("parameters", {}),
                    }
                )
            else:
                # Already in Anthropic format or unknown, pass through
                anthropic_tools.append(tool)

        return anthropic_tools

    @staticmethod
    def convert_openai_tool_choice_to_anthropic(
        tool_choice: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Convert OpenAI tool_choice to Anthropic format

        OpenAI:
        - "auto" -> {"type": "auto"}
        - "none" -> None (don't pass parameter)
        - {"type": "function", "function": {"name": "foo"}} -> {"type": "tool", "name": "foo"}

        Anthropic:
        - {"type": "auto"} (default)
        - {"type": "any"} (force tool use)
        - {"type": "tool", "name": "foo"} (specific tool)
        """
        if not tool_choice or tool_choice == "none":
            return None

        if tool_choice == "auto":
            return {"type": "auto"}

        if tool_choice == "required":
            # OpenAI "required" means force a tool call
            return {"type": "any"}

        if isinstance(tool_choice, dict):
            if tool_choice.get("type") == "function":
                func_name = tool_choice.get("function", {}).get("name")
                if func_name:
                    return {"type": "tool", "name": func_name}
            return tool_choice

        return None

    @staticmethod
    def rename_tools_for_anthropic(
        openai_tools: List[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], dict]:
        """
        Rename tools with MCP prefix for obfuscation
        Returns: (renamed_tools, name_mapping)
        where name_mapping is: {"mcp_bash_tool": "bash", ...}
        """
        if not openai_tools:
            return [], {}

        renamed_tools = []
        name_mapping = {}

        for tool in openai_tools:
            renamed_tool = tool.copy()

            if tool.get("type") == "function":
                func = tool["function"]
                original_name = func["name"]
                renamed_name = f"mcp_{original_name}_tool"

                renamed_tool["function"]["name"] = renamed_name
                name_mapping[renamed_name] = original_name
            elif "name" in tool:
                original_name = tool["name"]
                renamed_name = f"mcp_{original_name}_tool"

                renamed_tool["name"] = renamed_name
                name_mapping[renamed_name] = original_name

            renamed_tools.append(renamed_tool)

        return renamed_tools, name_mapping

    @staticmethod
    def restore_tool_names_from_anthropic(data: Any, name_mapping: dict) -> Any:
        """
        Restore original tool names in tool_calls
        Handles both streaming and non-streaming responses
        """
        if not name_mapping:
            return data

        if isinstance(data, dict):
            restored = {}
            for key, value in data.items():
                if key == "name" and value in name_mapping:
                    restored[key] = name_mapping[value]
                elif key == "tool_calls":
                    restored[key] = (
                        AnthropicOAuthClient.restore_tool_names_from_anthropic(
                            value, name_mapping
                        )
                    )
                elif key == "function":
                    restored[key] = (
                        AnthropicOAuthClient.restore_tool_names_from_anthropic(
                            value, name_mapping
                        )
                    )
                elif key == "choices":
                    restored[key] = (
                        AnthropicOAuthClient.restore_tool_names_from_anthropic(
                            value, name_mapping
                        )
                    )
                elif key == "message":
                    restored[key] = (
                        AnthropicOAuthClient.restore_tool_names_from_anthropic(
                            value, name_mapping
                        )
                    )
                elif key == "delta":
                    restored[key] = (
                        AnthropicOAuthClient.restore_tool_names_from_anthropic(
                            value, name_mapping
                        )
                    )
                else:
                    restored[key] = value
            return restored

        elif isinstance(data, list):
            return [
                AnthropicOAuthClient.restore_tool_names_from_anthropic(
                    item, name_mapping
                )
                for item in data
            ]

        return data

        if tool_choice == "auto":
            return {"type": "auto"}

        if tool_choice == "required":
            # OpenAI "required" means force a tool call
            return {"type": "any"}

        if isinstance(tool_choice, dict):
            if tool_choice.get("type") == "function":
                func_name = tool_choice.get("function", {}).get("name")
                if func_name:
                    return {"type": "tool", "name": func_name}
            return tool_choice

        return None

    def __init__(self, token_or_manager):
        self.base_url = "https://api.anthropic.com/v1"

        if isinstance(token_or_manager, str):
            # Legacy mode: direct token string
            if "#" in token_or_manager:
                self.access_token = token_or_manager.split("#")[0]
                self.accounts_manager = None
                self.fetch_wrapper = None
            else:
                self.access_token = token_or_manager
                self.accounts_manager = None
                self.fetch_wrapper = None
        else:
            self.accounts_manager = token_or_manager
            self.fetch_wrapper = OAuthFetchWrapper(self.accounts_manager, timeout=120)
            self.access_token = None  # Will be handled by fetch wrapper

        if self.fetch_wrapper:
            self.session = self.fetch_wrapper.create_session_with_oauth()
        else:
            self.session = requests.Session()

    def _handle_error_response(self, response):
        """Handle and log error responses from Anthropic API"""
        error_detail = response.text
        status_code = response.status_code
        response_headers = dict(response.headers)

        error_type = None
        error_message = error_detail
        error_json = None

        try:
            error_json = response.json()

            if isinstance(error_json, dict) and "error" in error_json:
                error_obj = error_json["error"]
                error_type = error_obj.get("type", "unknown_error")
                error_message = error_obj.get("message", error_detail)
            else:
                error_message = str(error_json)

            logger.error(
                "Anthropic API Error",
                status_code=status_code,
                error_type=error_type,
                error_message=error_message,
                headers=response_headers,
                error_json=error_json,
            )
        except Exception as parse_error:
            logger.error(
                "Anthropic API Error (unparseable response)",
                status_code=status_code,
                raw_response=error_detail,
                headers=response_headers,
                parse_error=str(parse_error),
            )

        error_info = {
            "status_code": status_code,
            "error_type": error_type,
            "error_message": error_message,
            "raw_response": error_detail,
            "error_json": error_json,
            "response_headers": response_headers,
        }

        raise AnthropicAPIError(error_info)

    def _format_messages_for_anthropic(
        self, messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format messages for Anthropic's API format
        Supports both simple string content and complex content blocks (vision, thinking, etc.)
        Converts OpenAI image_url format to Anthropic image format
        Handles OpenAI tool/function message format conversion
        """
        anthropic_messages = []
        system_message = None

        for message in messages:
            role = message.get("role")
            content = message.get("content")

            if role == "system":
                system_message = content
            elif role == "tool":
                anthropic_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.get("tool_call_id"),
                                "content": content,
                            }
                        ],
                    }
                )
            elif role in ["user", "assistant"]:
                converted_content = self._convert_content_format(content)
                msg_dict = {"role": role, "content": converted_content}

                if role == "assistant" and "tool_calls" in message:
                    tool_use_blocks = []
                    if content and isinstance(converted_content, str):
                        tool_use_blocks.append(
                            {"type": "text", "text": converted_content}
                        )

                    # Convert tool_calls to tool_use blocks
                    for tool_call in message["tool_calls"]:
                        if tool_call.get("type") == "function":
                            func = tool_call["function"]
                            tool_use_blocks.append(
                                {
                                    "type": "tool_use",
                                    "id": tool_call.get(
                                        "id", f"toolu_{uuid.uuid4().hex[:8]}"
                                    ),
                                    "name": func["name"],
                                    "input": (
                                        json.loads(func["arguments"])
                                        if isinstance(func["arguments"], str)
                                        else func["arguments"]
                                    ),
                                }
                            )

                    if tool_use_blocks:
                        msg_dict["content"] = tool_use_blocks

                anthropic_messages.append(msg_dict)

        request_data = {"messages": anthropic_messages, "max_tokens": 4096}

        if system_message:
            request_data["system"] = system_message

        return request_data

    def _convert_content_format(self, content):
        """Convert OpenAI content format to Anthropic format
        Handles image_url -> image conversion
        """
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            converted = []
            for block in content:
                if isinstance(block, dict):
                    block_type = block.get("type")

                    if block_type == "image_url":
                        image_url = block.get("image_url", {})
                        url = image_url.get("url", "")

                        if url.startswith("data:"):
                            parts = url.split(",", 1)
                            if len(parts) == 2:
                                header = parts[0]
                                data = parts[1]

                                media_type = "image/png"
                                if "image/jpeg" in header or "image/jpg" in header:
                                    media_type = "image/jpeg"
                                elif "image/gif" in header:
                                    media_type = "image/gif"
                                elif "image/webp" in header:
                                    media_type = "image/webp"

                                converted.append(
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": media_type,
                                            "data": data,
                                        },
                                    }
                                )
                        else:
                            converted.append(
                                {"type": "image", "source": {"type": "url", "url": url}}
                            )
                    else:
                        converted.append(block)
                else:
                    converted.append(block)

            return converted

        return content

    def completion(
        self, model: str, messages: List[Dict[str, Any]], stream: bool = False, **kwargs
    ) -> Any:
        """
        Create a completion using Anthropic's API
        """
        # Remove anthropic/ prefix if present
        if model.startswith("anthropic/"):
            model = model[10:]

        request_data = self._format_messages_for_anthropic(messages)
        request_data["model"] = model
        request_data["stream"] = stream

        for key, value in kwargs.items():
            if key not in ["model", "messages", "stream"]:
                request_data[key] = value

        logger.debug("Making completion request", model=model, stream=stream)
        logger.trace("Request data", request_data=request_data)

        try:
            # Use the OAuth-enabled session for the request
            response = self.session.post(
                f"{self.base_url}/messages", json=request_data, stream=stream
            )

            if not response.ok:
                self._handle_error_response(response)

            if stream:
                return self._handle_stream_response(response)
            else:
                response_json = response.json()
                response_headers = dict(response.headers)
                logger.debug(
                    f"Captured response headers: {list(response_headers.keys())}"
                )
                return self._handle_completion_response(response_json, response_headers)

        except AnthropicAPIError:
            raise
        except Exception as e:
            if "This credential is only authorized for use with Claude Code" in str(e):
                raise Exception("Claude Code spoof failed")
            raise

    def _handle_completion_response(
        self,
        anthropic_response: Dict[str, Any],
        response_headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Preserves all content blocks (text, thinking, tool_use, etc.)
        Converts tool_use blocks to OpenAI tool_calls format
        """

        class CompletionResponse:
            def __init__(self, anthropic_resp, headers=None):
                self.choices = [CompletionChoice(anthropic_resp)]
                self.usage = CompletionUsage(anthropic_resp.get("usage", {}))
                self.raw_response = anthropic_resp
                self.headers = headers or {}

        class CompletionChoice:
            def __init__(self, anthropic_resp):
                self.message = CompletionMessage(anthropic_resp)

        class CompletionMessage:
            def __init__(self, anthropic_resp):
                content_blocks = anthropic_resp.get("content", [])

                if isinstance(content_blocks, list):
                    self.content_blocks = content_blocks
                    self.content = ""
                    self.tool_calls = []

                    for block in content_blocks:
                        if block.get("type") == "text":
                            self.content += block.get("text", "")
                        elif block.get("type") == "tool_use":
                            tool_call = {
                                "id": block.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                                "type": "function",
                                "function": {
                                    "name": block.get("name"),
                                    "arguments": json.dumps(block.get("input", {})),
                                },
                            }
                            self.tool_calls.append(tool_call)

                    # If we have tool calls but no text, set content to None (OpenAI standard?)
                    if self.tool_calls and not self.content:
                        self.content = None

                    # Remove tool_calls attribute if empty for cleaner responses
                    if not self.tool_calls:
                        delattr(self, "tool_calls")
                else:
                    self.content = str(content_blocks)
                    self.content_blocks = [{"type": "text", "text": self.content}]

        class CompletionUsage:
            def __init__(self, usage_data):
                self.prompt_tokens = usage_data.get("input_tokens", 0)
                self.completion_tokens = usage_data.get("output_tokens", 0)
                self.total_tokens = self.prompt_tokens + self.completion_tokens

        return CompletionResponse(anthropic_response, response_headers)

    def _handle_stream_response(self, response) -> Generator[Any, None, None]:
        """Handle streaming response from Anthropic API
        Yields all event types: text, thinking, tool_use, etc.
        """
        response_headers = dict(response.headers)

        class StreamChunk:
            def __init__(
                self,
                content_delta=None,
                finish_reason=None,
                event_data=None,
                usage=None,
                headers=None,
            ):
                self.choices = [StreamChoice(content_delta, finish_reason)]
                self.event_data = event_data
                self.usage = usage
                self.headers = headers or {}

        class StreamChoice:
            def __init__(self, content_delta=None, finish_reason=None):
                self.delta = StreamDelta(content_delta)
                self.finish_reason = finish_reason

        class StreamDelta:
            def __init__(self, content=None):
                self.content = content

        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        event_type = data.get("type")

                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            delta_type = delta.get("type")

                            if delta_type == "text_delta":
                                content = delta.get("text", "")
                                if content:
                                    yield StreamChunk(
                                        content_delta=content, event_data=data
                                    )
                            elif delta_type == "thinking_delta":
                                thinking = delta.get("thinking", "")
                                if (
                                    thinking
                                ):  # TODO: Look up how thinkink works - no thinking model on anthropic at the moment it seems
                                    yield StreamChunk(
                                        content_delta=thinking, event_data=data
                                    )
                            elif delta_type == "input_json_delta":
                                yield StreamChunk(content_delta=None, event_data=data)

                        elif event_type == "content_block_start":
                            yield StreamChunk(event_data=data)

                        elif event_type == "content_block_stop":
                            yield StreamChunk(event_data=data)

                        elif event_type == "message_delta":
                            usage_data = data.get("usage")
                            if usage_data:
                                yield StreamChunk(
                                    event_data=data,
                                    usage=usage_data,
                                    headers=response_headers,
                                )

                        elif event_type == "message_stop":
                            yield StreamChunk(
                                finish_reason="stop",
                                event_data=data,
                                headers=response_headers,
                            )

                    except json.JSONDecodeError:
                        continue

    def messages_create(
        self, model: str, messages: List[Dict[str, Any]], stream: bool = False, **kwargs
    ) -> Any:
        """
        Native Anthropic Messages API format
        Returns raw Anthropic response without OpenAI conversion
        """
        if model.startswith("anthropic/"):
            model = model[10:]

        request_data = self._format_messages_for_anthropic(messages)
        request_data["model"] = model
        request_data["stream"] = stream

        for key, value in kwargs.items():
            if key not in ["model", "messages", "stream"]:
                request_data[key] = value

        logger.debug("Making messages request", model=model, stream=stream)
        logger.trace("Request data", request_data=request_data)

        try:
            response = self.session.post(
                f"{self.base_url}/messages", json=request_data, stream=stream
            )

            if not response.ok:
                self._handle_error_response(response)

            if stream:
                return self._handle_native_stream_response(response)
            else:
                response_json = response.json()
                response_json["_response_headers"] = dict(response.headers)
                return response_json

        except AnthropicAPIError:
            raise
        except Exception as e:
            if "This credential is only authorized for use with Claude Code" in str(e):
                raise Exception("Claude Code spoof failed")
            raise

    def _handle_native_stream_response(self, response) -> Generator[tuple, None, None]:
        """
        Handle streaming response in native Anthropic SSE format
        Returns tuple of (SSE event string, (usage_data, headers) or None)
        """
        usage_data = None
        response_headers = dict(response.headers)

        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")

                if line_str.startswith("data: "):
                    try:
                        data = json.loads(line_str[6:])
                        if data.get("type") == "message_delta" and data.get("usage"):
                            usage_data = data["usage"]
                    except:
                        pass

                if line_str.startswith("event: message_stop"):
                    yield (line_str + "\n", (usage_data, response_headers))
                else:
                    yield (line_str + "\n", None)
