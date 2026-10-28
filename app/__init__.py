"""Ekte Mat Online – Flask application factory."""
import os

from flask import Flask

from app.config import Config


def create_app(config_class=Config):
    # Templates live in app/views (the "View" in MVC) instead of Flask's default app/templates.
    app = Flask(__name__, instance_relative_config=True, template_folder="views")
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)

    from app.models import init_storage
    init_storage(app)

    from app.controllers.menu import bp as menu_bp
    app.register_blueprint(menu_bp)

    return app
