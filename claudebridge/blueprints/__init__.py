def register_blueprints(app):
    from claudebridge.blueprints.core import core_bp
    from claudebridge.blueprints.api import api_bp
    from claudebridge.blueprints.ui import ui_bp
    
    app.register_blueprint(core_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(ui_bp)
