from flask import request, jsonify
from services.service_manager import service_manager
from models.file_model import FileMetadata
from utils.helpers import get_content_type

def setup_upload_routes(app):
    """Setup upload-related routes"""
    
    @app.route("/upload", methods=["POST"])
    def upload_file():
        """Upload file to MinIO and create database entry"""
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file provided"}), 400

        filename = file.filename
        file_data = file.read()

        try:
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

            return jsonify({
                "message": f"{filename} uploaded to MinIO",
                "minio_available": True,
                "minio_urls_generated": minio_preview_url is not None and minio_download_url is not None,
                "ai_analysis_queued": service_manager.ai and service_manager.ai.is_available()
            }), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500