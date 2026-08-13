import os

from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from config import config


def get_resource_path(relative_path):
    """Return a resource path that works in development and PyInstaller builds."""
    import sys

    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)


def create_app(config_class=None):
    """Create and configure the PDF Combiner application."""
    app = Flask(
        __name__,
        template_folder=get_resource_path("app/templates"),
        static_folder=get_resource_path("app/static"),
    )

    if config_class is None:
        environment = os.getenv("APP_ENV", "development")
        config_class = config.get(environment, config["default"])
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_error):
        if request.path != "/":
            return jsonify({"error": "The upload is too large. Please choose smaller files."}), 413
        return "Request entity too large", 413

    from app.routes import main_bp

    app.register_blueprint(main_bp)
    return app
