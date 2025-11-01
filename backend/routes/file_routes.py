from flask import jsonify
from services.service_manager import service_manager

def setup_file_routes(app):
    """Setup file management routes"""
    
    @app.route("/files", methods=["GET"])
    def list_files():
        """Return all file metadata"""
        files = service_manager.mongodb.get_all_files()
        return jsonify(files)
    
    @app.route("/delete/<filename>", methods=["DELETE"])
    def delete_file(filename):
        """Delete file from all storage and database"""
        try:
            # Delete from MinIO
            service_manager.minio.delete_file(filename)
            
            # Delete from S3
            service_manager.s3.delete_file(filename)
            
            # Delete from database
            service_manager.mongodb.delete_file(filename)
            
            return jsonify({"message": f"{filename} deleted successfully"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/refresh-urls/<filename>", methods=["POST"])
    def refresh_urls(filename):
        """Refresh expired MinIO URLs"""
        try:
            minio_preview_url, minio_download_url = service_manager.minio.generate_presigned_urls(filename)
            
            update_data = {
                "minio_preview_url": minio_preview_url,
                "minio_download_url": minio_download_url
            }
            service_manager.mongodb.update_file(filename, update_data)
            
            return jsonify({
                "message": "URLs refreshed successfully",
                "minio_preview_url": minio_preview_url,
                "minio_download_url": minio_download_url
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500