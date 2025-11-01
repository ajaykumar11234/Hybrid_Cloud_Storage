from flask import request
from services.service_manager import service_manager
from utils.helpers import create_file_response

def setup_download_routes(app):
    """Setup file download and preview routes"""
    
    @app.route("/download/<filename>", methods=["GET"])
    def download_file(filename):
        """Download file from MinIO or S3"""
        source = request.args.get("source", "minio")
        
        try:
            if source == "s3":
                file_data = service_manager.s3.get_file(filename)
            else:
                file_data = service_manager.minio.get_file(filename)
            
            if not file_data:
                return jsonify({"error": "File not found"}), 404
            
            return create_file_response(file_data, filename, as_attachment=True)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/preview/<filename>", methods=["GET"])
    def preview_file(filename):
        """Preview file in browser from MinIO or S3"""
        source = request.args.get("source", "minio")
        
        try:
            if source == "s3":
                file_data = service_manager.s3.get_file(filename)
            else:
                file_data = service_manager.minio.get_file(filename)
            
            if not file_data:
                return jsonify({"error": "File not found"}), 404
            
            return create_file_response(file_data, filename, as_attachment=False)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500