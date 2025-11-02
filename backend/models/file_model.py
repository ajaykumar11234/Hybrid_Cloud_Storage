from datetime import datetime
from typing import Optional, Dict, List

class FileMetadata:
    """Data model for file metadata"""
    
    def __init__(self, filename: str, size: int, content_type: str):
        self.filename = filename
        self.size = size
        self.content_type = content_type
        self.status = "minio"
        self.minio_preview_url: Optional[str] = None
        self.minio_download_url: Optional[str] = None
        self.s3_preview_url: Optional[str] = None
        self.s3_download_url: Optional[str] = None
        self.created_at = datetime.utcnow().isoformat()  # Store as string
        self.minio_uploaded_at = datetime.utcnow().isoformat()  # Store as string
        self.s3_synced_at: Optional[str] = None
        self.ai_analysis_status = "pending"
        self.ai_analysis: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage"""
        return {
            "filename": self.filename,
            "size": self.size,
            "content_type": self.content_type,
            "status": self.status,
            "minio_preview_url": self.minio_preview_url,
            "minio_download_url": self.minio_download_url,
            "s3_preview_url": self.s3_preview_url,
            "s3_download_url": self.s3_download_url,
            "created_at": self.created_at,  # Already string
            "minio_uploaded_at": self.minio_uploaded_at,  # Already string
            "s3_synced_at": self.s3_synced_at,
            "ai_analysis_status": self.ai_analysis_status,
            "ai_analysis": self.ai_analysis
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FileMetadata':
        """Create FileMetadata from dictionary"""
        file_meta = cls(
            filename=data["filename"],
            size=data["size"],
            content_type=data["content_type"]
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