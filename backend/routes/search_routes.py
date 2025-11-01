from flask import request, jsonify
from services.service_manager import service_manager
from datetime import datetime, timedelta

def setup_search_routes(app):
    """Setup enhanced search and analytics routes"""
    
    @app.route("/search", methods=["GET"])
    def search_files():
        """Search files by text query"""
        query = request.args.get("q", "")
        search_type = request.args.get("type", "text")  # text, tags, date
        
        try:
            if search_type == "tags":
                tags = [tag.strip() for tag in query.split(",") if tag.strip()]
                results = service_manager.mongodb.search_files_by_tags(tags)
            elif search_type == "date":
                # Date range search (format: YYYY-MM-DD to YYYY-MM-DD)
                date_range = query.split(" to ")
                if len(date_range) == 2:
                    start_date = datetime.strptime(date_range[0].strip(), "%Y-%m-%d")
                    end_date = datetime.strptime(date_range[1].strip(), "%Y-%m-%d")
                    results = service_manager.mongodb.search_files_by_date_range(start_date, end_date)
                else:
                    results = []
            else:
                # Text search
                results = service_manager.mongodb.search_files(query)
            
            return jsonify({
                "results": results,
                "count": len(results),
                "query": query,
                "search_type": search_type
            }), 200
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/analytics/uploads", methods=["GET"])
    def get_upload_analytics():
        """Get upload statistics"""
        days = int(request.args.get("days", 30))
        
        try:
            stats = service_manager.mongodb.get_upload_stats(days)
            return jsonify(stats), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/analytics/tags", methods=["GET"])
    def get_tag_analytics():
        """Get tag statistics"""
        limit = int(request.args.get("limit", 10))
        
        try:
            tags = service_manager.mongodb.get_top_tags(limit)
            return jsonify(tags), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/analytics/storage", methods=["GET"])
    def get_storage_analytics():
        """Get storage statistics"""
        try:
            stats = service_manager.mongodb.get_storage_stats()
            file_types = service_manager.mongodb.get_file_type_stats()
            
            return jsonify({
                "storage": stats,
                "file_types": file_types
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/analytics/activity", methods=["GET"])
    def get_activity_analytics():
        """Get recent activity"""
        hours = int(request.args.get("hours", 24))
        event_type = request.args.get("event_type")
        
        try:
            activity = service_manager.mongodb.get_recent_activity(hours)
            if event_type:
                activity = [log for log in activity if log.get("event_type") == event_type]
            
            return jsonify(activity), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
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
            
            success = service_manager.mongodb.update_file(filename, {"tags": tags})
            
            if success:
                # Log the tag update
                service_manager.mongodb.log_event({
                    "event_type": "tag_update",
                    "resource": filename,
                    "user": "system",
                    "timestamp": datetime.utcnow(),
                    "details": {"tags": tags}
                })
                
                return jsonify({"message": "Tags updated successfully", "tags": tags}), 200
            else:
                return jsonify({"error": "File not found"}), 404
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500