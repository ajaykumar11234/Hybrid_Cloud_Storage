# routes/upload_routes.py

from flask import request, jsonify
from services.service_manager import service_manager
from models.file_model import FileMetadata
from utils.helpers import get_content_type
from utils.virus_scan import scan_file  # ✅ NEW import
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
# Upload Route
# ==========================================
def setup_upload_routes(app):
    """Setup upload-related routes"""

    @app.route("/upload", methods=["POST"])
    @token_required
    def upload_file(user_id):
        """Upload file to MinIO and save metadata in MongoDB"""
        try:
            # ✅ 1. Validate file
            if "file" not in request.files:
                return jsonify({"error": "No file provided"}), 400

            file = request.files["file"]
            filename = file.filename.strip()

            if not filename:
                return jsonify({"error": "No file selected"}), 400

            file_data = file.read()
            if not file_data:
                return jsonify({"error": "Empty file"}), 400

            # ✅ 2. Scan file for viruses
            logger.info(f"🧪 Scanning {filename} for viruses...")
            is_clean, virus_name = scan_file(file_data)

            if not is_clean:
                logger.warning(f"🚫 Virus detected in {filename}: {virus_name}")
                # Save metadata with infected status for audit
                infected_meta = FileMetadata(
                    filename=filename,
                    size=len(file_data),
                    content_type=get_content_type(filename),
                    user_id=user_id
                )
                infected_meta.scan_status = "infected"
                infected_meta.virus_name = virus_name
                service_manager.mongodb.insert_file(infected_meta)
                return jsonify({"error": f"File blocked due to virus: {virus_name}"}), 400

            # ✅ 3. Upload clean file to MinIO
            content_type = get_content_type(filename)
            uploaded = service_manager.minio.upload_file(user_id, filename, file_data, content_type)
            if not uploaded:
                return jsonify({"error": "MinIO upload failed"}), 500

            # ✅ 4. Generate presigned URLs
            minio_preview_url, minio_download_url = service_manager.minio.generate_presigned_urls(
                user_id, filename
            )

            # ✅ 5. Create metadata
            file_meta = FileMetadata(
                filename=filename,
                size=len(file_data),
                content_type=content_type,
                user_id=user_id
            )
            file_meta.minio_preview_url = minio_preview_url
            file_meta.minio_download_url = minio_download_url
            file_meta.ai_analysis_status = "pending"
            file_meta.scan_status = "clean"
            file_meta.virus_name = None

            # ✅ 6. Save in MongoDB
            service_manager.mongodb.insert_file(file_meta)

            # ✅ 7. AI analysis support check
            ai_analysis_queued = False
            if service_manager.ai and service_manager.ai.is_available():
                supported_extensions = ["pdf", "txt", "jpg", "jpeg", "png", "gif", "csv", "json", "xml"]
                ext = filename.lower().rsplit(".", 1)[-1]
                if ext in supported_extensions:
                    ai_analysis_queued = True

            return jsonify({
                "message": f"{filename} uploaded successfully and scanned clean.",
                "scan_status": "clean",
                "minio_available": True,
                "minio_urls_generated": bool(minio_preview_url and minio_download_url),
                "ai_analysis_queued": ai_analysis_queued
            }), 200

        except Exception as e:
            logger.exception("❌ Upload error")
            return jsonify({"error": f"Upload failed: {str(e)}"}), 500
