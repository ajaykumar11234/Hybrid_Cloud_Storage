import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from config import Config
from utils.helpers import get_content_type
import io
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class S3Service:
    """AWS S3 service for user-scoped file operations."""

    def __init__(self):
        self.client = None
        self.bucket = None
        logger.info("🔄 Initializing AWS S3 service...")
        self._initialize_client()

    # ------------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------------
    def _initialize_client(self):
        """Initialize S3 client with credentials and test connection."""
        try:
            if not all([Config.AWS_ACCESS_KEY, Config.AWS_SECRET_KEY, Config.AWS_BUCKET]):
                logger.warning("⚠️ Missing AWS S3 configuration, disabling S3 service.")
                return

            self.client = boto3.client(
                "s3",
                aws_access_key_id=Config.AWS_ACCESS_KEY,
                aws_secret_access_key=Config.AWS_SECRET_KEY,
                region_name=Config.AWS_REGION,
            )
            self.bucket = Config.AWS_BUCKET

            # Test bucket access
            self.client.head_bucket(Bucket=self.bucket)
            logger.info(f"✅ Connected to S3 bucket: {self.bucket}")

        except NoCredentialsError:
            logger.error("❌ AWS credentials not found.")
            self.client = None
            self.bucket = None
        except ClientError as e:
            logger.error(f"❌ S3 connection error: {e}", exc_info=True)
            self.client = None
            self.bucket = None
        except Exception as e:
            logger.error(f"❌ Unexpected S3 initialization error: {e}", exc_info=True)
            self.client = None
            self.bucket = None

    def is_available(self) -> bool:
        """Check if S3 client is configured and accessible."""
        return self.client is not None and self.bucket is not None

    # ------------------------------------------------------------
    # FILE OPERATIONS
    # ------------------------------------------------------------
    def upload_file(self, user_id: str, filename: str, file_data: bytes, content_type: Optional[str] = None) -> bool:
        """Upload file to S3 under user-specific path."""
        if not self.is_available():
            logger.warning("⚠️ S3 not available — skipping upload.")
            return False

        try:
            key = f"{user_id}/{filename}"
            content_type = content_type or get_content_type(filename)

            self.client.upload_fileobj(
                Fileobj=io.BytesIO(file_data),
                Bucket=self.bucket,
                Key=key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": {"user_id": user_id, "original_filename": filename},
                },
            )
            logger.info(f"✅ Uploaded {key} ({len(file_data)} bytes) to S3.")
            return True
        except ClientError as e:
            logger.error(f"❌ S3 ClientError uploading {filename}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected upload error for {filename}: {e}", exc_info=True)
            return False

    def get_file(self, user_id: str, filename: str) -> Optional[bytes]:
        """Download a file from S3."""
        if not self.is_available():
            return None

        try:
            key = f"{user_id}/{filename}"
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            file_bytes = response["Body"].read()
            logger.debug(f"📥 Downloaded {key} from S3 ({len(file_bytes)} bytes).")
            return file_bytes
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"⚠️ File not found in S3: {key}")
            else:
                logger.error(f"❌ S3 ClientError fetching {filename}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected download error for {filename}: {e}", exc_info=True)
            return None

    def delete_file(self, user_id: str, filename: str) -> bool:
        """Delete file from S3."""
        if not self.is_available():
            logger.warning("⚠️ S3 not available — skipping delete.")
            return False

        try:
            key = f"{user_id}/{filename}"
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"🗑️ Deleted {key} from S3.")
            return True
        except ClientError as e:
            logger.error(f"❌ S3 ClientError deleting {filename}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected delete error for {filename}: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------
    # PRESIGNED URLS
    # ------------------------------------------------------------
    def generate_presigned_urls(self, user_id: str, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """Generate secure 24h presigned preview + download URLs."""
        if not self.is_available():
            logger.warning("⚠️ S3 not available — cannot generate URLs.")
            return None, None

        try:
            key = f"{user_id}/{filename}"
            content_type = get_content_type(filename)
            expiry_seconds = 86400  # 24 hours

            # Inline preview
            preview_url = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ResponseContentType": content_type,
                    "ResponseContentDisposition": f'inline; filename="{filename}"',
                },
                ExpiresIn=expiry_seconds,
            )

            # Forced download
            download_url = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ResponseContentDisposition": f'attachment; filename="{filename}"',
                },
                ExpiresIn=expiry_seconds,
            )

            logger.info(f"✅ Generated S3 presigned URLs for {key}")
            return preview_url, download_url
        except ClientError as e:
            logger.error(f"❌ S3 ClientError generating URLs for {filename}: {e}", exc_info=True)
            return None, None
        except Exception as e:
            logger.error(f"❌ Unexpected presigned URL error for {filename}: {e}", exc_info=True)
            return None, None

    # ------------------------------------------------------------
    # HEALTH CHECK
    # ------------------------------------------------------------
    def health_check(self) -> bool:
        """Perform a simple health check on S3 service."""
        if not self.is_available():
            return False
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception as e:
            logger.error(f"❌ S3 health check failed: {e}", exc_info=True)
            return False


# ------------------------------------------------------------
# GLOBAL INSTANCE
# ------------------------------------------------------------
logger.info("🔄 Creating global S3 service instance...")
s3_service = S3Service()
