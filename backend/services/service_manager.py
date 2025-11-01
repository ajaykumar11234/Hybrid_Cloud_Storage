from services.minio_service import MinioService
from services.s3_service import S3Service
from services.mongodb_service import MongoDBService
from services.file_processor import FileProcessor

# Try to import Groq first, fall back to OpenAI
try:
    from services.groq_service import GroqService
    groq_available = True
except ImportError:
    try:
        from services.openai_service import OpenAIService
        groq_available = False
    except ImportError:
        groq_available = None

class ServiceManager:
    """Manages all service instances"""
    
    def __init__(self):
        self.minio = MinioService()
        self.s3 = S3Service()
        self.mongodb = MongoDBService()
        self.file_processor = FileProcessor()
        
        # Initialize AI service (Groq preferred, fallback to OpenAI)
        if groq_available is True:
            self.ai = GroqService()
            print("🤖 Using Groq for AI analysis")
        elif groq_available is False:
            self.ai = OpenAIService()
            print("🤖 Using OpenAI for AI analysis")
        else:
            self.ai = None
            print("⚠️ No AI service available")

# Create global service manager
service_manager = ServiceManager()