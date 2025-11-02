from flask import request, jsonify
from services.service_manager import service_manager
from models.file_model import FileMetadata
from utils.helpers import get_content_type
import logging

logger = logging.getLogger(__name__)

def setup_upload_routes(app):
    """Setup upload-related routes"""
    
    @app.route("/upload", methods=["POST"])
    def upload_file():
        """Upload file to MinIO and create database entry"""
        try:
            if 'file' not in request.files:
                return jsonify({"error": "No file provided"}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400

            filename = file.filename
            file_data = file.read()

            if len(file_data) == 0:
                return jsonify({"error": "Empty file"}), 400

            # Upload to MinIO
            content_type = get_content_type(filename)
            service_manager.minio.upload_file(filename, file_data, content_type)

            # Generate MinIO URLs
            minio_preview_url, minio_download_url = service_manager.minio.generate_presigned_urls(filename)

            # Create file metadata
            file_meta = FileMetadata(
                filename=filename,
                size=len(file_data),
                content_type=content_type
            )
            file_meta.minio_preview_url = minio_preview_url
            file_meta.minio_download_url = minio_download_url
            file_meta.ai_analysis_status = "pending"

            # Save to MongoDB
            service_manager.mongodb.insert_file(file_meta)

            # Check if AI analysis is available and file type is supported
            ai_analysis_queued = False
            if service_manager.ai and service_manager.ai.is_available():
                supported_extensions = ['pdf', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'csv', 'json', 'xml']
                file_extension = filename.lower().split('.')[-1]
                if file_extension in supported_extensions:
                    ai_analysis_queued = True

            return jsonify({
                "message": f"{filename} uploaded successfully",
                "minio_available": True,
                "minio_urls_generated": minio_preview_url is not None and minio_download_url is not None,
                "ai_analysis_queued": ai_analysis_queued
            }), 200

        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            return jsonify({"error": f"Upload failed: {str(e)}"}), 500