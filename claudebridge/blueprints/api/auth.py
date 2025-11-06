from flask import jsonify, request

from ..dependencies import get_oauth_manager
from . import api_bp

# FIX: Small rework needed - remnant from pre-ui era


@api_bp.route("/auth/status", methods=["OPTIONS", "GET"])
def auth_status():
    if request.method == "OPTIONS":
        return "", 200
    oauth_manager = get_oauth_manager()
    return jsonify(oauth_manager.get_auth_status())


@api_bp.route("/auth/authorize", methods=["OPTIONS", "GET"])
def get_auth_url():
    if request.method == "OPTIONS":
        return "", 200

    oauth_manager = get_oauth_manager()
    mode = request.args.get("mode", "max")

    try:
        auth_url, verifier = oauth_manager.get_authorization_url(mode)
        return jsonify(
            {
                "authorization_url": auth_url,
                "instructions": "Visit the URL above and paste the authorization code below",
                "code_verifier": verifier,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/auth/exchange", methods=["OPTIONS", "POST"])
def exchange_code():
    if request.method == "OPTIONS":
        return "", 200

    oauth_manager = get_oauth_manager()
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    code = data.get("code")
    verifier = data.get("verifier")

    if not code or not verifier:
        return jsonify({"error": "Both 'code' and 'verifier' are required"}), 400

    try:
        tokens = oauth_manager.exchange_code_for_tokens(code, verifier)
        return jsonify(
            {
                "success": True,
                "message": "Authentication successful",
                "expires_at": tokens["expires_at"],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/auth/clear", methods=["OPTIONS", "POST"])
def clear_auth():
    if request.method == "OPTIONS":
        return "", 200

    oauth_manager = get_oauth_manager()
    oauth_manager.clear_tokens()
    return jsonify({"success": True, "message": "Tokens cleared"})
