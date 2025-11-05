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
import logging, os

logger = logging.getLogger(__name__)


def create_app():
    """✅ Create and configure Flask application"""
    app = Flask(__name__)

    # ✅ Allow frontend (React) to access backend APIs
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},  # Allow all origins for Render deployment
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # ✅ Load debug configurations
    debug_config()

    # ✅ Initialize database from ServiceManager
    db = getattr(service_manager.mongodb, "db", None)
    if db is None:
        raise RuntimeError("❌ MongoDB not initialized in ServiceManager")

    # ✅ Initialize authentication routes
    init_auth_routes(db)
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # ✅ Register all route groups
    setup_file_routes(app)
    setup_download_routes(app)
    setup_analysis_routes(app)
    setup_analytics_routes(app)

    # ✅ Health check endpoint (Render will ping this)
    @app.route("/health", methods=["GET"])
    def health_check():
        """Basic server health check"""
        return jsonify({
            "status": "OK",
            "message": "Server is running",
            "version": "1.0.0",
            "environment": Config.ENVIRONMENT,
            "services": service_manager.get_service_status()
        }), 200

    print("✅ Flask app initialized successfully.")
    return app


if __name__ == "__main__":
    try:
        app = create_app()

        # ✅ Start background workers (S3 sync, AI analysis, etc.)
        start_background_threads()

        print("🚀 Starting Flask application...")

        # ✅ Use dynamic Render port instead of hardcoded 5000
        port = int(os.environ.get("PORT", 8000))
        app.run(
            host="0.0.0.0",
            port=port,
            debug=False  # Always false in production
        )

    except Exception as e:
        logger.exception("❌ Fatal error while starting app")
        print(f"❌ Fatal error while starting app: {e}")
