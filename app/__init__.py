"""
Flask application factory.
Creates the app, registers blueprints, initializes DB and rate limiting.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, send_from_directory
from app.config import Config
from app.extensions import limiter
from app.models.database import init_db
from app.routes.api import api_bp
from app.routes.main import main_bp

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

def create_app() -> Flask:
    """Application factory pattern — used by run.py and tests."""
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config["SECRET_KEY"] = Config.SECRET_KEY

    os.makedirs(Config.SCREENSHOTS_DIR, exist_ok=True)
    os.makedirs(Config.EXPORTS_DIR, exist_ok=True)
    db_dir = os.path.dirname(Config.DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    init_db()
    limiter.init_app(app)
    limiter.default_limits = [Config.RATE_LIMIT_DEFAULT]

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    @app.route("/screenshots/<path:filename>")
    def serve_screenshot(filename):
        if ".." in filename:
            return {"error": "Invalid path"}, 400
        return send_from_directory(Config.SCREENSHOTS_DIR, filename)

    return app
