"""
Qatar Foundation — Admin Portal
Flask Application Factory
"""

import os
import logging
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

from config import config_map
from models import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger("qatar_foundation")


def create_app(env=None):
    env = env or os.environ.get("FLASK_ENV", "default")
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_map.get(env, config_map["default"]))

    FRONTEND_DIR = os.path.abspath(os.path.join(app.root_path, "..", "sky"))

    db.init_app(app)
    CORS(app)

    # ── Blueprints 
    from routes.auth import auth_bp
    from routes.opportunities import opps_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(opps_bp)

    # ── Health 
    @app.get("/api/health")
    def health():
        return jsonify({"success": True, "message": "Qatar Foundation API is running.", "version": "1.0.0"})

    # ── Serve Frontend 
    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "admin.html")

    @app.get("/<path:filename>")
    def frontend_files(filename):
        if filename.startswith("api/"):
            return jsonify({"success": False, "message": "Not found"}), 404
        return send_from_directory(FRONTEND_DIR, filename)

    #  Error handlers 
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Endpoint not found."}), 404
        try:
            return send_from_directory(FRONTEND_DIR, "admin.html")
        except Exception:
            return jsonify({"success": False, "message": "Not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"success": False, "message": "Method not allowed."}), 405

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"500: {e}")
        return jsonify({"success": False, "message": "Internal server error."}), 500

    # ── DB bootstrap 
    with app.app_context():
        os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
        db.create_all()
        logger.info("Database ready.")
        logger.info(f"Frontend: {FRONTEND_DIR}")

    return app