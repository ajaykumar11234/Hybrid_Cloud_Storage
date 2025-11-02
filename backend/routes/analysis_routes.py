from flask import jsonify, request
from services.service_manager import service_manager
from datetime import datetime, timedelta
import logging

# Set up logging
logger = logging.getLogger(__name__)

def setup_analysis_routes(app):
    """Setup AI analysis routes"""
    
    @app.route("/analyze/<filename>", methods=["POST"])
    def analyze_file(filename):
        """Trigger AI analysis for a specific file"""
        try:
            logger.info(f"Starting AI analysis for file: {filename}")
            
            # Validate filename
            if not filename or not isinstance(filename, str):
                return jsonify({"error": "Invalid filename"}), 400
            
            # Check if file exists in MongoDB first
            existing_file = service_manager.mongodb.get_file_by_filename(filename)
            if not existing_file:
                return jsonify({"error": "File not found in database"}), 404
            
            # Set analysis status to pending initially
            service_manager.mongodb.update_file(filename, {
                "ai_analysis_status": "pending",
                "ai_analysis": None
            })
            
            # Get file from MinIO
            file_data = service_manager.minio.get_file(filename)
            if not file_data:
                # Update status to failed
                service_manager.mongodb.update_file(filename, {
                    "ai_analysis_status": "failed",
                    "ai_analysis_error": "File not found in storage"
                })
                return jsonify({"error": "File not found in storage"}), 404
            
            # Extract text based on file type
            try:
                text = service_manager.file_processor.extract_text(filename, file_data)
                logger.info(f"Text extraction completed. Text length: {len(text) if text else 0}")
            except Exception as extraction_error:
                logger.error(f"Text extraction failed: {str(extraction_error)}")
                service_manager.mongodb.update_file(filename, {
                    "ai_analysis_status": "failed",
                    "ai_analysis_error": f"Text extraction failed: {str(extraction_error)}"
                })
                return jsonify({"error": f"Text extraction failed: {str(extraction_error)}"}), 500
            
            # Validate extracted text
            if not text:
                service_manager.mongodb.update_file(filename, {
                    "ai_analysis_status": "failed", 
                    "ai_analysis_error": "No text could be extracted from file"
                })
                return jsonify({"error": "No text could be extracted from file"}), 400
            
            if len(text.strip()) < 10:
                service_manager.mongodb.update_file(filename, {
                    "ai_analysis_status": "failed",
                    "ai_analysis_error": "Not enough text content for analysis"
                })
                return jsonify({"error": "Not enough text content for analysis"}), 400
            
            # Perform AI analysis
            try:
                logger.info("Starting Groq AI analysis...")
                analysis_result = service_manager.groq.analyze_text(text, filename)
                
                if not analysis_result:
                    raise Exception("AI service returned empty result")
                    
            except Exception as ai_error:
                logger.error(f"AI analysis failed: {str(ai_error)}")
                service_manager.mongodb.update_file(filename, {
                    "ai_analysis_status": "failed",
                    "ai_analysis_error": f"AI analysis failed: {str(ai_error)}"
                })
                return jsonify({"error": f"AI analysis failed: {str(ai_error)}"}), 500
            
            # Add analysis timestamp
            if isinstance(analysis_result, dict):
                analysis_result["analysis_date"] = datetime.utcnow().isoformat()
            else:
                # Ensure analysis_result is a dictionary
                analysis_result = {
                    "summary": str(analysis_result),
                    "analysis_date": datetime.utcnow().isoformat()
                }
            
            # Update file metadata with successful analysis
            update_data = {
                "ai_analysis": analysis_result,
                "ai_analysis_status": "completed",
                "ai_analysis_error": None
            }
            
            success = service_manager.mongodb.update_file(filename, update_data)
            if not success:
                logger.error(f"Failed to update database for file: {filename}")
                return jsonify({"error": "Failed to save analysis results"}), 500
            
            logger.info(f"AI analysis completed successfully for: {filename}")
            return jsonify({
                "message": f"AI analysis completed for {filename}",
                "analysis": analysis_result,
                "status": "completed"
            }), 200
                
        except Exception as e:
            logger.error(f"Unexpected error during analysis of {filename}: {str(e)}")
            # Try to update status to failed even in case of unexpected errors
            try:
                service_manager.mongodb.update_file(filename, {
                    "ai_analysis_status": "failed",
                    "ai_analysis_error": f"Unexpected error: {str(e)}"
                })
            except:
                pass  # If we can't update the database, at least return the error
            
            return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

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
                    # Use the same analysis logic but don't wait for completion
                    analyze_file(filename)
                    results.append({
                        "filename": filename,
                        "status": "queued"
                    })
                except Exception as e:
                    results.append({
                        "filename": filename,
                        "status": "error",
                        "error": str(e)
                    })
            
            return jsonify({
                "message": f"Analysis queued for {len(filenames)} files",
                "results": results
            }), 202
            
        except Exception as e:
            return jsonify({"error": f"Batch analysis failed: {str(e)}"}), 500

    @app.route("/analysis/status/<filename>", methods=["GET"])
    def get_analysis_status(filename):
        """Get analysis status for a file"""
        try:
            file_data = service_manager.mongodb.get_file_by_filename(filename)
            if not file_data:
                return jsonify({"error": "File not found"}), 404
            
            status = file_data.get('ai_analysis_status', 'not_started')
            analysis = file_data.get('ai_analysis')
            error = file_data.get('ai_analysis_error')
            
            return jsonify({
                "filename": filename,
                "status": status,
                "has_analysis": analysis is not None,
                "error": error
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

def setup_analytics_routes(app):
    """Setup analytics and search routes"""
    
    @app.route("/search", methods=["GET"])
    def search_files():
        """Search files by text query, tags, or date range"""
        query = request.args.get("q", "").strip()
        search_type = request.args.get("type", "text")
        tags_param = request.args.get("tags", "")
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")
        
        try:
            all_files = service_manager.mongodb.get_all_files()
            
            if search_type == "tags":
                # Search by tags
                tags = [tag.strip() for tag in tags_param.split(",") if tag.strip()]
                if tags:
                    results = []
                    for file in all_files:
                        file_keywords = file.get('ai_analysis', {}).get('keywords', [])
                        if file_keywords and any(tag.lower() in [kw.lower() for kw in file_keywords] for tag in tags):
                            results.append(file)
                else:
                    results = all_files
                    
            elif search_type == "date":
                # Date range search
                results = []
                for file in all_files:
                    upload_date_str = file.get('minio_uploaded_at') or file.get('uploaded_at')
                    if upload_date_str:
                        try:
                            # Handle different date formats
                            if 'T' in upload_date_str:
                                upload_date = datetime.fromisoformat(upload_date_str.replace('Z', '+00:00'))
                            else:
                                upload_date = datetime.strptime(upload_date_str, '%Y-%m-%d %H:%M:%S')
                            
                            if start_date and end_date:
                                start = datetime.strptime(start_date, '%Y-%m-%d')
                                end = datetime.strptime(end_date, '%Y-%m-%d')
                                # Set end date to end of day
                                end = end.replace(hour=23, minute=59, second=59)
                                if start <= upload_date <= end:
                                    results.append(file)
                            elif start_date:
                                start = datetime.strptime(start_date, '%Y-%m-%d')
                                if upload_date >= start:
                                    results.append(file)
                            elif end_date:
                                end = datetime.strptime(end_date, '%Y-%m-%d')
                                end = end.replace(hour=23, minute=59, second=59)
                                if upload_date <= end:
                                    results.append(file)
                            else:
                                results.append(file)
                        except (ValueError, AttributeError) as e:
                            logger.warning(f"Could not parse date {upload_date_str}: {e}")
                            continue
                else:
                    results = all_files
                    
            else:
                # Text search in filename and AI analysis content
                if query:
                    results = []
                    for file in all_files:
                        filename = file.get('filename', '').lower()
                        ai_analysis = file.get('ai_analysis', {})
                        
                        # Search in filename
                        if query.lower() in filename:
                            results.append(file)
                            continue
                            
                        # Search in AI analysis content
                        if ai_analysis:
                            summary = ai_analysis.get('summary', '').lower()
                            caption = ai_analysis.get('caption', '').lower()
                            keywords = [kw.lower() for kw in ai_analysis.get('keywords', [])]
                            
                            if (query.lower() in summary or 
                                query.lower() in caption or 
                                any(query.lower() in kw for kw in keywords)):
                                results.append(file)
                else:
                    results = all_files
            
            return jsonify({
                "results": results,
                "count": len(results),
                "query": query,
                "search_type": search_type
            }), 200
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return jsonify({"error": str(e), "results": [], "count": 0}), 500

    @app.route("/analytics/storage", methods=["GET"])
    def get_storage_analytics():
        """Get storage statistics"""
        try:
            storage_stats = service_manager.mongodb.get_storage_stats()
            return jsonify({"storage": storage_stats}), 200
        except Exception as e:
            logger.error(f"Storage analytics error: {e}")
            return jsonify({
                "storage": {
                    "total_files": 0,
                    "total_size": 0,
                    "avg_file_size": 0,
                    "status_distribution": {},
                    "files_analyzed": 0
                }
            }), 200
    
    @app.route("/analytics/uploads", methods=["GET"])
    def get_upload_analytics():
        """Get upload statistics"""
        days = int(request.args.get("days", 30))
        
        try:
            upload_trends = service_manager.mongodb.get_upload_trends(days)
            return jsonify({"daily_uploads": upload_trends}), 200
        except Exception as e:
            logger.error(f"Upload analytics error: {e}")
            # Return empty data structure
            empty_data = []
            today = datetime.now()
            for i in range(days):
                date = today - timedelta(days=i)
                empty_data.append({
                    "_id": date.strftime('%Y-%m-%d'),
                    "count": 0
                })
            return jsonify({"daily_uploads": empty_data}), 200
    
    @app.route("/analytics/tags", methods=["GET"])
    def get_tag_analytics():
        """Get tag statistics"""
        limit = int(request.args.get("limit", 10))
        
        try:
            top_tags = service_manager.mongodb.get_top_keywords(limit)
            return jsonify({"top_tags": top_tags}), 200
        except Exception as e:
            logger.error(f"Tag analytics error: {e}")
            return jsonify({"top_tags": []}), 200
    
    @app.route("/analytics/activity", methods=["GET"])
    def get_activity_analytics():
        """Get recent activity"""
        hours = int(request.args.get("hours", 24))
        
        try:
            recent_files = service_manager.mongodb.get_recent_files(limit=50)
            activity = []
            
            for file in recent_files:
                filename = file.get('filename', 'Unknown')
                upload_date = file.get('minio_uploaded_at') or file.get('uploaded_at')
                
                if upload_date:
                    try:
                        if 'T' in upload_date:
                            upload_time = datetime.fromisoformat(upload_date.replace('Z', '+00:00'))
                        else:
                            upload_time = datetime.strptime(upload_date, '%Y-%m-%d %H:%M:%S')
                            
                        time_threshold = datetime.utcnow() - timedelta(hours=hours)
                        
                        if upload_time >= time_threshold:
                            activity.append({
                                "event_type": "file_uploaded",
                                "resource": filename,
                                "timestamp": upload_date,
                                "details": f"File {filename} was uploaded"
                            })
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Could not parse upload date {upload_date}: {e}")
                        pass
                
                ai_analysis = file.get('ai_analysis')
                if ai_analysis and isinstance(ai_analysis, dict):
                    analysis_date = ai_analysis.get('analysis_date')
                    if analysis_date:
                        try:
                            if 'T' in analysis_date:
                                analysis_time = datetime.fromisoformat(analysis_date.replace('Z', '+00:00'))
                            else:
                                analysis_time = datetime.strptime(analysis_date, '%Y-%m-%d %H:%M:%S')
                                
                            time_threshold = datetime.utcnow() - timedelta(hours=hours)
                            
                            if analysis_time >= time_threshold:
                                activity.append({
                                    "event_type": "ai_analysis_completed",
                                    "resource": filename,
                                    "timestamp": analysis_date,
                                    "details": f"AI analysis completed for {filename}"
                                })
                        except (ValueError, AttributeError) as e:
                            logger.warning(f"Could not parse analysis date {analysis_date}: {e}")
                            pass
            
            activity.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return jsonify({"recent_activity": activity}), 200
            
        except Exception as e:
            logger.error(f"Activity analytics error: {e}")
            return jsonify({"recent_activity": []}), 200

    @app.route("/files/<filename>/tags", methods=["POST"])
    def update_file_tags(filename):
        """Update tags for a file"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        tags = data.get("tags", [])
        
        try:
            if not isinstance(tags, list):
                return jsonify({"error": "Tags must be a list"}), 400
            
            # Get current file data
            current_file = service_manager.mongodb.get_file_by_filename(filename)
            if not current_file:
                return jsonify({"error": "File not found"}), 404
            
            # Update AI analysis with new tags
            current_analysis = current_file.get('ai_analysis', {})
            updated_analysis = {
                **current_analysis,
                "keywords": tags,
                "tags_updated_at": datetime.utcnow().isoformat()
            }
            
            success = service_manager.mongodb.update_file(filename, {
                "ai_analysis": updated_analysis,
                "last_updated": datetime.utcnow().isoformat()
            })
            
            if success:
                return jsonify({
                    "message": "Tags updated successfully", 
                    "tags": tags,
                    "filename": filename
                }), 200
            else:
                return jsonify({"error": "Failed to update tags"}), 500
                
        except Exception as e:
            logger.error(f"Error updating tags for {filename}: {e}")
            return jsonify({"error": str(e)}), 500