import boto3
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
from config import Config
from utils.helpers import get_content_type
import io
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class S3Service:
    """AWS S3 service for user-scoped file operations with retry safety & validation."""

    def __init__(self):
        self.client = None
        self.bucket = None
        logger.info("🔄 [S3Service] Creating global S3 service instance...")
        print("🔄 [S3Service] Creating global S3 service instance...")
        self._initialize_client()

    # ------------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------------
    def _initialize_client(self):
        """Initialize S3 client with credentials and test bucket access."""
        try:
            if not all([Config.AWS_ACCESS_KEY, Config.AWS_SECRET_KEY, Config.AWS_BUCKET]):
                logger.warning("⚠️ Missing AWS S3 configuration, disabling S3 service.")
                print("⚠️ [S3Service] Missing AWS S3 configuration. Disabling S3 service.")
                return

            session = boto3.session.Session()

            # ✅ Create S3 client with retries enabled
            self.client = session.client(
                "s3",
                aws_access_key_id=Config.AWS_ACCESS_KEY,
                aws_secret_access_key=Config.AWS_SECRET_KEY,
                region_name=Config.AWS_REGION,
                config=boto3.session.Config(
                    retries={"max_attempts": 3, "mode": "standard"}
                ),
            )
            self.bucket = Config.AWS_BUCKET

            # ✅ Test connectivity
            self.client.head_bucket(Bucket=self.bucket)
            logger.info(f"✅ [S3Service] Connected to AWS S3 bucket: {self.bucket}")
            print(f"✅ [S3Service] Connected to AWS S3 bucket: {self.bucket}")

        except NoCredentialsError:
            logger.error("❌ AWS credentials not found.")
            print("❌ [S3Service] AWS credentials not found.")
        except EndpointConnectionError as e:
            logger.error(f"❌ Could not connect to S3 endpoint: {e}", exc_info=True)
            print(f"❌ [S3Service] Could not connect to S3 endpoint: {e}")
        except ClientError as e:
            logger.error(f"❌ S3 connection error: {e}", exc_info=True)
            print(f"❌ [S3Service] S3 connection error: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected S3 initialization error: {e}", exc_info=True)
            print(f"❌ [S3Service] Unexpected S3 initialization error: {e}")

    def is_available(self) -> bool:
        """Check if S3 client is configured and accessible."""
        available = self.client is not None and self.bucket is not None
        logger.debug(f"🧩 [S3Service] Availability check: {available}")
        return available

    # ------------------------------------------------------------
    # FILE UPLOAD
    # ------------------------------------------------------------
    def upload_file(
        self, user_id: str, filename: str, file_data: bytes, content_type: Optional[str] = None
    ) -> bool:
        """Upload a file to S3 under user-specific path."""
        if not self.is_available():
            print("⚠️ [S3Service] S3 not available — skipping upload.")
            return False

        try:
            key = f"{user_id}/{filename}"
            content_type = content_type or get_content_type(filename)

            if not file_data:
                logger.warning(f"⚠️ Skipping upload: Empty data for {filename}")
                return False

            print(f"☁️ [S3Service] Uploading {filename} → {self.bucket}/{key} ...")

            self.client.upload_fileobj(
                Fileobj=io.BytesIO(file_data),
                Bucket=self.bucket,
                Key=key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": {"user_id": user_id, "original_filename": filename},
                },
            )

            logger.info(f"✅ [S3Service] Uploaded {filename} ({len(file_data)} bytes) to S3.")
            return True

        except ClientError as e:
            logger.error(f"❌ [S3Service] ClientError uploading {filename}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"❌ [S3Service] Unexpected upload error for {filename}: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------
    # FILE DOWNLOAD
    # ------------------------------------------------------------
    def get_file(self, user_id: str, filename: str) -> Optional[bytes]:
        """Download a file from S3."""
        if not self.is_available():
            print("⚠️ [S3Service] S3 not available — cannot download.")
            return None

        try:
            key = f"{user_id}/{filename}"
            print(f"📥 [S3Service] Downloading {key} from S3...")
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            file_bytes = response["Body"].read()
            logger.debug(f"📥 [S3Service] Downloaded {key} ({len(file_bytes)} bytes).")
            return file_bytes

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"⚠️ [S3Service] File not found: {filename}")
            else:
                logger.error(f"❌ [S3Service] ClientError fetching {filename}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"❌ [S3Service] Unexpected download error for {filename}: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------
    # FILE DELETE
    # ------------------------------------------------------------
    def delete_file(self, user_id: str, filename: str) -> bool:
        """Delete a file from S3."""
        if not self.is_available():
            print("⚠️ [S3Service] S3 not available — skipping delete.")
            return False

        try:
            key = f"{user_id}/{filename}"
            print(f"🗑️ [S3Service] Deleting {key} from S3...")
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"🗑️ [S3Service] Deleted {key} from S3.")
            return True
        except ClientError as e:
            logger.error(f"❌ [S3Service] ClientError deleting {filename}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"❌ [S3Service] Unexpected delete error for {filename}: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------
    # PRESIGNED URLS
    # ------------------------------------------------------------
    def generate_presigned_urls(self, user_id: str, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """Generate secure 24h presigned preview and download URLs."""
        if not self.is_available():
            print("⚠️ [S3Service] S3 not available — cannot generate URLs.")
            return None, None

        try:
            key = f"{user_id}/{filename}"
            content_type = get_content_type(filename)
            expiry_seconds = 86400  # 24 hours

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

            download_url = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ResponseContentDisposition": f'attachment; filename="{filename}"',
                },
                ExpiresIn=expiry_seconds,
            )

            logger.info(f"🔗 [S3Service] Generated presigned URLs for {filename}")
            return preview_url, download_url

        except ClientError as e:
            logger.error(f"❌ [S3Service] ClientError generating URLs for {filename}: {e}", exc_info=True)
            return None, None
        except Exception as e:
            logger.error(f"❌ [S3Service] Unexpected presigned URL error for {filename}: {e}", exc_info=True)
            return None, None

    # ------------------------------------------------------------
    # HEALTH CHECK
    # ------------------------------------------------------------
    def health_check(self) -> bool:
        """Perform a simple health check on S3 service."""
        if not self.is_available():
            print("⚠️ [S3Service] Health check failed — S3 unavailable.")
            return False
        try:
            self.client.head_bucket(Bucket=self.bucket)
            logger.debug("✅ [S3Service] S3 health check passed.")
            return True
        except Exception as e:
            logger.error(f"❌ [S3Service] S3 health check failed: {e}", exc_info=True)
            return False


# ------------------------------------------------------------
# GLOBAL INSTANCE
# ------------------------------------------------------------
logger.info("🔄 [S3Service] Creating global S3 service instance...")
print("🔄 [S3Service] Creating global S3 service instance...")
try:
    s3_service = S3Service()
    if s3_service.is_available():
        logger.info("✅ [S3Service] Global instance initialized successfully.")
    else:
        logger.warning("⚠️ [S3Service] Initialized but not connected.")
except Exception as e:
    logger.error(f"❌ [S3Service] Failed to initialize: {e}", exc_info=True)
    s3_service = None
