from flask import request, jsonify
from services.service_manager import service_manager
from datetime import datetime, timedelta
from functools import wraps
from config import Config
import jwt
import logging

logger = logging.getLogger(__name__)

# =========================================================
# JWT AUTH DECORATOR
# =========================================================
def token_required(f):
    """Verify JWT token and extract user_id"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Handle CORS preflight
        if request.method == "OPTIONS":
            return jsonify({"message": "CORS preflight OK"}), 200

        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token missing"}), 401

        try:
            if token.startswith("Bearer "):
                token = token[7:]

            data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = str(data.get("user_id"))
            if not user_id:
                return jsonify({"error": "Invalid token: missing user_id"}), 401

            return f(user_id, *args, **kwargs)

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        except Exception as e:
            logger.exception("JWT verification failed")
            return jsonify({"error": f"Token verification failed: {str(e)}"}), 401

    return decorated


# =========================================================
# USER-SPECIFIC ANALYTICS ROUTES
# =========================================================
def setup_analytics_routes(app):
    """Setup analytics routes for authenticated users"""

    # ------------------------------
    # SEARCH ANALYTICS
    # ------------------------------
    @app.route("/user/analytics/search", methods=["GET", "OPTIONS"])
    @token_required
    def analytics_search_files(user_id):
        """Search user files by text, tags, or date"""
        query = request.args.get("q", "").strip()
        search_type = request.args.get("type", "text")
        tags_param = request.args.get("tags", "")
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")

        try:
            files = service_manager.mongodb.get_all_files(user_id=user_id)
            results = []

            # --- TAG SEARCH ---
            if search_type == "tags":
                tags = [t.strip().lower() for t in tags_param.split(",") if t.strip()]
                for f in files:
                    keywords = [k.lower() for k in f.get("ai_analysis", {}).get("keywords", [])]
                    if any(tag in keywords for tag in tags):
                        results.append(f)

            # --- DATE SEARCH ---
            elif search_type == "date":
                for f in files:
                    date_val = f.get("minio_uploaded_at") or f.get("uploaded_at")
                    if not date_val:
                        continue
                    try:
                        if isinstance(date_val, datetime):
                            upload_date = date_val
                        elif "T" in str(date_val):
                            upload_date = datetime.fromisoformat(str(date_val).replace("Z", "+00:00"))
                        else:
                            upload_date = datetime.strptime(str(date_val), "%Y-%m-%d %H:%M:%S")

                        s = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
                        e = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
                        if s and e:
                            if s <= upload_date <= e:
                                results.append(f)
                        elif s and upload_date >= s:
                            results.append(f)
                        elif e and upload_date <= e:
                            results.append(f)
                    except Exception:
                        continue

            # --- TEXT SEARCH ---
            else:
                q = query.lower()
                for f in files:
                    filename = f.get("filename", "").lower()
                    ai = f.get("ai_analysis", {})
                    summary = ai.get("summary", "").lower()
                    caption = ai.get("caption", "").lower()
                    keywords = [k.lower() for k in ai.get("keywords", [])]

                    if (q in filename or q in summary or q in caption or any(q in k for k in keywords)):
                        results.append(f)
                if not query:
                    results = files

            return jsonify({
                "results": results,
                "count": len(results),
                "query": query,
                "search_type": search_type
            }), 200

        except Exception as e:
            logger.exception(f"Search analytics error for user {user_id}")
            return jsonify({"error": str(e), "results": [], "count": 0}), 500

    # ------------------------------
    # STORAGE ANALYTICS
    # ------------------------------
    @app.route("/user/analytics/storage", methods=["GET", "OPTIONS"])
    @token_required
    def analytics_storage(user_id):
        """Get user's storage stats"""
        try:
            files = service_manager.mongodb.get_all_files(user_id=user_id)
            total_files = len(files)
            total_size = sum(f.get("size", 0) for f in files)
            avg_size = total_size / total_files if total_files else 0
            analyzed = sum(1 for f in files if f.get("ai_analysis_status") == "completed")

            status_distribution = {}
            for f in files:
                status = f.get("status", "unknown")
                status_distribution[status] = status_distribution.get(status, 0) + 1

            return jsonify({
                "storage": {
                    "total_files": total_files,
                    "total_size": total_size,
                    "avg_file_size": avg_size,
                    "files_analyzed": analyzed,
                    "status_distribution": status_distribution
                }
            }), 200

        except Exception as e:
            logger.exception(f"Storage analytics error for user {user_id}")
            return jsonify({"storage": {}}), 200

    # ------------------------------
    # UPLOAD ANALYTICS
    # ------------------------------
    @app.route("/user/analytics/uploads", methods=["GET", "OPTIONS"])
    @token_required
    def analytics_uploads(user_id):
        """Daily upload trends"""
        days = int(request.args.get("days", 30))
        try:
            files = service_manager.mongodb.get_all_files(user_id=user_id)
            uploads_by_date = {}

            for f in files:
                date_val = f.get("minio_uploaded_at") or f.get("uploaded_at")
                if not date_val:
                    continue
                try:
                    if isinstance(date_val, datetime):
                        d = date_val
                    elif "T" in str(date_val):
                        d = datetime.fromisoformat(str(date_val).replace("Z", "+00:00"))
                    else:
                        d = datetime.strptime(str(date_val), "%Y-%m-%d %H:%M:%S")
                    key = d.strftime("%Y-%m-%d")
                    uploads_by_date[key] = uploads_by_date.get(key, 0) + 1
                except Exception:
                    continue

            end = datetime.utcnow()
            start = end - timedelta(days=days - 1)
            daily_uploads = []
            for i in range(days):
                date_key = (start + timedelta(days=i)).strftime("%Y-%m-%d")
                daily_uploads.append({
                    "_id": date_key,
                    "count": uploads_by_date.get(date_key, 0)
                })

            return jsonify({"daily_uploads": daily_uploads}), 200

        except Exception as e:
            logger.exception(f"Upload analytics error for user {user_id}")
            return jsonify({"daily_uploads": []}), 200

    # ------------------------------
    # TAG ANALYTICS
    # ------------------------------
    @app.route("/user/analytics/tags", methods=["GET", "OPTIONS"])
    @token_required
    def analytics_tags(user_id):
        """Get user's top keywords"""
        limit = int(request.args.get("limit", 10))
        try:
            files = service_manager.mongodb.get_all_files(user_id=user_id)
            keyword_counts = {}

            for f in files:
                for kw in f.get("ai_analysis", {}).get("keywords", []):
                    if isinstance(kw, str):
                        keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

            top_tags = [{"_id": k, "count": v} for k, v in keyword_counts.items()]
            top_tags.sort(key=lambda x: x["count"], reverse=True)
            top_tags = top_tags[:limit]

            return jsonify({"top_tags": top_tags}), 200

        except Exception as e:
            logger.exception(f"Tag analytics error for user {user_id}")
            return jsonify({"top_tags": []}), 200

    # ------------------------------
    # ACTIVITY ANALYTICS
    # ------------------------------
    @app.route("/user/analytics/activity", methods=["GET", "OPTIONS"])
    @token_required
    def analytics_activity(user_id):
        """Get user's recent upload and analysis activity"""
        hours = int(request.args.get("hours", 24))
        try:
            files = service_manager.mongodb.get_all_files(user_id=user_id)
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            activity = []

            for f in files:
                filename = f.get("filename", "Unknown")

                # Upload event
                upload_val = f.get("minio_uploaded_at")
                if upload_val:
                    try:
                        upload_time = datetime.fromisoformat(str(upload_val).replace("Z", "+00:00"))
                        if upload_time >= cutoff:
                            activity.append({
                                "event_type": "file_uploaded",
                                "resource": filename,
                                "timestamp": upload_time.isoformat(),
                                "details": f"File {filename} uploaded"
                            })
                    except Exception:
                        pass

                # AI analysis event
                ai = f.get("ai_analysis", {})
                if ai and ai.get("analysis_date"):
                    try:
                        analysis_time = datetime.fromisoformat(str(ai["analysis_date"]).replace("Z", "+00:00"))
                        if analysis_time >= cutoff:
                            activity.append({
                                "event_type": "ai_analysis_completed",
                                "resource": filename,
                                "timestamp": analysis_time.isoformat(),
                                "details": f"AI analysis completed for {filename}"
                            })
                    except Exception:
                        pass

            activity.sort(key=lambda x: x["timestamp"], reverse=True)
            return jsonify({"recent_activity": activity}), 200

        except Exception as e:
            logger.exception(f"Activity analytics error for user {user_id}")
            return jsonify({"recent_activity": []}), 200

    return app
