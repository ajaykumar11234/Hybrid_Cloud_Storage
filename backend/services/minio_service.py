from minio import Minio
from minio.error import S3Error
from config import Config
from utils.helpers import get_content_type
import io
import logging
from datetime import timedelta
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

class MinioService:
    """Handles file operations in MinIO (local object storage)."""

    def __init__(self):
        self.client = None
        self.bucket = None
        logger.info("🔄 Initializing MinIO service...")
        print("🔄 [MinIO] Initializing MinIO service...")
        self._initialize_client()

    # ------------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------------
    def _initialize_client(self):
        """Initialize MinIO client with error handling."""
        try:
            logger.info(f"🔧 MinIO Config - Endpoint: {Config.MINIO_ENDPOINT}, Bucket: {Config.MINIO_BUCKET}")
            print(f"🔧 [MinIO] Endpoint: {Config.MINIO_ENDPOINT}, Bucket: {Config.MINIO_BUCKET}")

            if not all([Config.MINIO_ENDPOINT, Config.MINIO_ACCESS_KEY, Config.MINIO_SECRET_KEY]):
                logger.warning("⚠️ Missing MinIO configuration")
                print("⚠️ [MinIO] Missing configuration — cannot start client.")
                return

            minio_secure = getattr(Config, "MINIO_SECURE", False)

            self.client = Minio(
                endpoint=Config.MINIO_ENDPOINT,
                access_key=Config.MINIO_ACCESS_KEY,
                secret_key=Config.MINIO_SECRET_KEY,
                secure=minio_secure
            )

            self.bucket = Config.MINIO_BUCKET
            self._ensure_bucket_exists()

            logger.info(f"✅ Connected to MinIO bucket: {self.bucket}")
            print(f"✅ [MinIO] Connected successfully to bucket: {self.bucket}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize MinIO client: {e}", exc_info=True)
            print(f"❌ [MinIO] Initialization failed: {e}")
            self.client = None
            self.bucket = None

    def _ensure_bucket_exists(self):
        """Ensure the configured bucket exists (create if needed)."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"✅ Created new MinIO bucket: {self.bucket}")
                print(f"✅ [MinIO] Created new bucket: {self.bucket}")
        except Exception as e:
            logger.error(f"❌ Error ensuring bucket exists: {e}", exc_info=True)
            print(f"❌ [MinIO] Error ensuring bucket exists: {e}")
            raise

    def is_available(self) -> bool:
        """Check if MinIO is initialized and bucket exists."""
        try:
            available = bool(self.client and self.bucket and self.client.bucket_exists(self.bucket))
            print(f"🧩 [MinIO] Availability check: {available}")
            return available
        except Exception as e:
            logger.error(f"❌ MinIO availability check failed: {e}")
            print(f"❌ [MinIO] Availability check failed: {e}")
            return False

    # ------------------------------------------------------------
    # FILE UPLOAD
    # ------------------------------------------------------------
    def upload_file(self, user_id: str, filename: str, file_data, content_type: Optional[str] = None) -> bool:
        """Upload a file to MinIO under user-specific path."""
        if not self.is_available():
            logger.warning("⚠️ MinIO not available — skipping upload")
            print("⚠️ [MinIO] Not available — skipping upload.")
            return False

        try:
            key = f"{user_id}/{filename}"
            content_type = content_type or get_content_type(filename)

            # Convert data safely
            if isinstance(file_data, str):
                file_data = file_data.encode("utf-8")
            elif not isinstance(file_data, (bytes, bytearray)):
                file_data = bytes(file_data)

            file_bytes = io.BytesIO(file_data)
            size = len(file_data)

            print(f"☁️ [MinIO] Uploading {filename} ({size} bytes)...")
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=key,
                data=file_bytes,
                length=size,
                content_type=content_type
            )

            logger.info(f"✅ Uploaded {key} ({size} bytes)")
            print(f"✅ [MinIO] Uploaded {filename} → {self.bucket}/{key}")
            return True

        except S3Error as e:
            logger.error(f"❌ MinIO S3Error during upload: {e}", exc_info=True)
            print(f"❌ [MinIO] Upload failed: {e}")
        except Exception as e:
            logger.error(f"❌ Upload failed for {filename}: {e}", exc_info=True)
            print(f"❌ [MinIO] Unexpected upload error: {e}")
        return False

    # ------------------------------------------------------------
    # FILE RETRIEVAL
    # ------------------------------------------------------------
    def get_file(self, user_id: str, filename: str) -> Optional[bytes]:
        """Retrieve file bytes from MinIO."""
        if not self.is_available():
            print("⚠️ [MinIO] Unavailable — cannot get file.")
            return None

        key = f"{user_id}/{filename}"
        response = None
        try:
            print(f"📥 [MinIO] Fetching file: {key}")
            response = self.client.get_object(self.bucket, key)
            file_data = response.read()
            logger.info(f"✅ Retrieved {filename} ({len(file_data)} bytes)")
            print(f"✅ [MinIO] Retrieved {filename} ({len(file_data)} bytes)")
            return file_data
        except Exception as e:
            logger.error(f"❌ Error fetching {filename}: {e}", exc_info=True)
            print(f"❌ [MinIO] Error fetching {filename}: {e}")
            return None
        finally:
            if response:
                try:
                    response.close()
                    response.release_conn()
                except Exception:
                    pass

    # ------------------------------------------------------------
    # FILE DELETE
    # ------------------------------------------------------------
    def delete_file(self, user_id: str, filename: str) -> bool:
        """Delete file from MinIO."""
        if not self.is_available():
            print("⚠️ [MinIO] Unavailable — cannot delete file.")
            return False
        try:
            key = f"{user_id}/{filename}"
            print(f"🗑️ [MinIO] Deleting {key} ...")
            self.client.remove_object(self.bucket, key)
            logger.info(f"🗑️ Deleted {key} from MinIO")
            print(f"✅ [MinIO] Deleted {filename} from bucket.")
            return True
        except Exception as e:
            logger.error(f"❌ Delete failed for {filename}: {e}", exc_info=True)
            print(f"❌ [MinIO] Delete failed: {e}")
            return False

    # ------------------------------------------------------------
    # URL GENERATION
    # ------------------------------------------------------------
    def generate_presigned_urls(self, user_id: str, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """Generate 24h presigned preview and download URLs."""
        if not self.is_available():
            print("⚠️ [MinIO] Unavailable — cannot generate URLs.")
            return None, None

        try:
            key = f"{user_id}/{filename}"
            content_type = get_content_type(filename)
            expiry = timedelta(hours=24)

            preview_url = self.client.presigned_get_object(
                bucket_name=self.bucket,
                object_name=key,
                expires=expiry,
                response_headers={
                    "response-content-type": content_type,
                    "response-content-disposition": f'inline; filename="{filename}"'
                },
            )

            download_url = self.client.presigned_get_object(
                bucket_name=self.bucket,
                object_name=key,
                expires=expiry,
                response_headers={
                    "response-content-disposition": f'attachment; filename="{filename}"'
                },
            )

            logger.info(f"✅ Generated presigned URLs for {key}")
            print(f"🔗 [MinIO] Generated presigned URLs for {filename}")
            return preview_url, download_url

        except Exception as e:
            logger.error(f"❌ Presigned URL generation failed for {filename}: {e}", exc_info=True)
            print(f"❌ [MinIO] URL generation failed for {filename}: {e}")
            return None, None

    # ------------------------------------------------------------
    # EXTRA UTILITIES
    # ------------------------------------------------------------
    def list_user_files(self, user_id: str) -> List[dict]:
        """List all objects for a given user prefix."""
        if not self.is_available():
            print("⚠️ [MinIO] Unavailable — cannot list files.")
            return []
        try:
            prefix = f"{user_id}/"
            files = []
            for obj in self.client.list_objects(self.bucket, prefix=prefix, recursive=True):
                files.append({
                    "name": obj.object_name.replace(prefix, ""),
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                })
            logger.info(f"✅ Listed {len(files)} files for user {user_id}")
            print(f"📄 [MinIO] Listed {len(files)} files for user {user_id}")
            return files
        except Exception as e:
            logger.error(f"❌ Error listing files for {user_id}: {e}", exc_info=True)
            print(f"❌ [MinIO] Error listing files for {user_id}: {e}")
            return []

    def get_file_info(self, user_id: str, filename: str) -> Optional[dict]:
        """Return metadata for a specific file."""
        if not self.is_available():
            return None
        try:
            key = f"{user_id}/{filename}"
            stat = self.client.stat_object(self.bucket, key)
            print(f"ℹ️ [MinIO] Fetched info for {filename}")
            return {
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "etag": stat.etag,
            }
        except Exception as e:
            logger.error(f"❌ Failed to get info for {filename}: {e}", exc_info=True)
            print(f"❌ [MinIO] Failed to get info for {filename}: {e}")
            return None

    def health_check(self) -> bool:
        """Simple availability check."""
        try:
            available = self.is_available()
            print(f"✅ [MinIO] Health check: {available}")
            return available
        except Exception as e:
            logger.error(f"❌ MinIO health check failed: {e}")
            print(f"❌ [MinIO] Health check failed: {e}")
            return False


# Global instance
logger.info("🔄 Creating global MinIO service instance...")
print("🔄 [MinIO] Creating global MinIO service instance...")
minio_service = MinioService()
