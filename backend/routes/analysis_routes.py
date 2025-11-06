from flask import jsonify, request
from services.service_manager import service_manager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def setup_analysis_routes(app):
    """Setup AI analysis routes"""
    
    @app.route("/analyze/<filename>", methods=["POST"])
    def analyze_file(filename):
        """Trigger AI analysis for a specific file"""
        try:
            logger.info(f"Starting AI analysis for file: {filename}")
            
            if not filename or not isinstance(filename, str):
                return jsonify({"error": "Invalid filename"}), 400

            # ✅ Fetch file metadata safely
            existing_file = service_manager.mongodb.get_file_by_filename(filename)
            if not existing_file:
                return jsonify({"error": "File not found in database"}), 404

            user_id = existing_file.get("user_id")

            # Set AI analysis status
            service_manager.mongodb.update_file(filename, {
                "ai_analysis_status": "pending",
                "ai_analysis": None
            }, user_id=user_id)

            # ✅ Fetch file bytes from MinIO
            file_data = service_manager.minio.get_file(user_id, filename)
            if not file_data:
                service_manager.mongodb.update_file(filename, {
                    "ai_analysis_status": "failed",
                    "ai_analysis_error": "File not found in MinIO storage"
                }, user_id=user_id)
                return jsonify({"error": "File not found in MinIO storage"}), 404

            # ✅ Extract text from the file
            try:
                text = service_manager.file_processor.extract_text(filename, file_data)
                logger.info(f"[AI] Extracted text length: {len(text) if text else 0}")
            except Exception as extraction_error:
                error_msg = f"Text extraction failed: {str(extraction_error)}"
                logger.error(error_msg)
                service_manager.mongodb.update_file(filename, {
                    "ai_analysis_status": "failed",
                    "ai_analysis_error": error_msg
                }, user_id=user_id)
                return jsonify({"error": error_msg}), 500

            # ✅ Validate text before analysis
            if not text or len(text.strip()) < 10:
                msg = "Not enough content for AI analysis"
                logger.warning(msg)
                service_manager.mongodb.update_file(filename, {
                    "ai_analysis_status": "failed",
                    "ai_analysis_error": msg
                }, user_id=user_id)
                return jsonify({"error": msg}), 400

            # ✅ Run Groq AI (via service_manager.ai)
            try:
                if not service_manager.ai or not service_manager.ai.is_available():
                    raise Exception("AI service unavailable")

                logger.info(f"[AI] Starting Groq analysis for {filename}")
                analysis_result = service_manager.ai.analyze_text(text, filename)
                if not analysis_result:
                    raise Exception("AI returned no analysis result")

            except Exception as ai_error:
                error_msg = f"AI analysis failed: {ai_error}"
                logger.error(error_msg)
                service_manager.mongodb.update_file(filename, {
                    "ai_analysis_status": "failed",
                    "ai_analysis_error": str(ai_error)
                }, user_id=user_id)
                return jsonify({"error": error_msg}), 500

            # ✅ Add timestamp and update DB
            analysis_result["analysis_date"] = datetime.utcnow().isoformat()
            update_data = {
                "ai_analysis": analysis_result,
                "ai_analysis_status": "completed",
                "ai_analysis_error": None
            }
            service_manager.mongodb.update_file(filename, update_data, user_id=user_id)

            logger.info(f"✅ AI analysis completed successfully for {filename}")
            return jsonify({
                "message": f"AI analysis completed for {filename}",
                "analysis": analysis_result,
                "status": "completed"
            }), 200

        except Exception as e:
            error_msg = f"Unexpected error during analysis: {str(e)}"
            logger.error(error_msg)
            try:
                service_manager.mongodb.update_file(filename, {
                    "ai_analysis_status": "failed",
                    "ai_analysis_error": error_msg
                })
            except:
                pass
            return jsonify({"error": error_msg}), 500

    @app.route("/analyze/batch", methods=["POST"])
    def analyze_batch():
        """Trigger AI analysis for multiple files"""
        try:
            data = request.get_json()
            if not data or 'files' not in data:
                return jsonify({"error": "No files provided"}), 400
            
            filenames = data['files']
            if not isinstance(filenames, list):
                return jsonify({"error": "Files must be a list"}), 400

            results = []
            for filename in filenames:
                try:
                    analyze_file(filename)
                    results.append({"filename": filename, "status": "queued"})
                except Exception as e:
                    results.append({"filename": filename, "status": "error", "error": str(e)})

            return jsonify({
                "message": f"Analysis queued for {len(filenames)} files",
                "results": results
            }), 202

        except Exception as e:
            return jsonify({"error": f"Batch analysis failed: {str(e)}"}), 500

    @app.route("/analysis/status/<filename>", methods=["GET"])
    def get_analysis_status(filename):
        """Get AI analysis status for a file"""
        try:
            file_data = service_manager.mongodb.get_file_by_filename(filename)
            if not file_data:
                return jsonify({"error": "File not found"}), 404

            return jsonify({
                "filename": filename,
                "status": file_data.get("ai_analysis_status", "not_started"),
                "has_analysis": file_data.get("ai_analysis") is not None,
                "error": file_data.get("ai_analysis_error")
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to get status: {str(e)}"}), 500

    @app.route("/analysis/<filename>", methods=["DELETE"])
    def delete_analysis(filename):
        """Delete AI analysis for a file"""
        try:
            update_data = {
                "ai_analysis": None,
                "ai_analysis_status": "not_started",
                "ai_analysis_error": None
            }
            success = service_manager.mongodb.update_file(filename, update_data)
            if not success:
                return jsonify({"error": "File not found"}), 404

            return jsonify({
                "message": f"AI analysis deleted for {filename}",
                "status": "deleted"
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to delete analysis: {str(e)}"}), 500
