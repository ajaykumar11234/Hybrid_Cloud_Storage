from flask import request, jsonify
from services.service_manager import service_manager
import logging

logger = logging.getLogger(__name__)

def setup_search_routes(app):
    """Setup simplified search routes for basic filtering"""
    
    @app.route("/search", methods=["GET"])
    def search_files():
        """Simple search by filename or keywords"""
        query = request.args.get("q", "").strip()
        
        try:
            if not query:
                # If no query, return all files
                results = service_manager.mongodb.get_all_files()
            else:
                # Search in filename and keywords
                results = []
                all_files = service_manager.mongodb.get_all_files()
                
                for file in all_files:
                    filename = file.get('filename', '').lower()
                    
                    # Search in filename
                    if query.lower() in filename:
                        results.append(file)
                        continue
                    
                    # Search in keywords
                    keywords = file.get('ai_analysis', {}).get('keywords', [])
                    keyword_matches = any(
                        query.lower() in str(kw).lower() 
                        for kw in keywords
                    )
                    
                    if keyword_matches:
                        results.append(file)
            
            return jsonify({
                "results": results,
                "count": len(results),
                "query": query
            }), 200
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return jsonify({"error": str(e), "results": [], "count": 0}), 500
    
    @app.route("/search/filename", methods=["GET"])
    def search_by_filename():
        """Search files by filename only"""
        query = request.args.get("q", "").strip()
        
        try:
            if not query:
                return jsonify({"error": "Query parameter 'q' is required"}), 400
            
            results = []
            all_files = service_manager.mongodb.get_all_files()
            
            for file in all_files:
                filename = file.get('filename', '').lower()
                if query.lower() in filename:
                    results.append(file)
            
            return jsonify({
                "results": results,
                "count": len(results),
                "query": query
            }), 200
            
        except Exception as e:
            logger.error(f"Filename search error: {e}")
            return jsonify({"error": str(e), "results": [], "count": 0}), 500
    
    @app.route("/search/keywords", methods=["GET"])
    def search_by_keywords():
        """Search files by keywords only"""
        query = request.args.get("q", "").strip()
        
        try:
            if not query:
                return jsonify({"error": "Query parameter 'q' is required"}), 400
            
            results = []
            all_files = service_manager.mongodb.get_all_files()
            
            for file in all_files:
                keywords = file.get('ai_analysis', {}).get('keywords', [])
                keyword_matches = any(
                    query.lower() in str(kw).lower() 
                    for kw in keywords
                )
                
                if keyword_matches:
                    results.append(file)
            
            return jsonify({
                "results": results,
                "count": len(results),
                "query": query
            }), 200
            
        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            return jsonify({"error": str(e), "results": [], "count": 0}), 500
    
    @app.route("/files", methods=["GET"])
    def get_all_files_route():
        """Get all files with optional filtering"""
        filename_filter = request.args.get("filename", "").strip()
        keyword_filter = request.args.get("keyword", "").strip()
        
        try:
            all_files = service_manager.mongodb.get_all_files()
            filtered_files = []
            
            for file in all_files:
                # Apply filename filter
                if filename_filter:
                    filename = file.get('filename', '').lower()
                    if filename_filter.lower() not in filename:
                        continue
                
                # Apply keyword filter
                if keyword_filter:
                    keywords = file.get('ai_analysis', {}).get('keywords', [])
                    keyword_matches = any(
                        keyword_filter.lower() in str(kw).lower() 
                        for kw in keywords
                    )
                    if not keyword_matches:
                        continue
                
                filtered_files.append(file)
            
            return jsonify({
                "files": filtered_files,
                "count": len(filtered_files),
                "filters": {
                    "filename": filename_filter,
                    "keyword": keyword_filter
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Files filtering error: {e}")
            return jsonify({"error": str(e), "files": [], "count": 0}), 500