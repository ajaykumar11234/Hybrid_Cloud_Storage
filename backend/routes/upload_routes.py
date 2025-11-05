from flask import request, jsonify
from services.service_manager import service_manager
from models.file_model import FileMetadata
from utils.helpers import get_content_type
from functools import wraps
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

            # Decode JWT
            data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = str(data.get("user_id"))

            if not user_id:
                return jsonify({"error": "Invalid token: no user_id"}), 401

            # Inject user_id into route
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
# Upload Route
# ==========================================
def setup_upload_routes(app):
    """Setup upload-related routes"""

    @app.route("/upload", methods=["POST"])
    @token_required
    def upload_file(user_id):
        """Upload file to MinIO and save metadata in MongoDB"""
        try:
            # ✅ 1. Validate file existence
            if "file" not in request.files:
                return jsonify({"error": "No file provided"}), 400

            file = request.files["file"]
            if not file.filename.strip():
                return jsonify({"error": "No file selected"}), 400

            filename = file.filename.strip()
            file_data = file.read()

            # ✅ 2. Validate non-empty file
            if not file_data:
                return jsonify({"error": "Empty file"}), 400

            # ✅ 3. Determine content type
            content_type = get_content_type(filename)

            # ✅ 4. Upload to MinIO (per-user folder)
            service_manager.minio.upload_file(user_id, filename, file_data, content_type)

            # ✅ 5. Generate presigned URLs
            minio_preview_url, minio_download_url = service_manager.minio.generate_presigned_urls(
                user_id, filename
            )

            # ✅ 6. Create file metadata (now includes user_id)
            file_meta = FileMetadata(
                filename=filename,
                size=len(file_data),
                content_type=content_type,
                user_id=user_id  # ✅ attach uploader’s ID
            )

            # Set URLs and status
            file_meta.minio_preview_url = minio_preview_url
            file_meta.minio_download_url = minio_download_url
            file_meta.ai_analysis_status = "pending"

            # ✅ 7. Save metadata in MongoDB
            service_manager.mongodb.insert_file(file_meta)

            # ✅ 8. Check if AI analysis is supported
            ai_analysis_queued = False
            if service_manager.ai and service_manager.ai.is_available():
                supported_extensions = ["pdf", "txt", "jpg", "jpeg", "png", "gif", "csv", "json", "xml"]
                ext = filename.lower().rsplit(".", 1)[-1]
                if ext in supported_extensions:
                    ai_analysis_queued = True

            # ✅ 9. Return success response
            return jsonify({
                "message": f"{filename} uploaded successfully",
                "minio_available": True,
                "minio_urls_generated": bool(minio_preview_url and minio_download_url),
                "ai_analysis_queued": ai_analysis_queued
            }), 200

        except Exception as e:
            logger.exception("❌ Upload error")
            return jsonify({"error": f"Upload failed: {str(e)}"}), 500
