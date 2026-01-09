"""
OAuth Fetch Wrapper for token management
Implements the same network exchange pattern as ClaudeCode
"""

import asyncio
import time
from typing import Any, Callable, Dict, Optional

import requests

from .logger import logger


class OAuthFetchWrapper:
    """
    Custom fetch wrapper that handles OAuth token management
    """

    def __init__(self, accounts_manager, timeout: Optional[int] = None):
        self.accounts_manager = accounts_manager
        self.timeout = timeout or 120  # default 2 minutes

    def create_session_with_oauth(self) -> requests.Session:
        """
        Create a requests session with OAuth handling
        Returns a session that automatically handles OAuth for all requests
        """
        session = requests.Session()

        original_request = session.request

        def oauth_request(method, url, **kwargs):
            """Override session.request to add OAuth handling"""

            headers = kwargs.get("headers", {})

            access_token = self.accounts_manager.get_valid_access_token()

            if not access_token:
                raise Exception(
                    "No valid OAuth token available. Please authenticate first."
                )

            headers["Authorization"] = f"Bearer {access_token}"

            headers.update(
                {
                    "anthropic-version": "2023-06-01",
                    "anthropic-beta": "oauth-2025-04-20,interleaved-thinking-2025-05-14",
                }
            )

            headers["user-agent"] = "claude-cli/2.1.2 (external, cli)"

            conflicting_headers = ["x-api-key", "X-API-Key", "api-key"]
            for header in conflicting_headers:
                if header in headers:
                    del headers[header]

            if "timeout" not in kwargs:
                kwargs["timeout"] = self.timeout

            kwargs["headers"] = headers

            logger.debug(f"Session OAuth request to {url}")
            logger.debug(f"Headers: {dict(headers)}")
            logger.trace(f"Session outgoing request to Anthropic API - URL: {url}")
            logger.trace(f"Session outgoing request headers: {dict(headers)}")
            if "json" in kwargs:
                logger.trace(f"Session outgoing request body: {kwargs['json']}")

            try:
                response = original_request(method, url, **kwargs)

                logger.debug(f"Response status: {response.status_code}")
                logger.trace(f"Anthropic API response status: {response.status_code}")
                logger.trace(
                    f"Anthropic API response headers: {dict(response.headers)}"
                )
                if "stream" not in kwargs or not kwargs["stream"]:
                    try:
                        logger.trace(f"Anthropic API response body: {response.json()}")
                    except:
                        logger.trace(
                            f"Anthropic API response body (text): {response.text[:1000]}"
                        )

                if response.status_code == 401:
                    logger.debug("Got 401, attempting token refresh and retry")

                    try:
                        new_access_token = (
                            self.accounts_manager.get_valid_access_token()
                        )
                        if new_access_token:
                            headers["Authorization"] = f"Bearer {new_access_token}"
                            kwargs["headers"] = headers

                            logger.debug("Token refreshed, retrying request")

                            response = original_request(method, url, **kwargs)
                            logger.debug(
                                f"Retry response status: {response.status_code}"
                            )

                    except Exception as refresh_error:
                        logger.debug(f"Token refresh failed: {refresh_error}")

                return response

            except requests.exceptions.Timeout:
                raise Exception(
                    f"Request timed out after {kwargs.get('timeout', self.timeout)} seconds"
                )
            except requests.exceptions.RequestException as e:
                raise Exception(f"Request failed: {str(e)}")

        session.request = oauth_request

        return session
