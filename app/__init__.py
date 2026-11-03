"""Ekte Mat Online – Flask application factory."""
import os

from flask import Flask, flash, redirect, render_template, request

from app.config import Config


def create_app(config_class=Config):
    # Templates live in app/views (the "View" in MVC) instead of Flask's default app/templates.
    app = Flask(__name__, instance_relative_config=True, template_folder="views")
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)

    from app.models import init_storage
    init_storage(app)

    app.add_template_filter(format_nok, "nok")

    for code, (title, message) in ERROR_PAGES.items():
        app.register_error_handler(code, _error_page(code, title, message))

    @app.errorhandler(413)
    def upload_too_large(error):
        mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        flash(f"The picture is too large. The limit is {mb} MB.", "error")
        return redirect(request.path)

    from app.controllers.menu import bp as menu_bp
    from app.controllers.cart import bp as cart_bp
    from app.controllers.auth import bp as auth_bp
    from app.controllers.orders import bp as orders_bp
    from app.controllers.admin_food import bp as admin_food_bp
    from app.controllers.admin_orders import bp as admin_orders_bp
    from app.controllers.admin_questions import bp as admin_questions_bp
    app.register_blueprint(menu_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_food_bp)
    app.register_blueprint(admin_orders_bp)
    app.register_blueprint(admin_questions_bp)

    return app


def format_nok(amount):
    """Whole NOK with a space as thousands separator: 1250 -> '1 250 kr'."""
    return f"{amount:,} kr".replace(",", " ")


ERROR_PAGES = {
    400: ("Bad request", "The form contained a value we didn't understand."),
    403: ("Access denied", "This page is only for administrators."),
    404: ("Page not found", "The page doesn't exist, or you don't have access to it."),
}


def _error_page(code, title, message):
    def handler(error):
        return render_template("errors/error.html", code=code, title=title, message=message), code
    return handler
