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
    """Factory to create and configure the Flask app."""
    app = Flask(__name__)

    # Enable CORS for frontend communication
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # Load environment config for debugging
    debug_config()

    # ----------------------------------------------------------
    # Verify database & initialize auth routes
    # ----------------------------------------------------------
    db = getattr(service_manager.mongodb, "db", None) if service_manager and getattr(service_manager, "mongodb", None) else None
    if db is not None:
        init_auth_routes(db)
        app.register_blueprint(auth_bp, url_prefix="/auth")
        logger.info("✅ Auth routes initialized with MongoDB.")
    else:
        logger.warning("⚠️ MongoDB not initialized — auth routes may be limited.")
    
    # ----------------------------------------------------------
    # Register other route blueprints
    # ----------------------------------------------------------
    setup_file_routes(app)
    setup_download_routes(app)
    setup_analysis_routes(app)
    setup_analytics_routes(app)

    # ----------------------------------------------------------
    # Health check endpoint
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # Start background threads (safe in Render/Gunicorn)
    # ----------------------------------------------------------
    try:
        start_background_threads()
    except Exception as e:
        logger.exception("⚠️ Background threads failed to start")

    return app


# ----------------------------------------------------------
# Local Development / Direct Execution
# ----------------------------------------------------------
if __name__ == "__main__":
    app = create_app()

    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting Flask development server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
