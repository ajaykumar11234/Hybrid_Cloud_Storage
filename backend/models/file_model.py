# models/file_model.py
from datetime import datetime
from typing import Optional, Dict

class FileMetadata:
    """Data model for file metadata with user ownership and virus scan tracking"""

    def __init__(self, filename: str, size: int, content_type: str, user_id: Optional[str] = None):
        self.filename = filename
        self.size = size
        self.content_type = content_type
        self.status = "minio"
        self.user_id = user_id  # ✅ Each file belongs to a specific user

        # Storage URLs
        self.minio_preview_url: Optional[str] = None
        self.minio_download_url: Optional[str] = None
        self.s3_preview_url: Optional[str] = None
        self.s3_download_url: Optional[str] = None

        # Timestamps
        now = datetime.utcnow().isoformat()
        self.created_at = now
        self.minio_uploaded_at = now
        self.s3_synced_at: Optional[str] = None
        self.last_updated: Optional[str] = now

        # ✅ Virus Scan Fields
        self.scan_status: str = "pending"      # pending | clean | infected | error
        self.virus_name: Optional[str] = None  # Detected virus name, if any

        # AI Analysis
        self.ai_analysis_status: str = "pending"
        self.ai_analysis: Optional[Dict] = None
        self.ai_analysis_completed_at: Optional[str] = None
        self.ai_error: Optional[str] = None

    # -------------------------------------------------------------
    # Convert to Dictionary (for MongoDB)
    # -------------------------------------------------------------
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage"""
        return {
            "filename": self.filename,
            "size": self.size,
            "content_type": self.content_type,
            "status": self.status,
            "user_id": self.user_id,
            "minio_preview_url": self.minio_preview_url,
            "minio_download_url": self.minio_download_url,
            "s3_preview_url": self.s3_preview_url,
            "s3_download_url": self.s3_download_url,
            "created_at": self.created_at,
            "minio_uploaded_at": self.minio_uploaded_at,
            "s3_synced_at": self.s3_synced_at,
            "last_updated": self.last_updated,

            # ✅ Virus Scan info
            "scan_status": self.scan_status,
            "virus_name": self.virus_name,

            # ✅ AI Analysis info
            "ai_analysis_status": self.ai_analysis_status,
            "ai_analysis": self.ai_analysis,
            "ai_analysis_completed_at": self.ai_analysis_completed_at,
            "ai_error": self.ai_error,
        }

    # -------------------------------------------------------------
    # Rebuild from MongoDB Document
    # -------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: Dict) -> "FileMetadata":
        """Rebuild FileMetadata from MongoDB document"""
        file_meta = cls(
            filename=data["filename"],
            size=data["size"],
            content_type=data["content_type"],
            user_id=data.get("user_id")
        )

        # Storage and sync info
        file_meta.status = data.get("status", "minio")
        file_meta.minio_preview_url = data.get("minio_preview_url")
        file_meta.minio_download_url = data.get("minio_download_url")
        file_meta.s3_preview_url = data.get("s3_preview_url")
        file_meta.s3_download_url = data.get("s3_download_url")

        # Time info
        file_meta.created_at = data.get("created_at", datetime.utcnow().isoformat())
        file_meta.minio_uploaded_at = data.get("minio_uploaded_at", datetime.utcnow().isoformat())
        file_meta.s3_synced_at = data.get("s3_synced_at")
        file_meta.last_updated = data.get("last_updated", datetime.utcnow().isoformat())

        # ✅ Virus scan info
        file_meta.scan_status = data.get("scan_status", "pending")
        file_meta.virus_name = data.get("virus_name")

        # ✅ AI analysis info
        file_meta.ai_analysis_status = data.get("ai_analysis_status", "pending")
        file_meta.ai_analysis = data.get("ai_analysis")
        file_meta.ai_analysis_completed_at = data.get("ai_analysis_completed_at")
        file_meta.ai_error = data.get("ai_error")

        return file_meta
