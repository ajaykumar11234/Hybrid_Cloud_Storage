from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError
from config import Config
from models.file_model import FileMetadata
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class MongoDBService:
    """MongoDB service for user-scoped file metadata operations."""

    def __init__(self):
        try:
            # Initialize MongoDB client
            self.client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
            self.db = self.client[Config.DB_NAME]
            self.files = self.db[Config.COLLECTION_NAME]

            # Verify connection
            self.client.admin.command("ping")
            logger.info("✅ MongoDB connected successfully")

            # Ensure indexes exist
            existing = self.files.index_information()
            if "filename_1" not in existing:
                self.files.create_index([("filename", 1)])
            if "user_id_1" not in existing:
                self.files.create_index([("user_id", 1)])
            if "minio_uploaded_at_-1" not in existing:
                self.files.create_index([("minio_uploaded_at", DESCENDING)])
            if "ai_analysis_status_1" not in existing:
                self.files.create_index([("ai_analysis_status", 1)])

            logger.info("✅ MongoDB indexes ready")

        except PyMongoError as e:
            logger.error(f"❌ MongoDB initialization error: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------
    # INSERT
    # ------------------------------------------------------------
    def insert_file(self, file_meta: FileMetadata) -> str:
        """Insert file metadata document."""
        try:
            file_dict = file_meta.to_dict()
            file_dict.setdefault("minio_uploaded_at", datetime.utcnow().isoformat())
            file_dict.setdefault("status", "minio")
            file_dict.setdefault("ai_analysis_status", "pending")

            result = self.files.insert_one(file_dict)
            logger.info(f"✅ Inserted metadata for '{file_meta.filename}' (user: {file_meta.user_id})")
            return str(result.inserted_id)
        except DuplicateKeyError:
            logger.warning(f"⚠️ Duplicate file: {file_meta.filename}")
            raise
        except PyMongoError as e:
            logger.error(f"❌ MongoDB insert error for {file_meta.filename}: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------
    # GET ALL FILES
    # ------------------------------------------------------------
    def get_all_files(self, user_id: Optional[str] = None) -> List[Dict]:
        """Fetch all files for a specific user."""
        try:
            query = {"user_id": user_id} if user_id else {}
            cursor = self.files.find(query).sort("minio_uploaded_at", DESCENDING)
            files = [self._normalize(doc) for doc in cursor]
            logger.debug(f"📂 Retrieved {len(files)} files for user {user_id}")
            return files
        except PyMongoError as e:
            logger.error(f"❌ MongoDB fetch error: {e}", exc_info=True)
            return []

    # ------------------------------------------------------------
    # GET SINGLE FILE
    # ------------------------------------------------------------
    def get_file(self, filename: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Get a single file metadata document."""
        try:
            query = {"filename": filename}
            if user_id:
                query["user_id"] = user_id
            doc = self.files.find_one(query)
            return self._normalize(doc)
        except PyMongoError as e:
            logger.error(f"❌ MongoDB error fetching file {filename}: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------
    # DELETE FILE
    # ------------------------------------------------------------
    def delete_file(self, filename: str, user_id: Optional[str] = None) -> bool:
        """Delete file metadata document."""
        try:
            query = {"filename": filename}
            if user_id:
                query["user_id"] = user_id
            result = self.files.delete_one(query)
            deleted = result.deleted_count > 0
            if deleted:
                logger.info(f"🗑️ Deleted metadata for '{filename}' (user: {user_id})")
            else:
                logger.warning(f"⚠️ File not found for deletion: {filename} (user: {user_id})")
            return deleted
        except PyMongoError as e:
            logger.error(f"❌ MongoDB delete error for {filename}: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------
    # UPDATE FILE
    # ------------------------------------------------------------
    def update_file(self, filename: str, data: dict, user_id: Optional[str] = None) -> bool:
        """Update file metadata document."""
        if not data:
            return False
        try:
            data["last_updated"] = datetime.utcnow().isoformat()
            query = {"filename": filename}
            if user_id:
                query["user_id"] = user_id
            result = self.files.update_one(query, {"$set": data})
            modified = result.modified_count > 0
            logger.info(f"🔄 Updated metadata for {filename} (user: {user_id}) -> modified: {modified}")
            return modified
        except PyMongoError as e:
            logger.error(f"❌ MongoDB update error for {filename}: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------
    # SEARCH FILES
    # ------------------------------------------------------------
    def search_files(self, query_text: str, user_id: Optional[str] = None) -> List[Dict]:
        """Search user's files by filename, AI keywords, or summary."""
        try:
            if not query_text:
                return self.get_all_files(user_id)

            filters = [
                {"filename": {"$regex": query_text, "$options": "i"}},
                {"ai_analysis.keywords": {"$regex": query_text, "$options": "i"}},
                {"ai_analysis.summary": {"$regex": query_text, "$options": "i"}},
            ]
            query = {"$and": [{"user_id": user_id}, {"$or": filters}]} if user_id else {"$or": filters}

            cursor = self.files.find(query).sort("minio_uploaded_at", DESCENDING)
            results = [self._normalize(doc) for doc in cursor]
            logger.debug(f"🔍 Search results for '{query_text}' (user: {user_id}) -> {len(results)} files")
            return results
        except PyMongoError as e:
            logger.error(f"❌ MongoDB search error for '{query_text}': {e}", exc_info=True)
            return []

    # ------------------------------------------------------------
    # PENDING ANALYSIS FILES
    # ------------------------------------------------------------
    def get_pending_analysis_files(self, limit: int = 20) -> List[Dict]:
        """Get files waiting for AI analysis."""
        try:
            query = {"$or": [
                {"ai_analysis_status": "pending"},
                {"ai_analysis_status": {"$exists": False}},
            ]}
            cursor = self.files.find(query).sort("minio_uploaded_at", DESCENDING).limit(limit)
            return [self._normalize(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"❌ MongoDB error fetching pending files: {e}", exc_info=True)
            return []

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------
    def _normalize(self, doc: Optional[Dict]) -> Dict:
        """Normalize MongoDB document."""
        if not doc:
            return {}
        d = dict(doc)
        d["_id"] = str(d.get("_id"))
        d.setdefault("ai_analysis_status", d.get("ai_analysis_status", "pending"))
        d.setdefault("status", d.get("status", "minio"))
        d.setdefault("minio_uploaded_at", d.get("minio_uploaded_at", datetime.utcnow().isoformat()))
        return d

# ------------------------------------------------------------
# GLOBAL INSTANCE
# ------------------------------------------------------------
logger.info("🔄 Creating global MongoDB service instance...")
mongodb_service = MongoDBService()
