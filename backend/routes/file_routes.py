from flask import request, jsonify
from functools import wraps
import jwt
import logging
from config import Config
from models.file_model import FileMetadata
from services.service_manager import service_manager
from utils.helpers import get_content_type
from datetime import datetime

logger = logging.getLogger(__name__)

# =========================================================
# JWT AUTH DECORATOR (with CORS preflight bypass)
# =========================================================
def token_required(f):
    """Verify JWT and extract user_id (skip preflight OPTIONS requests)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Allow preflight CORS checks
        if request.method == "OPTIONS":
            return jsonify({"message": "CORS preflight OK"}), 200

        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token missing"}), 401

        try:
            if token.startswith("Bearer "):
                token = token[7:]
            data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = str(data.get("user_id"))
            if not user_id:
                return jsonify({"error": "Invalid token: missing user_id"}), 401
            return f(user_id, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        except Exception as e:
            logger.exception("JWT verification failed")
            return jsonify({"error": f"Token verification failed: {str(e)}"}), 401

    return decorated


# =========================================================
# USER FILE ROUTES
# =========================================================
def setup_file_routes(app):
    """Register all user-specific file routes."""

    # ------------------------------
    # LIST FILES
    # ------------------------------
    @app.route("/user/files", methods=["GET", "OPTIONS"])
    @token_required
    def list_user_files(user_id):
        try:
            files = service_manager.mongodb.get_all_files(user_id=user_id)
            logger.info(f"📂 User {user_id} fetched {len(files)} files.")
            return jsonify(files), 200
        except Exception as e:
            logger.exception("❌ Error listing files")
            return jsonify({"error": f"Failed to fetch files: {str(e)}"}), 500

    # ------------------------------
    # UPLOAD FILE
    # ------------------------------
    @app.route("/user/upload", methods=["POST", "OPTIONS"])
    @token_required
    def upload_user_file(user_id):
        try:
            if "file" not in request.files:
                return jsonify({"error": "No file provided"}), 400

            file = request.files["file"]
            filename = file.filename.strip()
            if not filename:
                return jsonify({"error": "Filename is empty"}), 400

            file_data = file.read()
            if not file_data:
                return jsonify({"error": "Empty file"}), 400

            content_type = get_content_type(filename)
            service_manager.minio.upload_file(user_id, filename, file_data, content_type)

            preview_url, download_url = service_manager.minio.generate_presigned_urls(user_id, filename)
            file_meta = FileMetadata(filename, len(file_data), content_type, user_id)
            file_meta.minio_preview_url = preview_url
            file_meta.minio_download_url = download_url
            service_manager.mongodb.insert_file(file_meta)

            return jsonify({
                "message": f"File '{filename}' uploaded successfully",
                "preview_url": preview_url,
                "download_url": download_url
            }), 200
        except Exception as e:
            logger.exception("❌ Upload error")
            return jsonify({"error": f"Upload failed: {str(e)}"}), 500

    # ------------------------------
    # DELETE FILE
    # ------------------------------
    @app.route("/user/delete/<filename>", methods=["DELETE", "OPTIONS"])
    @token_required
    def delete_user_file(user_id, filename):
        """Delete file from MinIO, S3, and MongoDB."""
        try:
            file_doc = service_manager.mongodb.get_file(filename, user_id=user_id)
            if not file_doc:
                return jsonify({"error": "File not found or unauthorized"}), 404

            # Delete from S3 if available
            s3_deleted = True
            if service_manager.s3 and service_manager.s3.is_available():
                try:
                    s3_deleted = service_manager.s3.delete_file(user_id, filename)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to delete {filename} from S3: {e}")
                    s3_deleted = False

            # Delete from MinIO
            minio_deleted = service_manager.minio.delete_file(user_id, filename)

            # Delete metadata
            db_deleted = service_manager.mongodb.delete_file(filename, user_id=user_id)

            if all([s3_deleted, minio_deleted, db_deleted]):
                logger.info(f"🗑️ File '{filename}' fully deleted for user {user_id}")
                return jsonify({"message": f"'{filename}' deleted successfully"}), 200
            else:
                logger.warning(f"⚠️ Partial deletion: {filename}")
                return jsonify({"error": "Partial deletion — one or more storage layers failed"}), 500

        except Exception as e:
            logger.exception("❌ File deletion error")
            return jsonify({"error": f"File deletion failed: {str(e)}"}), 500

    # ------------------------------
    # REFRESH MINIO URLS
    # ------------------------------
    @app.route("/user/refresh-urls/<filename>", methods=["POST", "OPTIONS"])
    @token_required
    def refresh_user_urls(user_id, filename):
        """Regenerate MinIO presigned URLs for user's file."""
        try:
            file_doc = service_manager.mongodb.get_file(filename, user_id=user_id)
            if not file_doc:
                return jsonify({"error": "File not found or unauthorized"}), 404

            # Generate new URLs
            preview_url, download_url = service_manager.minio.generate_presigned_urls(user_id, filename)

            # Update metadata in MongoDB (optional)
            service_manager.mongodb.update_file(filename, {
                "minio_preview_url": preview_url,
                "minio_download_url": download_url,
                "last_updated": datetime.utcnow().isoformat()
            }, user_id=user_id)

            return jsonify({
                "message": "URLs refreshed successfully",
                "minio_preview_url": preview_url,
                "minio_download_url": download_url
            }), 200

        except Exception as e:
            logger.exception("❌ URL refresh error")
            return jsonify({"error": f"Failed to refresh URLs: {str(e)}"}), 500

    # ------------------------------
    # SEARCH FILES
    # ------------------------------
    @app.route("/user/search", methods=["GET", "OPTIONS"])
    @token_required
    def user_search_files(user_id):
        try:
            query = request.args.get("q", "").strip()
            results = service_manager.mongodb.search_files(query, user_id=user_id)
            return jsonify({
                "query": query,
                "count": len(results),
                "results": results
            }), 200
        except Exception as e:
            logger.exception("❌ Search error")
            return jsonify({"error": f"Search failed: {str(e)}"}), 500

    return app
