from flask import Blueprint, redirect

core_bp = Blueprint('core', __name__)

@core_bp.route("/", methods=["GET"])
def root():
    return redirect("/app/")

@core_bp.route("/favicon.ico", methods=["GET"])
def favicon():
    return redirect("/static/icon.png")

@core_bp.route("/icon.png", methods=["GET"])
def icon():
    return redirect("/static/icon.png")

@core_bp.route("/app", methods=["GET"])
@core_bp.route("/app/", methods=["GET"])
def ui_root():
    return redirect("/app/models")
