from flask import redirect, request, session
from claudebridge.services.ui import create_login_page
from ..dependencies import get_config_manager
from . import ui_bp

@ui_bp.route("/auth", methods=["GET"])
def ui_login_page():
    config_manager = get_config_manager()
    ui_password_info = config_manager.get_ui_password()
    ui_password = ui_password_info.get("password")
    if not ui_password:
        session["ui_authenticated"] = True
        return redirect("/app/models")

    return str(create_login_page())

@ui_bp.route("/login", methods=["POST"])
def ui_login():
    config_manager = get_config_manager()
    password = request.form.get("password", "")
    ui_password_info = config_manager.get_ui_password()
    ui_password = ui_password_info.get("password")

    if not ui_password or password == ui_password:
        session["ui_authenticated"] = True
        return redirect("/app/models")

    return str(create_login_page(error="Invalid password"))

@ui_bp.route("/logout", methods=["GET", "POST"])
def ui_logout():
    session.pop("ui_authenticated", None)
    return redirect("/app/auth")
