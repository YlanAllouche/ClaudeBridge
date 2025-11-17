import time

from flask import request, session

from claudebridge.blueprints.dependencies import (
    get_accounts_manager,
    get_config_manager,
    get_oauth_manager,
    get_web_session_poller,
)
from claudebridge.services.logger import logger
from claudebridge.services.ui import (
    create_accounts_page,
    create_add_account_form,
    create_layout,
    create_oauth_flow_card,
)
from claudebridge.services.ui.accounts import create_account_card

from . import ui_bp


@ui_bp.route("/account", methods=["GET"])
def ui_account():
    config_manager = get_config_manager()
    accounts_manager = get_accounts_manager()
    web_session_poller = get_web_session_poller()
    accounts = accounts_manager.get_all_accounts()
    content = create_accounts_page(
        accounts, config_manager, accounts_manager, web_session_poller
    )

    if request.headers.get("HX-Request"):
        return str(content)

    return str(create_layout(content, "Account - ClaudeBridge", "account"))


@ui_bp.route("/account/refresh-card", methods=["GET"])
def ui_account_refresh_card():
    accounts_manager = get_accounts_manager()
    web_session_poller = get_web_session_poller()
    accounts = accounts_manager.get_all_accounts()
    if accounts:
        return str(
            create_account_card(accounts[0], accounts_manager, web_session_poller)
        )
    return ""


@ui_bp.route("/account/add-form", methods=["GET"])
def ui_account_add_form():
    return str(create_add_account_form())


@ui_bp.route("/account/cancel-form", methods=["GET"])
def ui_account_cancel_form():
    return ""


@ui_bp.route("/account/start-oauth", methods=["POST"])
def ui_account_start_oauth():
    oauth_manager = get_oauth_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    account_name = data.get("account_name", "").strip()
    mode = data.get("mode", "max")

    if not account_name:
        return "Account name is required", 400

    auth_url, code_verifier, session_id = oauth_manager.get_authorization_url(mode=mode)

    session[f"oauth_session_{session_id}"] = {
        "account_name": account_name,
        "code_verifier": code_verifier,
        "mode": mode,
        "created_at": time.time(),
    }

    return str(create_oauth_flow_card(session_id, auth_url, account_name))


@ui_bp.route("/account/complete-oauth", methods=["POST"])
def ui_account_complete_oauth():
    oauth_manager = get_oauth_manager()
    accounts_manager = get_accounts_manager()

    logger.debug("DEBUG: complete-oauth endpoint called")

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    logger.debug(f"DEBUG: Received data: {data}")

    code = data.get("code", "").strip()
    session_id = data.get("session_id", "").strip()

    logger.debug(f"DEBUG: code={code[:20]}..., session_id={session_id}")

    if not code or not session_id:
        logger.error("DEBUG: Missing code or session_id")
        return "Code and session ID are required", 400

    oauth_session_key = f"oauth_session_{session_id}"
    oauth_reconnect_key = f"oauth_reconnect_{session_id}"

    oauth_session = session.get(oauth_session_key)
    oauth_reconnect = session.get(oauth_reconnect_key)

    if not oauth_session and not oauth_reconnect:
        logger.error("DEBUG: No session found for this session_id")
        return "OAuth session not found or expired", 400

    if oauth_session:
        logger.debug("DEBUG: Processing new account")
        account_name = oauth_session.get("account_name")
        code_verifier = oauth_session.get("code_verifier")

        try:
            redirect_uri = oauth_manager.default_redirect_uri
            tokens = oauth_manager.exchange_code_for_tokens(
                code, code_verifier, redirect_uri
            )

            account_metadata = tokens.get("full_response", {})

            account = accounts_manager.add_account(
                account_name=account_name,
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                expires_at=tokens["expires_at"],
                account_metadata=account_metadata,
            )

            session.pop(oauth_session_key, None)

            return f"""
            <div class="bg-olive text-white p-6 rounded-material">
                <div class="text-xl font-bold mb-2">✅ Account Connected Successfully!</div>
                <p class="mb-0"><strong>{account_name}</strong> has been connected.</p>
                <script>
                    setTimeout(() => {{ window.location.href = '/app/account'; }}, 1500);
                </script>
            </div>
            """

        except Exception as e:
            logger.info(f"Error in OAuth callback: {e}")
            return f"Error: {str(e)}", 500

    elif oauth_reconnect_key in session:
        oauth_data = session[oauth_reconnect_key]
        account_id = oauth_data.get("account_id")
        code_verifier = oauth_data.get("code_verifier")

        try:
            redirect_uri = oauth_manager.default_redirect_uri
            tokens = oauth_manager.exchange_code_for_tokens(
                code, code_verifier, redirect_uri
            )

            success = accounts_manager.update_account_tokens(
                account_id=account_id,
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                expires_at=tokens["expires_at"],
            )

            session.pop(oauth_reconnect_key, None)

            if success:
                account = accounts_manager.get_account_by_id(account_id)
                account_name = account.get("account_name", "Unknown Account")

                return f"""
                <div class="bg-olive text-white p-6 rounded-material">
                    <div class="text-xl font-bold mb-2">✅ Account Reconnected Successfully!</div>
                    <p class="mb-0"><strong>{account_name}</strong> has been reconnected.</p>
                    <script>
                        setTimeout(() => {{ window.location.href = '/app/account'; }}, 1500);
                    </script>
                </div>
                """
            else:
                return "Failed to update account tokens", 500

        except Exception as e:
            logger.info(f"Error in OAuth reconnect callback: {e}")
            return f"Error: {str(e)}", 500

    else:
        return "OAuth session not found or expired", 400


@ui_bp.route("/account/reconnect", methods=["POST"])
def ui_account_reconnect():
    oauth_manager = get_oauth_manager()
    accounts_manager = get_accounts_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    account_id = data.get("account_id", "").strip()

    if not account_id:
        return "Account ID is required", 400

    account = accounts_manager.get_account_by_id(account_id)
    if not account:
        return "Account not found", 404

    account_name = account.get("account_name", "Unknown Account")
    mode = "max"

    auth_url, code_verifier, session_id = oauth_manager.get_authorization_url(mode=mode)

    session[f"oauth_reconnect_{session_id}"] = {
        "account_id": account_id,
        "code_verifier": code_verifier,
        "mode": mode,
        "created_at": time.time(),
    }

    return str(create_oauth_flow_card(session_id, auth_url, account_name))


@ui_bp.route("/account/delete", methods=["POST"])
def ui_account_delete():
    accounts_manager = get_accounts_manager()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    account_id = data.get("account_id", "").strip()

    if not account_id:
        return "Account ID is required", 400

    success = accounts_manager.delete_account(account_id)

    if success:
        return "", 200
    else:
        return "Account not found", 404


@ui_bp.route("/account/update-session-key", methods=["POST"])
def update_session_key():
    accounts_manager = get_accounts_manager()
    account_id = request.form.get("account_id")
    session_key = request.form.get("session_key", "").strip()
    if not account_id:
        return "Account ID required", 400
    if not session_key:
        return "Session key required", 400
    accounts_manager.update_web_session_key(account_id, session_key)

    web_session_poller = get_web_session_poller()
    web_session_poller.clear_error(account_id)

    accounts = accounts_manager.get_all_accounts()
    for acc in accounts:
        if acc.get("account_id") == account_id:
            return str(create_account_card(acc, accounts_manager, web_session_poller))
    return "Account not found", 404


@ui_bp.route("/account/remove-session-key", methods=["POST"])
def remove_session_key():
    accounts_manager = get_accounts_manager()
    account_id = request.form.get("account_id") or request.get_json().get("account_id")
    if not account_id:
        return "Account ID required", 400
    accounts_manager.update_web_session_key(account_id, None)

    web_session_poller = get_web_session_poller()
    web_session_poller.clear_error(account_id)

    accounts = accounts_manager.get_all_accounts()
    for acc in accounts:
        if acc.get("account_id") == account_id:
            return str(create_account_card(acc, accounts_manager, web_session_poller))
    return "Account not found", 404
