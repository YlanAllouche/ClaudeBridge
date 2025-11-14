"""
OAuth Manager for Anthropic Claude Pro/Max authentication
Implements full OAuth flow with PKCE, token storage, and refresh
"""

import base64
import hashlib
import json
import os
import secrets
import time
import uuid
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import requests

from .logger import logger

# TODO: Probably some refactoring


class OAuthManager:
    """
    Manages complete OAuth flow for Anthropic Claude
    Handles PKCE generation, authorization, token exchange, and refresh
    Supports session-based OAuth for multi-account management
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        accounts_manager=None,
    ):
        self.client_id = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
        self.base_url = base_url
        self.default_redirect_uri = "https://console.anthropic.com/oauth/code/callback"
        self.scopes = "org:create_api_key user:profile user:inference"
        self.accounts_manager = accounts_manager

    def generate_pkce(self) -> Dict[str, str]:
        """Generate PKCE code verifier and challenge"""
        # Generate code verifier (43-128 characters)
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )

        # Generate code challenge (SHA256 hash of verifier)
        challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = (
            base64.urlsafe_b64encode(challenge_bytes).decode("utf-8").rstrip("=")
        )

        return {"verifier": code_verifier, "challenge": code_challenge}

    def get_authorization_url(
        self,
        mode: str = "max",
        session_id: Optional[str] = None,
        use_custom_redirect: bool = False,
    ) -> Tuple[str, str, str]:
        """
        Generate authorization URL for Claude Pro/Max
        Args:
            mode: "max" for claude.ai, "console" for console.anthropic.com
            use_custom_redirect: If True, use local callback URL (not working at the moment)
        Returns:
            (authorization_url, code_verifier, session_id)
        """
        # FIX: Remnants of several older tests
        pkce = self.generate_pkce()

        if session_id is None:
            session_id = str(uuid.uuid4())

        # Always use default redirect URI - Anthropic doesn't support custom callbacks
        # for this OAuth client_id
        redirect_uri = self.default_redirect_uri

        base_url = f"https://{'claude.ai' if mode == 'max' else 'console.anthropic.com'}/oauth/authorize"

        params = {
            "code": "true",
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": self.scopes,
            "code_challenge": pkce["challenge"],
            "code_challenge_method": "S256",
            "state": pkce["verifier"],
        }

        auth_url = f"{base_url}?{urlencode(params)}"
        return auth_url, pkce["verifier"], session_id

    def exchange_code_for_tokens(
        self, code: str, verifier: str, redirect_uri: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens"""
        # Handle code format: "code#state" - split the code and state
        splits = code.split("#")
        actual_code = splits[0]
        state = splits[1] if len(splits) > 1 else ""

        if redirect_uri is None:
            redirect_uri = self.default_redirect_uri

        token_data = {
            "code": actual_code,
            "state": state,
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        }

        response = requests.post(
            "https://console.anthropic.com/v1/oauth/token",
            headers={"Content-Type": "application/json"},
            json=token_data,
        )

        if not response.ok:
            raise Exception(
                f"Token exchange failed: {response.status_code} {response.text}"
            )

        token_response = response.json()

        # Log full response to see what metadata is available
        logger.debug(f"Token exchange response keys: {list(token_response.keys())}")
        logger.debug(f"Full token response: {json.dumps(token_response)}")

        # Calculate expiry timestamp
        expires_at = int(time.time()) + token_response.get("expires_in", 3600)

        tokens = {
            "access_token": token_response["access_token"],
            "refresh_token": token_response["refresh_token"],
            "expires_at": expires_at,
            "obtained_at": int(time.time()),
            "full_response": token_response,  # Include full response for metadata capture
        }

        return tokens

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        Args:
            refresh_token: Valid refresh token
        Returns:
            New token data (no automatic storage, caller handles persistence)
        """
        refresh_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }

        response = requests.post(
            "https://console.anthropic.com/v1/oauth/token",
            headers={"Content-Type": "application/json"},
            json=refresh_data,
        )

        if not response.ok:
            raise Exception(
                f"Token refresh failed: {response.status_code} {response.text}"
            )

        token_response = response.json()

        # Calculate expiry timestamp
        expires_at = int(time.time()) + token_response.get("expires_in", 3600)

        tokens = {
            "access_token": token_response["access_token"],
            "refresh_token": token_response.get(
                "refresh_token", refresh_token
            ),  # Use new refresh token if provided
            "expires_at": expires_at,
            "refreshed_at": int(time.time()),
        }

        return tokens
