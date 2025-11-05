import logging
from datetime import datetime
from typing import List, Dict, Optional

# from pymongo import MongoClient, DESCENDING
# from pymongo.errors import PyMongoError, DuplicateKeyError
import certifi  # ✅ For trusted SSL certificates
from config import Config
from models.file_model import FileMetadata

logger = logging.getLogger(__name__)

class MongoDBService:
    def __init__(self):
        try:
            logger.info("🔄 Connecting to MongoDB...")

            # ✅ Force TLS 1.2 and use trusted CA from certifi
            self.client = MongoClient(
                Config.MONGO_URI,
                tls=True,
                tlsAllowInvalidCertificates=False,
                tlsCAFile=certifi.where(),
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                serverSelectionTimeoutMS=8000,
            )

            self.client.admin.command("ping")
            logger.info("✅ MongoDB connected successfully")

            self.db = self.client[Config.DB_NAME]
            self.files = self.db[Config.COLLECTION_NAME]

        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}", exc_info=True)
            raise


    # ------------------------------------------------------------
    # INSERT FILE
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
            return [self._normalize(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"❌ MongoDB fetch error: {e}", exc_info=True)
            return []

    # ------------------------------------------------------------
    # GET SINGLE FILE
    # ------------------------------------------------------------
    def get_file(self, filename: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Fetch single file metadata."""
        try:
            query = {"filename": filename}
            if user_id:
                query["user_id"] = user_id
            doc = self.files.find_one(query)
            return self._normalize(doc)
        except PyMongoError as e:
            logger.error(f"❌ MongoDB get_file error for '{filename}': {e}", exc_info=True)
            return None

    # ------------------------------------------------------------
    # DELETE FILE
    # ------------------------------------------------------------
    def delete_file(self, filename: str, user_id: Optional[str] = None) -> bool:
        """Delete a file metadata document (user-scoped)."""
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
            logger.error(f"❌ MongoDB delete error for '{filename}': {e}", exc_info=True)
            return False

    # ------------------------------------------------------------
    # UPDATE FILE
    # ------------------------------------------------------------
    def update_file(self, filename: str, updates: dict, user_id: Optional[str] = None) -> bool:
        """Update file metadata."""
        if not updates:
            return False
        try:
            updates["last_updated"] = datetime.utcnow().isoformat()
            query = {"filename": filename}
            if user_id:
                query["user_id"] = user_id
            result = self.files.update_one(query, {"$set": updates})
            modified = result.modified_count > 0
            logger.info(f"🔄 Updated '{filename}' (user: {user_id}) -> modified={modified}")
            return modified
        except PyMongoError as e:
            logger.error(f"❌ MongoDB update error for '{filename}': {e}", exc_info=True)
            return False

    # ------------------------------------------------------------
    # SEARCH FILES
    # ------------------------------------------------------------
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
            results = [self._normalize(doc) for doc in cursor]
            logger.debug(f"🔍 Search '{query_text}' → {len(results)} files (user={user_id or 'ALL'})")
            return results
        except PyMongoError as e:
            logger.error(f"❌ MongoDB search error for '{query_text}': {e}", exc_info=True)
            return []

    # ------------------------------------------------------------
    # GET PENDING ANALYSIS FILES
    # ------------------------------------------------------------
    def get_pending_analysis_files(self, limit: int = 20) -> List[Dict]:
        """Fetch files waiting for AI analysis."""
        try:
            query = {
                "$or": [
                    {"ai_analysis_status": "pending"},
                    {"ai_analysis_status": {"$exists": False}},
                ]
            }
            cursor = self.files.find(query).sort("minio_uploaded_at", DESCENDING).limit(limit)
            return [self._normalize(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"❌ MongoDB pending analysis fetch error: {e}", exc_info=True)
            return []

    # ------------------------------------------------------------
    # HELPER: Normalize MongoDB document
    # ------------------------------------------------------------
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
