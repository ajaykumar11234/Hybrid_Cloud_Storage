from flask import request, jsonify
from services.service_manager import service_manager
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

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
        
        logger.info(f"Search request: type={search_type}, query='{query}', tags='{tags_param}', start_date='{start_date}', end_date='{end_date}'")
        
        try:
            all_files = service_manager.mongodb.get_all_files()
            logger.info(f"Total files in database: {len(all_files)}")
            
            results = []
            
            if search_type == "tags":
                # Search by tags
                tags = [tag.strip().lower() for tag in tags_param.split(",") if tag.strip()]
                logger.info(f"Tags search with tags: {tags}")
                
                if tags:
                    for file in all_files:
                        file_keywords = file.get('ai_analysis', {}).get('keywords', [])
                        if file_keywords:
                            # Check if any tag matches any keyword (case insensitive)
                            file_keywords_lower = [kw.lower() for kw in file_keywords]
                            if any(tag in file_keywords_lower for tag in tags):
                                results.append(file)
                else:
                    # If no tags provided, return all files for tags search
                    results = all_files
                    
            elif search_type == "date":
                # Date range search
                logger.info(f"Date search: {start_date} to {end_date}")
                
                for file in all_files:
                    upload_date_value = file.get('minio_uploaded_at') or file.get('uploaded_at')
                    if upload_date_value:
                        try:
                            # Handle both datetime objects and strings
                            if isinstance(upload_date_value, datetime):
                                upload_date = upload_date_value
                            else:
                                # It's a string, parse it
                                if 'T' in upload_date_value:
                                    upload_date = datetime.fromisoformat(upload_date_value.replace('Z', '+00:00'))
                                else:
                                    upload_date = datetime.strptime(upload_date_value, '%Y-%m-%d %H:%M:%S')
                            
                            # Convert to date only for comparison
                            upload_date_date = upload_date.date()
                            
                            if start_date and end_date:
                                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                                if start <= upload_date_date <= end:
                                    results.append(file)
                            elif start_date:
                                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                                if upload_date_date >= start:
                                    results.append(file)
                            elif end_date:
                                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                                if upload_date_date <= end:
                                    results.append(file)
                            else:
                                # If no date range specified, include the file
                                results.append(file)
                        except (ValueError, AttributeError, TypeError) as e:
                            logger.warning(f"Could not parse date {upload_date_value}: {e}")
                            continue
                
            else:
                # Text search in filename and AI analysis content
                logger.info(f"Text search with query: '{query}'")
                
                if query:
                    query_lower = query.lower()
                    for file in all_files:
                        filename = file.get('filename', '').lower()
                        
                        # Search in filename (partial match)
                        if query_lower in filename:
                            results.append(file)
                            continue
                            
                        # Search in AI analysis content
                        ai_analysis = file.get('ai_analysis', {})
                        if ai_analysis:
                            summary = ai_analysis.get('summary', '').lower()
                            caption = ai_analysis.get('caption', '').lower()
                            keywords = [kw.lower() for kw in ai_analysis.get('keywords', [])]
                            
                            # Search in summary, caption, and keywords
                            if (query_lower in summary or 
                                query_lower in caption or 
                                any(query_lower in kw for kw in keywords)):
                                results.append(file)
                else:
                    # If no query, return all files
                    results = all_files
            
            logger.info(f"Search found {len(results)} results")
            
            return jsonify({
                "results": results,
                "count": len(results),
                "query": query,
                "search_type": search_type
            }), 200
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}", exc_info=True)
            return jsonify({"error": str(e), "results": [], "count": 0}), 500

    @app.route("/analytics/storage", methods=["GET"])
    def get_storage_analytics():
        """Get storage statistics"""
        try:
            all_files = service_manager.mongodb.get_all_files()
            
            total_files = len(all_files)
            total_size = sum(f.get('size', 0) for f in all_files)
            avg_file_size = total_size / total_files if total_files > 0 else 0
            
            # Count files with AI analysis
            files_analyzed = sum(1 for f in all_files if f.get('ai_analysis_status') == 'completed')
            
            # Status distribution
            status_distribution = {}
            for file in all_files:
                status = file.get('status', 'unknown')
                status_distribution[status] = status_distribution.get(status, 0) + 1
            
            storage_stats = {
                "total_files": total_files,
                "total_size": total_size,
                "avg_file_size": avg_file_size,
                "status_distribution": status_distribution,
                "files_analyzed": files_analyzed
            }
            
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
            all_files = service_manager.mongodb.get_all_files()
            
            # Group by date
            uploads_by_date = {}
            for file in all_files:
                upload_date_value = file.get('minio_uploaded_at') or file.get('uploaded_at')
                if upload_date_value:
                    try:
                        # Handle both datetime objects and strings
                        if isinstance(upload_date_value, datetime):
                            upload_date = upload_date_value
                        else:
                            if 'T' in upload_date_value:
                                upload_date = datetime.fromisoformat(upload_date_value.replace('Z', '+00:00'))
                            else:
                                upload_date = datetime.strptime(upload_date_value, '%Y-%m-%d %H:%M:%S')
                        
                        date_key = upload_date.strftime('%Y-%m-%d')
                        uploads_by_date[date_key] = uploads_by_date.get(date_key, 0) + 1
                    except (ValueError, AttributeError, TypeError):
                        continue
            
            # Fill in missing days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days-1)  # Include today
            daily_uploads = []
            
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                daily_uploads.append({
                    "_id": date_str,
                    "count": uploads_by_date.get(date_str, 0)
                })
                current_date += timedelta(days=1)
            
            return jsonify({"daily_uploads": daily_uploads}), 200
        except Exception as e:
            logger.error(f"Upload analytics error: {e}")
            # Return empty data for the requested days
            daily_uploads = []
            today = datetime.now()
            for i in range(days):
                date = today - timedelta(days=days-1-i)  # Proper order
                daily_uploads.append({
                    "_id": date.strftime('%Y-%m-%d'),
                    "count": 0
                })
            return jsonify({"daily_uploads": daily_uploads}), 200
    
    @app.route("/analytics/tags", methods=["GET"])
    def get_tag_analytics():
        """Get tag statistics"""
        limit = int(request.args.get("limit", 10))
        
        try:
            all_files = service_manager.mongodb.get_all_files()
            
            # Count keywords
            keyword_counts = {}
            for file in all_files:
                keywords = file.get('ai_analysis', {}).get('keywords', [])
                for keyword in keywords:
                    if keyword and isinstance(keyword, str):  # Skip empty and non-string keywords
                        keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
            
            # Convert to list and sort
            top_tags = [{"_id": k, "count": v} for k, v in keyword_counts.items()]
            top_tags.sort(key=lambda x: x["count"], reverse=True)
            top_tags = top_tags[:limit]
            
            return jsonify({"top_tags": top_tags}), 200
        except Exception as e:
            logger.error(f"Tag analytics error: {e}")
            return jsonify({"top_tags": []}), 200
    
    @app.route("/analytics/activity", methods=["GET"])
    def get_activity_analytics():
        """Get recent activity including uploads, analysis, and deletions"""
        hours = int(request.args.get("hours", 24))
        
        try:
            all_files = service_manager.mongodb.get_all_files()
            activity = []
            
            for file in all_files:
                filename = file.get('filename', 'Unknown')
                
                # Upload activity
                upload_date_value = file.get('minio_uploaded_at')
                if upload_date_value:
                    try:
                        # Handle both datetime objects and strings
                        if isinstance(upload_date_value, datetime):
                            upload_time = upload_date_value
                        else:
                            if 'T' in upload_date_value:
                                upload_time = datetime.fromisoformat(upload_date_value.replace('Z', '+00:00'))
                            else:
                                upload_time = datetime.strptime(upload_date_value, '%Y-%m-%d %H:%M:%S')
                            
                        time_threshold = datetime.utcnow() - timedelta(hours=hours)
                        
                        if upload_time >= time_threshold:
                            # Convert to string for response
                            timestamp_str = upload_time.isoformat() if isinstance(upload_date_value, datetime) else upload_date_value
                            activity.append({
                                "event_type": "file_uploaded",
                                "resource": filename,
                                "timestamp": timestamp_str,
                                "details": f"File {filename} was uploaded to MinIO"
                            })
                    except (ValueError, AttributeError, TypeError) as e:
                        logger.warning(f"Could not parse upload date {upload_date_value}: {e}")
                        pass
                
                # AI analysis activity
                ai_analysis = file.get('ai_analysis')
                if ai_analysis and isinstance(ai_analysis, dict):
                    analysis_date = ai_analysis.get('analysis_date')
                    if analysis_date:
                        try:
                            if isinstance(analysis_date, datetime):
                                analysis_time = analysis_date
                            else:
                                if 'T' in analysis_date:
                                    analysis_time = datetime.fromisoformat(analysis_date.replace('Z', '+05:30'))
                                else:
                                    analysis_time = datetime.strptime(analysis_date, '%Y-%m-%d %H:%M:%S')
                                
                            time_threshold = datetime.utcnow() - timedelta(hours=hours)
                            
                            if analysis_time >= time_threshold:
                                # Convert to string for response
                                timestamp_str = analysis_time.isoformat() if isinstance(analysis_date, datetime) else analysis_date
                                activity.append({
                                    "event_type": "ai_analysis_completed",
                                    "resource": filename,
                                    "timestamp": timestamp_str,
                                    "details": f"AI analysis completed for {filename}"
                                })
                        except (ValueError, AttributeError, TypeError) as e:
                            logger.warning(f"Could not parse analysis date {analysis_date}: {e}")
                            pass
            
            # Sort by timestamp (newest first)
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