# models/file_model.py
from datetime import datetime
from typing import Optional, Dict

class FileMetadata:
    """Data model for file metadata with user ownership support"""

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

        # AI Analysis
        self.ai_analysis_status = "pending"
        self.ai_analysis: Optional[Dict] = None

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
            "ai_analysis_status": self.ai_analysis_status,
            "ai_analysis": self.ai_analysis,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FileMetadata":
        """Rebuild FileMetadata from MongoDB document"""
        file_meta = cls(
            filename=data["filename"],
            size=data["size"],
            content_type=data["content_type"],
            user_id=data.get("user_id")
        )
        file_meta.status = data.get("status", "minio")
        file_meta.minio_preview_url = data.get("minio_preview_url")
        file_meta.minio_download_url = data.get("minio_download_url")
        file_meta.s3_preview_url = data.get("s3_preview_url")
        file_meta.s3_download_url = data.get("s3_download_url")
        file_meta.created_at = data.get("created_at", datetime.utcnow().isoformat())
        file_meta.minio_uploaded_at = data.get("minio_uploaded_at", datetime.utcnow().isoformat())
        file_meta.s3_synced_at = data.get("s3_synced_at")
        file_meta.ai_analysis_status = data.get("ai_analysis_status", "pending")
        file_meta.ai_analysis = data.get("ai_analysis")
        return file_meta
