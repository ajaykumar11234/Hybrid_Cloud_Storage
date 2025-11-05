import logging
from datetime import datetime
from typing import List, Dict, Optional
import ssl
import certifi

# ✅ Import MongoClient & PyMongo errors
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError

from config import Config
from models.file_model import FileMetadata

logger = logging.getLogger(__name__)


class MongoDBService:
    """MongoDB service for user-scoped file metadata operations."""

    def __init__(self):
        try:
            logger.info("🔄 [MongoDB] Initializing connection...")

            # ✅ Secure TLS connection (works on Render)
            self.client = MongoClient(
                Config.MONGO_URI,
                tls=True,
                tlsCAFile=certifi.where(),
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                serverSelectionTimeoutMS=8000
            )

            # ✅ Verify connection
            self.client.admin.command("ping")
            logger.info("✅ [MongoDB] Connected successfully")

            # Select DB and collection
            self.db = self.client[Config.DB_NAME]
            self.files = self.db[Config.COLLECTION_NAME]

            self._ensure_indexes()

        except PyMongoError as e:
            logger.error(f"❌ [MongoDB] Connection or setup failed: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------
    # INDEX SETUP
    # ------------------------------------------------------------
    def _ensure_indexes(self):
        """Ensure required indexes exist on the collection."""
        try:
            existing_indexes = self.files.index_information()

            def create_index_safe(fields, **kwargs):
                name = kwargs.pop("name", "_".join(f"{f[0]}_{f[1]}" for f in fields))
                if name not in existing_indexes:
                    self.files.create_index(fields, name=name, **kwargs)
                    logger.info(f"🆕 Created index: {name}")
                else:
                    logger.debug(f"ℹ️ Index already exists: {name}")

            # Regular indexes
            create_index_safe([("filename", 1)])
            create_index_safe([("user_id", 1)])
            create_index_safe([("minio_uploaded_at", DESCENDING)])
            create_index_safe([("ai_analysis_status", 1)])

            # Text index for search
            text_index_exists = any(
                idx.get("key", {}).get("_fts") == "text"
                for idx in existing_indexes.values()
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
            else:
                logger.debug("ℹ️ Text index already exists")

            logger.info("✅ [MongoDB] Indexes ready")

        except PyMongoError as e:
            logger.error(f"❌ [MongoDB] Index creation failed: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------
    # CRUD OPERATIONS
    # ------------------------------------------------------------
    def insert_file(self, file_meta: FileMetadata) -> str:
        """Insert new file metadata document."""
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
        try:
            query = {"user_id": user_id} if user_id else {}
            cursor = self.files.find(query).sort("minio_uploaded_at", DESCENDING)
            return [self._normalize(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"❌ Fetch error: {e}", exc_info=True)
            return []

    def get_file(self, filename: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Fetch single file metadata."""
        try:
            query = {"filename": filename}
            if user_id:
                query["user_id"] = user_id
            doc = self.files.find_one(query)
            return self._normalize(doc)
        except PyMongoError as e:
            logger.error(f"❌ Get file error: {e}", exc_info=True)
            return None

    def delete_file(self, filename: str, user_id: Optional[str] = None) -> bool:
        """Delete a file metadata document (user-scoped)."""
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
        """Update file metadata."""
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

    def _normalize(self, doc: Optional[Dict]) -> Dict:
        """Normalize MongoDB document for API-safe response."""
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
mongodb_service = MongoDBService()
