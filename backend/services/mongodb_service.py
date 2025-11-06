import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import certifi
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError

from config import Config
from models.file_model import FileMetadata

logger = logging.getLogger(__name__)


class MongoDBService:
    """MongoDB service for user-scoped file metadata operations."""

    def __init__(self):
        try:
            logger.info("🔄 [MongoDB] Initializing secure TLS connection...")

            self.client = MongoClient(
                Config.MONGO_URI,
                tls=True,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=20000,  # 20s timeout
            )

            # ✅ Connectivity check
            self.client.admin.command("ping")
            logger.info("✅ [MongoDB] Connected successfully")

            # Select DB and collection
            self.db = self.client[Config.DB_NAME]
            self.files = self.db[Config.COLLECTION_NAME]

            # Ensure indexes exist
            self._ensure_indexes()

        except PyMongoError as e:
            logger.error(f"❌ [MongoDB] Connection or setup failed: {e}", exc_info=True)
            self.client = None
            self.db = None
            self.files = None

    # ------------------------------------------------------------
    # INDEX SETUP
    # ------------------------------------------------------------
    def _ensure_indexes(self):
        """Ensure required indexes exist on the collection."""
        if self.files is None:
            logger.warning("⚠️ [MongoDB] Skipping index setup — collection unavailable.")
            return

        try:
            existing_indexes = self.files.index_information()

            def create_index_safe(fields, **kwargs):
                name = kwargs.pop("name", "_".join(f"{f[0]}_{f[1]}" for f in fields))
                if name not in existing_indexes:
                    self.files.create_index(fields, name=name, **kwargs)
                    logger.info(f"🆕 Created index: {name}")

            # Core indexes
            create_index_safe([("filename", 1)])
            create_index_safe([("user_id", 1)])
            create_index_safe([("minio_uploaded_at", DESCENDING)])
            create_index_safe([("ai_analysis_status", 1)])

            # Text index for search
            text_index_exists = any(
                "text" in str(idx_info.get("key", "")) for idx_info in existing_indexes.values()
            )
            if not text_index_exists:
                self.files.create_index(
                    [
                        ("filename", "text"),
                        ("ai_analysis.summary", "text"),
                        ("ai_analysis.keywords", "text"),
                    ],
                    name="text_search_index",
                    default_language="english",
                )
                logger.info("🆕 Created text index for search")

            logger.info("✅ [MongoDB] Indexes ready")

        except PyMongoError as e:
            logger.error(f"❌ [MongoDB] Index creation failed: {e}", exc_info=True)

    # ------------------------------------------------------------
    # CRUD OPERATIONS
    # ------------------------------------------------------------
    def insert_file(self, file_meta: FileMetadata) -> str:
        """Insert new file metadata document."""
        if self.files is None:
            logger.error("❌ [MongoDB] Insert failed — connection unavailable.")
            return ""

        try:
            file_dict = file_meta.to_dict()
            file_dict.setdefault("minio_uploaded_at", datetime.utcnow().isoformat())
            file_dict.setdefault("status", "minio")
            file_dict.setdefault("ai_analysis_status", "pending")

            result = self.files.insert_one(file_dict)
            logger.info(f"✅ Inserted metadata for '{file_meta.filename}' (user: {file_meta.user_id})")
            return str(result.inserted_id)

        except DuplicateKeyError:
            logger.warning(f"⚠️ Duplicate file entry: {file_meta.filename}")
            raise
        except PyMongoError as e:
            logger.error(f"❌ Insert error for {file_meta.filename}: {e}", exc_info=True)
            raise

    def get_all_files(self, user_id: Optional[str] = None) -> List[Dict]:
        """Fetch all files for a specific user."""
        if self.files is None:
            logger.warning("⚠️ [MongoDB] get_all_files() skipped — no DB connection.")
            return []

        try:
            query = {"user_id": user_id} if user_id else {}
            cursor = self.files.find(query).sort("minio_uploaded_at", DESCENDING)
            return [self._normalize(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"❌ Fetch error: {e}", exc_info=True)
            return []

    def get_file(self, filename: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Fetch a single file metadata entry."""
        if self.files is None:
            logger.warning("⚠️ [MongoDB] get_file() skipped — no DB connection.")
            return None

        try:
            query = {"filename": filename}
            if user_id:
                query["user_id"] = user_id
            doc = self.files.find_one(query)
            return self._normalize(doc)
        except PyMongoError as e:
            logger.error(f"❌ Get file error for '{filename}': {e}", exc_info=True)
            return None

    # ✅ NEW — Compatibility alias for older routes
    def get_file_by_filename(self, filename: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Alias for get_file() to maintain backward compatibility."""
        logger.debug(f"🔍 [MongoDB] get_file_by_filename() called for {filename}")
        return self.get_file(filename, user_id)

    def delete_file(self, filename: str, user_id: Optional[str] = None) -> bool:
        """Delete a file metadata document."""
        if self.files is None:
            logger.warning("⚠️ [MongoDB] delete_file() skipped — no DB connection.")
            return False

        try:
            query = {"filename": filename}
            if user_id:
                query["user_id"] = user_id
            result = self.files.delete_one(query)
            if result.deleted_count > 0:
                logger.info(f"🗑️ Deleted '{filename}' (user: {user_id})")
                return True
            logger.warning(f"⚠️ File not found for deletion: {filename}")
            return False
        except PyMongoError as e:
            logger.error(f"❌ Delete error: {e}", exc_info=True)
            return False

    def update_file(self, filename: str, updates: dict, user_id: Optional[str] = None) -> bool:
        """Update file metadata document."""
        if self.files is None:
            logger.warning("⚠️ [MongoDB] update_file() skipped — no DB connection.")
            return False

        try:
            updates["last_updated"] = datetime.utcnow().isoformat()
            query = {"filename": filename}
            if user_id:
                query["user_id"] = user_id
            result = self.files.update_one(query, {"$set": updates})
            logger.info(f"🔄 Updated '{filename}' (user: {user_id})")
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"❌ Update error: {e}", exc_info=True)
            return False

    def search_files(self, query_text: str, user_id: Optional[str] = None) -> List[Dict]:
        """Search user's files by filename, summary, caption, or keywords."""
        if self.files is None:
            logger.warning("⚠️ [MongoDB] search_files() skipped — no DB connection.")
            return []

        try:
            if not query_text:
                return self.get_all_files(user_id)

            filters = [
                {"filename": {"$regex": query_text, "$options": "i"}},
                {"ai_analysis.summary": {"$regex": query_text, "$options": "i"}},
                {"ai_analysis.caption": {"$regex": query_text, "$options": "i"}},
                {"ai_analysis.keywords": {"$regex": query_text, "$options": "i"}},
            ]

            query = {"$and": [{"user_id": user_id}, {"$or": filters}]} if user_id else {"$or": filters}
            cursor = self.files.find(query).sort("minio_uploaded_at", DESCENDING)
            return [self._normalize(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"❌ Search error: {e}", exc_info=True)
            return []

    # ------------------------------------------------------------
    # ANALYTICS HELPER FUNCTIONS
    # ------------------------------------------------------------
    def get_storage_stats(self) -> Dict:
        """Compute global storage statistics."""
        try:
            files = list(self.files.find())
            total = len(files)
            total_size = sum(f.get("size", 0) for f in files)
            avg_size = total_size / total if total > 0 else 0
            analyzed = sum(1 for f in files if f.get("ai_analysis_status") == "completed")

            status_dist = {}
            for f in files:
                s = f.get("status", "unknown")
                status_dist[s] = status_dist.get(s, 0) + 1

            return {
                "total_files": total,
                "total_size": total_size,
                "avg_file_size": avg_size,
                "files_analyzed": analyzed,
                "status_distribution": status_dist,
            }
        except Exception as e:
            logger.error(f"❌ Storage stats error: {e}")
            return {}

    def get_upload_trends(self, days: int = 30) -> List[Dict]:
        """Get upload counts per day."""
        try:
            end = datetime.utcnow()
            start = end - timedelta(days=days - 1)
            cursor = self.files.find({"minio_uploaded_at": {"$exists": True}})

            counts = {}
            for doc in cursor:
                date_str = str(doc.get("minio_uploaded_at", ""))[:10]
                if date_str:
                    counts[date_str] = counts.get(date_str, 0) + 1

            trends = []
            for i in range(days):
                date = (start + timedelta(days=i)).strftime("%Y-%m-%d")
                trends.append({"_id": date, "count": counts.get(date, 0)})
            return trends
        except Exception as e:
            logger.error(f"❌ Upload trends error: {e}")
            return []

    def get_top_keywords(self, limit: int = 10) -> List[Dict]:
        """Get top AI keywords across all files."""
        try:
            keyword_counts = {}
            for f in self.files.find():
                for kw in f.get("ai_analysis", {}).get("keywords", []):
                    if isinstance(kw, str):
                        keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

            top = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
            return [{"_id": k, "count": v} for k, v in top]
        except Exception as e:
            logger.error(f"❌ Top keyword error: {e}")
            return []

    def get_recent_files(self, limit: int = 50) -> List[Dict]:
        """Fetch most recent uploaded files."""
        try:
            cursor = self.files.find().sort("minio_uploaded_at", DESCENDING).limit(limit)
            return [self._normalize(doc) for doc in cursor]
        except Exception as e:
            logger.error(f"❌ Recent files error: {e}")
            return []

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------
    def _normalize(self, doc: Optional[Dict]) -> Dict:
        """Normalize MongoDB document for safe API responses."""
        if not doc:
            return {}
        d = dict(doc)
        d["_id"] = str(d.get("_id"))
        d.setdefault("ai_analysis_status", "pending")
        d.setdefault("status", "minio")
        d.setdefault("minio_uploaded_at", d.get("minio_uploaded_at", datetime.utcnow().isoformat()))
        return d


# ------------------------------------------------------------
# GLOBAL INSTANCE
# ------------------------------------------------------------
logger.info("🔄 Creating global MongoDB service instance...")

try:
    mongodb_service = MongoDBService()
    if mongodb_service.client:
        logger.info("✅ [MongoDB] Global instance initialized successfully.")
    else:
        logger.warning("⚠️ [MongoDB] Instance created but connection unavailable.")
except Exception as e:
    logger.error(f"❌ [MongoDB] Failed to create global instance: {e}", exc_info=True)
    mongodb_service = None
