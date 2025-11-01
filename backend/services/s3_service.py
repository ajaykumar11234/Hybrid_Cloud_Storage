import boto3
from config import Config
from utils.helpers import get_content_type
import io

class S3Service:
    """AWS S3 service for file operations"""
    
    def __init__(self):
        if Config.AWS_ACCESS_KEY and Config.AWS_SECRET_KEY:
            self.client = boto3.client(
                "s3",
                aws_access_key_id=Config.AWS_ACCESS_KEY,
                aws_secret_access_key=Config.AWS_SECRET_KEY,
                region_name=Config.AWS_REGION,
            )
            self.bucket = Config.AWS_BUCKET
            print("✅ AWS S3 service initialized")
        else:
            self.client = None
            self.bucket = None
            print("⚠️ AWS credentials not found, S3 service disabled")
    
    def is_available(self) -> bool:
        """Check if S3 service is available"""
        return self.client is not None and self.bucket is not None
    
    def upload_file(self, filename: str, file_data: bytes, content_type: str = None):
        """Upload file to S3"""
        if not self.is_available():
            return False
        
        if not content_type:
            content_type = get_content_type(filename)
        
        try:
            self.client.upload_fileobj(
                io.BytesIO(file_data),
                self.bucket,
                filename,
                ExtraArgs={'ContentType': content_type}
            )
            print(f"✅ Uploaded {filename} to S3")
            return True
        except Exception as e:
            print(f"❌ Error uploading {filename} to S3: {e}")
            return False
    
    def get_file(self, filename: str) -> bytes:
        """Get file from S3"""
        if not self.is_available():
            return None
        
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=filename)
            file_data = response['Body'].read()
            return file_data
        except Exception as e:
            print(f"❌ Error getting file {filename} from S3: {e}")
            return None
    
    def delete_file(self, filename: str) -> bool:
        """Delete file from S3"""
        if not self.is_available():
            return False
        
        try:
            self.client.delete_object(Bucket=self.bucket, Key=filename)
            print(f"✅ Deleted {filename} from S3")
            return True
        except Exception as e:
            print(f"❌ Error deleting file {filename} from S3: {e}")
            return False
    
    def generate_presigned_urls(self, filename: str):
        """Generate presigned URLs for S3 file"""
        if not self.is_available():
            return None, None
        
        try:
            # Preview URL (inline) - S3 uses seconds (integer), which is correct
            preview_url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': filename,
                    'ResponseContentType': get_content_type(filename),
                    'ResponseContentDisposition': f'inline; filename="{filename}"'
                },
                ExpiresIn=86400  # 24 hours in seconds (correct for S3)
            )
            
            # Download URL (attachment)
            download_url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': filename,
                    'ResponseContentDisposition': f'attachment; filename="{filename}"'
                },
                ExpiresIn=86400  # 24 hours in seconds (correct for S3)
            )
            
            return preview_url, download_url
        except Exception as e:
            print(f"❌ Error generating S3 URLs for {filename}: {e}")
            return None, None

# Global instance
s3_service = S3Service()