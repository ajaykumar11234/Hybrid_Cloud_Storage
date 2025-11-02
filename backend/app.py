from flask import Flask
from flask_cors import CORS
from config import Config, debug_config
from utils.background_tasks import start_background_threads
from routes.upload_routes import setup_upload_routes
from routes.file_routes import setup_file_routes
from routes.analysis_routes import setup_analysis_routes
from routes.analytics_routes import setup_analytics_routes
from routes.download_routes import setup_download_routes

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    CORS(app)
    
    # Debug configuration
    debug_config()
    
    # Setup routes
    setup_upload_routes(app)
    setup_analytics_routes(app)
    setup_file_routes(app)
    setup_analysis_routes(app)
    setup_download_routes(app)
    
    return app

if __name__ == "__main__":
    app = create_app()
    
    # Start background threads
    start_background_threads()
    
    print("🚀 Starting Flask application...")
    app.run(debug=Config.DEBUG, port=5000, host='0.0.0.0')