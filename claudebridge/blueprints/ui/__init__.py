from flask import Blueprint

ui_bp = Blueprint('ui', __name__, url_prefix='/app')

from claudebridge.blueprints.ui import auth, models, accounts, users, settings, usage, chat
