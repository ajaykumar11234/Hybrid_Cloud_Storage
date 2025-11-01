from flask import jsonify
from services.service_manager import service_manager

def setup_analysis_routes(app):
    """Setup AI analysis routes"""
    
    @app.route("/analyze/<filename>", methods=["POST"])
    def analyze_file(filename):
        """Trigger AI analysis for a specific file"""
        try:
            # Get file from MinIO
            file_data = service_manager.minio.get_file(filename)
            if not file_data:
                return jsonify({"error": "File not found"}), 404
            
            # Extract text
            text = service_manager.file_processor.extract_text(filename, file_data)
            
            if not text or len(text) < 10:
                return jsonify({"error": "Not enough text for analysis"}), 400
            
            # Perform AI analysis
            analysis_result = service_manager.groq.analyze_text(text, filename)
            
            if analysis_result:
                # Update file metadata
                update_data = {
                    "ai_analysis": analysis_result,
                    "ai_analysis_status": "completed"
                }
                service_manager.mongodb.update_file(filename, update_data)
                
                return jsonify({
                    "message": f"AI analysis completed for {filename}",
                    "analysis": analysis_result
                }), 200
            else:
                update_data = {"ai_analysis_status": "failed"}
                service_manager.mongodb.update_file(filename, update_data)
                return jsonify({"error": "AI analysis failed"}), 500
                
        except Exception as e:
            update_data = {"ai_analysis_status": "failed"}
            service_manager.mongodb.update_file(filename, update_data)
            return jsonify({"error": str(e)}), 500