import logging
import os
import secrets
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, request, session

from claudebridge.services.accounts_manager import AccountsManager
from claudebridge.services.config_manager import ConfigManager
from claudebridge.services.logger import logger
from claudebridge.services.metrics_manager import MetricsManager
from claudebridge.services.oauth_manager import OAuthManager
from claudebridge.services.rate_limiter import RateLimiter
from claudebridge.services.web_session_poller import WebSessionPoller

load_dotenv()

static_folder = Path(__file__).parent / "static"

app = Flask(__name__, static_folder=str(static_folder), static_url_path="/static")
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))


# ====================
# FIX:: Find standard way to make Flask logger work with Loguru or pick another logger
class WerkzeugToLoguruHandler(logging.Handler):
    def emit(self, record):
        message = record.getMessage()
        if "/metrics" in message:
            logger.opt(depth=6, exception=record.exc_info).trace(message)
        else:
            logger.opt(depth=6, exception=record.exc_info).log(
                record.levelname, message
            )


logging.getLogger("werkzeug").handlers = []
logging.getLogger("werkzeug").addHandler(WerkzeugToLoguruHandler())
logging.getLogger("werkzeug").setLevel(logging.INFO)
logging.getLogger("werkzeug").propagate = False

# ====================

config_manager = ConfigManager()
oauth_manager = OAuthManager(
    # TODO: Make this more flexible if we can ever implement the full PKCE flow
    base_url="http://localhost:8000"
)
accounts_manager = AccountsManager(oauth_manager=oauth_manager)
metrics_manager = MetricsManager(config_manager=config_manager)
rate_limiter = RateLimiter()
web_session_poller = WebSessionPoller(accounts_manager)


web_session_poller.start()  # PERF: Avoid delays to poll on restart this may lead to rapid polling  if restarting right after a natural poll - ok for now


def on_config_reload(config: ConfigManager):
    logger.info("Config reloaded, updating globals...")
    token_count = len(config.get_all_tokens())
    metrics_manager.update_active_tokens(token_count)
    logger.info(f"  Updated active tokens count: {token_count}")


config_manager.register_reload_callback(on_config_reload)
config_manager.start_watch(interval=2)


def ensure_frontend_token():
    tokens = config_manager.get_all_tokens()

    for token in tokens:
        if token.get("name") == "frontend":
            logger.info("'frontend' token already exists")
            return token.get("token")

    frontend_token = config_manager.add_api_token("frontend")
    logger.info(f"Created 'frontend' token for chat UI")
    return frontend_token


frontend_token_value = ensure_frontend_token()


def shutdown_handler(signum, frame):
    logger.info("\nShutting down gracefully...")
    config_manager.stop_watch()
    metrics_manager.shutdown()
    rate_limiter.shutdown()
    web_session_poller.stop()
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

metrics_manager.update_active_tokens(len(config_manager.get_all_tokens()))

app.config["config_manager"] = config_manager
app.config["oauth_manager"] = oauth_manager
app.config["accounts_manager"] = accounts_manager
app.config["metrics_manager"] = metrics_manager
app.config["rate_limiter"] = rate_limiter
app.config["web_session_poller"] = web_session_poller
app.config["frontend_token_value"] = frontend_token_value


# TODO: could this become a problem?
@app.after_request
def after_request(response):
    # TODO: look into this security wise
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response


@app.before_request
def check_ui_auth():
    if request.path.startswith("/app"):
        ui_password_info = config_manager.get_ui_password()
        ui_password = ui_password_info.get("password")

        if ui_password and request.path != "/app/auth" and request.path != "/app/login":
            if not session.get("ui_authenticated"):
                if request.headers.get("HX-Request"):
                    return redirect("/app/auth")
                return redirect("/app/auth")


from claudebridge.blueprints import register_blueprints

register_blueprints(app)


def main():
    """Entry point for installed package (production mode)"""
    if "DEBUG" not in os.environ:
        os.environ["DEBUG"] = "info"
    logger.info("Starting ClaudeBridge in production mode (DEBUG=info)")

    from waitress import serve

    serve(app, host="0.0.0.0", port=8000, threads=4)


if __name__ == "__main__":
    if "DEBUG" not in os.environ:
        os.environ["DEBUG"] = "debug"
    logger.info("Starting ClaudeBridge in development mode (DEBUG=debug)")
    app.run(debug=True, host="0.0.0.0", port=8000, use_reloader=True)
