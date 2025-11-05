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
    """Verify JWT and extract user_id"""
    @wraps(f)
    def decorated(*args, **kwargs):
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
    """Setup analytics routes for each user (JWT-protected)"""

    # ------------------------------
    # SEARCH ANALYTICS
    # ------------------------------
    @app.route("/user/analytics/search", methods=["GET", "OPTIONS"])
    @token_required
    def analytics_search_files(user_id):
        """Search user files by query, tags, or date"""
        query = request.args.get("q", "").strip()
        search_type = request.args.get("type", "text")
        tags_param = request.args.get("tags", "")
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")

        try:
            all_files = service_manager.mongodb.get_all_files(user_id=user_id)
            results = []

            # --- TAG SEARCH ---
            if search_type == "tags":
                tags = [t.strip().lower() for t in tags_param.split(",") if t.strip()]
                for file in all_files:
                    keywords = file.get("ai_analysis", {}).get("keywords", [])
                    if any(tag in [k.lower() for k in keywords] for tag in tags):
                        results.append(file)

            # --- DATE SEARCH ---
            elif search_type == "date":
                for file in all_files:
                    upload_date_value = file.get("minio_uploaded_at") or file.get("uploaded_at")
                    if not upload_date_value:
                        continue
                    try:
                        if isinstance(upload_date_value, datetime):
                            upload_date = upload_date_value
                        else:
                            if "T" in upload_date_value:
                                upload_date = datetime.fromisoformat(upload_date_value.replace("Z", "+00:00"))
                            else:
                                upload_date = datetime.strptime(upload_date_value, "%Y-%m-%d %H:%M:%S")
                        file_date = upload_date.date()

                        if start_date and end_date:
                            s = datetime.strptime(start_date, "%Y-%m-%d").date()
                            e = datetime.strptime(end_date, "%Y-%m-%d").date()
                            if s <= file_date <= e:
                                results.append(file)
                        elif start_date:
                            s = datetime.strptime(start_date, "%Y-%m-%d").date()
                            if file_date >= s:
                                results.append(file)
                        elif end_date:
                            e = datetime.strptime(end_date, "%Y-%m-%d").date()
                            if file_date <= e:
                                results.append(file)
                    except Exception:
                        continue

            # --- TEXT SEARCH ---
            else:
                if query:
                    q_lower = query.lower()
                    for file in all_files:
                        filename = file.get("filename", "").lower()
                        if q_lower in filename:
                            results.append(file)
                            continue

                        ai_data = file.get("ai_analysis", {})
                        summary = ai_data.get("summary", "").lower()
                        caption = ai_data.get("caption", "").lower()
                        keywords = [k.lower() for k in ai_data.get("keywords", [])]

                        if (q_lower in summary or q_lower in caption or
                            any(q_lower in kw for kw in keywords)):
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
            logger.exception(f"Search analytics error for user {user_id}")
            return jsonify({"error": str(e), "results": [], "count": 0}), 500


    # ------------------------------
    # STORAGE ANALYTICS
    # ------------------------------
    @app.route("/user/analytics/storage", methods=["GET", "OPTIONS"])
    @token_required
    def analytics_storage(user_id):
        """Get user's storage statistics"""
        try:
            files = service_manager.mongodb.get_all_files(user_id=user_id)
            total = len(files)
            total_size = sum(f.get("size", 0) for f in files)
            avg_size = total_size / total if total > 0 else 0
            analyzed = sum(1 for f in files if f.get("ai_analysis_status") == "completed")

            status_dist = {}
            for f in files:
                status = f.get("status", "unknown")
                status_dist[status] = status_dist.get(status, 0) + 1

            return jsonify({
                "storage": {
                    "total_files": total,
                    "total_size": total_size,
                    "avg_file_size": avg_size,
                    "files_analyzed": analyzed,
                    "status_distribution": status_dist
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
        """Daily upload statistics"""
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
                    else:
                        if "T" in date_val:
                            d = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                        else:
                            d = datetime.strptime(date_val, "%Y-%m-%d %H:%M:%S")
                    key = d.strftime("%Y-%m-%d")
                    uploads_by_date[key] = uploads_by_date.get(key, 0) + 1
                except Exception:
                    continue

            end = datetime.now()
            start = end - timedelta(days=days - 1)
            current = start
            daily_uploads = []

            while current <= end:
                key = current.strftime("%Y-%m-%d")
                daily_uploads.append({
                    "_id": key,
                    "count": uploads_by_date.get(key, 0)
                })
                current += timedelta(days=1)

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
        """Get user's top tags/keywords"""
        limit = int(request.args.get("limit", 10))
        try:
            files = service_manager.mongodb.get_all_files(user_id=user_id)
            keyword_counts = {}

            for f in files:
                keywords = f.get("ai_analysis", {}).get("keywords", [])
                for kw in keywords:
                    if kw and isinstance(kw, str):
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
        """Recent user activity (uploads, analysis, etc.)"""
        hours = int(request.args.get("hours", 24))
        try:
            files = service_manager.mongodb.get_all_files(user_id=user_id)
            activity = []

            for f in files:
                filename = f.get("filename", "Unknown")

                # Upload event
                upload_val = f.get("minio_uploaded_at")
                if upload_val:
                    try:
                        if isinstance(upload_val, datetime):
                            upload_time = upload_val
                        else:
                            upload_time = datetime.fromisoformat(upload_val.replace("Z", "+00:00"))
                        if upload_time >= datetime.utcnow() - timedelta(hours=hours):
                            activity.append({
                                "event_type": "file_uploaded",
                                "resource": filename,
                                "timestamp": upload_time.isoformat(),
                                "details": f"File {filename} uploaded"
                            })
                    except Exception:
                        continue

                # AI analysis event
                ai_analysis = f.get("ai_analysis")
                if ai_analysis and isinstance(ai_analysis, dict):
                    analysis_date = ai_analysis.get("analysis_date")
                    if analysis_date:
                        try:
                            if isinstance(analysis_date, datetime):
                                analysis_time = analysis_date
                            else:
                                analysis_time = datetime.fromisoformat(analysis_date.replace("Z", "+05:30"))
                            if analysis_time >= datetime.utcnow() - timedelta(hours=hours):
                                activity.append({
                                    "event_type": "ai_analysis_completed",
                                    "resource": filename,
                                    "timestamp": analysis_time.isoformat(),
                                    "details": f"AI analysis completed for {filename}"
                                })
                        except Exception:
                            continue

            activity.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return jsonify({"recent_activity": activity}), 200

        except Exception as e:
            logger.exception(f"Activity analytics error for user {user_id}")
            return jsonify({"recent_activity": []}), 200

    return app
