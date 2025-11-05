# backend/app.py
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config, debug_config
from routes.auth_routes import setup_auth_routes, init_auth_routes, auth_bp
from routes.file_routes import setup_file_routes
from routes.analysis_routes import setup_analysis_routes
from routes.analytics_routes import setup_analytics_routes
from routes.download_routes import setup_download_routes
from utils.background_tasks import start_background_threads
from services.service_manager import service_manager

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)

    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    debug_config()

    # Service manager may have partially-initialized services; just log if DB missing
    db = getattr(service_manager.mongodb, "db", None) if service_manager and getattr(service_manager, "mongodb", None) else None
    if db is None:
        logger.warning("⚠️ MongoDB not initialized (service_manager.mongodb is None). Some endpoints may be limited.")

    # Initialize auth (if DB present)
    if db:
        init_auth_routes(db)
        app.register_blueprint(auth_bp, url_prefix="/auth")

    # Register routes (they should handle missing DB/service gracefully)
    setup_file_routes(app)
    setup_download_routes(app)
    setup_analysis_routes(app)
    setup_analytics_routes(app)

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "OK",
            "message": "Server is running",
            "version": "1.0.0",
            "environment": Config.ENVIRONMENT,
            "services": service_manager.get_service_status() if hasattr(service_manager, "get_service_status") else {}
        }), 200

    print("✅ Flask app initialized successfully.")
    return app

if __name__ == "__main__":
    app = create_app()

    # start background threads (should be non-blocking)
    try:
        start_background_threads()
    except Exception as e:
        logger.exception("⚠️ Background threads failed to start")

    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting Flask (Gunicorn actually launches it on port 8000) - listening on {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
