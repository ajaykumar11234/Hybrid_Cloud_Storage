import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for environment variables"""
    
    # MinIO Configuration
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "uploads")
    
    # AWS S3 Configuration
    AWS_BUCKET = os.getenv("AWS_BUCKET")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
    
    # MongoDB Configuration
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "mydb")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "files")
    
    # Groq AI Configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # Debug configuration
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

def debug_config():
    """Print debug information about configuration"""
    print("🔍 DEBUG: Checking environment variables...")
    print(f"MINIO_ENDPOINT: {Config.MINIO_ENDPOINT}")
    print(f"GROQ_API_KEY present: {bool(Config.GROQ_API_KEY)}")
    print(f"GROQ_API_KEY first 10 chars: {Config.GROQ_API_KEY[:10] if Config.GROQ_API_KEY else 'NOT FOUND'}")
    print(f"Current directory: {os.getcwd()}")
    
    if os.path.exists('.env'):
        print("✅ .env file found")
    else:
        print("❌ .env file NOT found")