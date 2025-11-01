from minio import Minio
from minio.error import S3Error
from config import Config
from utils.helpers import get_content_type
import io
from datetime import timedelta

class MinioService:
    """MinIO service for file operations"""
    
    def __init__(self):
        self.client = Minio(
            Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            secure=False
        )
        self.bucket = Config.MINIO_BUCKET
        self._ensure_bucket_exists()
        print("✅ MinIO service initialized")
    
    def _ensure_bucket_exists(self):
        """Ensure the MinIO bucket exists"""
        found = self.client.bucket_exists(self.bucket)
        if not found:
            self.client.make_bucket(self.bucket)
            print(f"✅ Created MinIO bucket: {self.bucket}")
    
    def upload_file(self, filename: str, file_data: bytes, content_type: str = None):
        """Upload file to MinIO"""
        if not content_type:
            content_type = get_content_type(filename)
        
        self.client.put_object(
            self.bucket,
            filename,
            data=io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type
        )
        print(f"✅ Uploaded {filename} to MinIO")
    
    def get_file(self, filename: str) -> bytes:
        """Get file from MinIO"""
        try:
            response = self.client.get_object(self.bucket, filename)
            file_data = response.read()
            response.close()
            response.release_conn()
            return file_data
        except S3Error as e:
            print(f"❌ Error getting file {filename} from MinIO: {e}")
            return None
    
    def delete_file(self, filename: str) -> bool:
        """Delete file from MinIO"""
        try:
            self.client.remove_object(self.bucket, filename)
            print(f"✅ Deleted {filename} from MinIO")
            return True
        except S3Error as e:
            print(f"❌ Error deleting file {filename} from MinIO: {e}")
            return False
    
    def generate_presigned_urls(self, filename: str):
        """Generate presigned URLs for MinIO file"""
        try:
            # Preview URL (inline) - FIXED: Use timedelta instead of integer
            preview_url = self.client.presigned_get_object(
                self.bucket,
                filename,
                expires=timedelta(hours=24),  # Fixed: Use timedelta
                response_headers={
                    'response-content-type': get_content_type(filename),
                    'response-content-disposition': f'inline; filename="{filename}"'
                }
            )
            
            # Download URL (attachment) - FIXED: Use timedelta instead of integer
            download_url = self.client.presigned_get_object(
                self.bucket,
                filename,
                expires=timedelta(hours=24),  # Fixed: Use timedelta
                response_headers={
                    'response-content-disposition': f'attachment; filename="{filename}"'
                }
            )
            
            return preview_url, download_url
        except Exception as e:
            print(f"❌ Error generating MinIO URLs for {filename}: {e}")
            return None, None

# Create global instance
minio_service = MinioService()