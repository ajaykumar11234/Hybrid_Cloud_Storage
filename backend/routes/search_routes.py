from flask import request, jsonify
from functools import wraps
from services.service_manager import service_manager
import jwt
from config import Config
import logging

logger = logging.getLogger(__name__)

# ==========================================
# JWT Authentication Decorator
# ==========================================
def token_required(f):
    """Decorator to verify JWT and extract user_id"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token missing"}), 401

        try:
            # Remove Bearer prefix if present
            if token.startswith("Bearer "):
                token = token[7:]

            data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = str(data.get("user_id"))

            if not user_id:
                return jsonify({"error": "Invalid token: no user_id"}), 401

            return f(user_id, *args, **kwargs)

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        except Exception as e:
            logger.error(f"JWT decode error: {e}")
            return jsonify({"error": "Token verification failed"}), 401
    return decorated


# ==========================================
# Search Routes
# ==========================================
def setup_search_routes(app):
    """Setup search routes with user isolation"""

    # Helper function for filtering user's files
    def get_user_files(user_id):
        """Fetch only files belonging to the authenticated user"""
        all_files = service_manager.mongodb.get_all_files()
        return [f for f in all_files if f.get("user_id") == user_id]

    # -------------------------------
    # General Search Route
    # -------------------------------
    @app.route("/search", methods=["GET"])
    @token_required
    def search_files(user_id):
        """Search user's files by filename or keywords"""
        query = request.args.get("q", "").strip().lower()

        try:
            user_files = get_user_files(user_id)
            if not query:
                return jsonify({
                    "results": user_files,
                    "count": len(user_files),
                    "query": query
                }), 200

            results = []
            for file in user_files:
                filename = file.get("filename", "").lower()
                keywords = file.get("ai_analysis", {}).get("keywords", [])

                # Match filename or keywords
                if query in filename or any(query in str(kw).lower() for kw in keywords):
                    results.append(file)

            return jsonify({
                "results": results,
                "count": len(results),
                "query": query
            }), 200

        except Exception as e:
            logger.exception("Search error")
            return jsonify({"error": str(e), "results": [], "count": 0}), 500

    # -------------------------------
    # Search by Filename Only
    # -------------------------------
    @app.route("/search/filename", methods=["GET"])
    @token_required
    def search_by_filename(user_id):
        """Search files by filename only"""
        query = request.args.get("q", "").strip().lower()
        if not query:
            return jsonify({"error": "Query parameter 'q' is required"}), 400

        try:
            user_files = get_user_files(user_id)
            results = [
                f for f in user_files
                if query in f.get("filename", "").lower()
            ]

            return jsonify({
                "results": results,
                "count": len(results),
                "query": query
            }), 200
        except Exception as e:
            logger.exception("Filename search error")
            return jsonify({"error": str(e), "results": [], "count": 0}), 500

    # -------------------------------
    # Search by Keywords Only
    # -------------------------------
    @app.route("/search/keywords", methods=["GET"])
    @token_required
    def search_by_keywords(user_id):
        """Search files by AI-generated keywords"""
        query = request.args.get("q", "").strip().lower()
        if not query:
            return jsonify({"error": "Query parameter 'q' is required"}), 400

        try:
            user_files = get_user_files(user_id)
            results = []

            for f in user_files:
                keywords = f.get("ai_analysis", {}).get("keywords", [])
                if any(query in str(kw).lower() for kw in keywords):
                    results.append(f)

            return jsonify({
                "results": results,
                "count": len(results),
                "query": query
            }), 200
        except Exception as e:
            logger.exception("Keyword search error")
            return jsonify({"error": str(e), "results": [], "count": 0}), 500

    # -------------------------------
    # Get All Files with Filters
    # -------------------------------
    @app.route("/files", methods=["GET"])
    @token_required
    def get_all_files_route(user_id):
        """Get user's files with optional filtering"""
        filename_filter = request.args.get("filename", "").strip().lower()
        keyword_filter = request.args.get("keyword", "").strip().lower()

        try:
            user_files = get_user_files(user_id)
            filtered_files = []

            for f in user_files:
                filename = f.get("filename", "").lower()
                keywords = f.get("ai_analysis", {}).get("keywords", [])

                # Apply filename filter
                if filename_filter and filename_filter not in filename:
                    continue

                # Apply keyword filter
                if keyword_filter and not any(keyword_filter in str(kw).lower() for kw in keywords):
                    continue

                filtered_files.append(f)

            return jsonify({
                "files": filtered_files,
                "count": len(filtered_files),
                "filters": {
                    "filename": filename_filter,
                    "keyword": keyword_filter
                }
            }), 200

        except Exception as e:
            logger.exception("Files filtering error")
            return jsonify({"error": str(e), "files": [], "count": 0}), 500

    return app
