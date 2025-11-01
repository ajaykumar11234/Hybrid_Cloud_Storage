from pymongo import MongoClient
from pymongo.collection import Collection
from config import Config
from models.file_model import FileMetadata

class MongoDBService:
    """MongoDB service for file metadata operations"""
    
    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI)
        self.db = self.client[Config.DB_NAME]
        self.files_collection: Collection = self.db[Config.COLLECTION_NAME]
        print("✅ MongoDB connection established")
    
    def insert_file(self, file_metadata: FileMetadata) -> str:
        """Insert file metadata into MongoDB"""
        result = self.files_collection.insert_one(file_metadata.to_dict())
        return str(result.inserted_id)
    
    def get_file(self, filename: str) -> dict:
        """Get file metadata by filename as dictionary"""
        data = self.files_collection.find_one({"filename": filename})
        if data:
            data.pop('_id', None)  # Remove MongoDB _id
            return data
        return None
    
    def get_all_files(self) -> list:
        """Get all file metadata as list of dictionaries"""
        cursor = self.files_collection.find({}, {"_id": 0})
        return list(cursor)
    
    def update_file(self, filename: str, update_data: dict) -> bool:
        """Update file metadata"""
        result = self.files_collection.update_one(
            {"filename": filename},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    def delete_file(self, filename: str) -> bool:
        """Delete file metadata"""
        result = self.files_collection.delete_one({"filename": filename})
        return result.deleted_count > 0
    
    def get_pending_analysis_files(self) -> list:
        """Get files pending AI analysis as list of dictionaries"""
        cursor = self.files_collection.find({
            "ai_analysis_status": "pending"
        }, {"_id": 0})
        return list(cursor)

# Global instance
mongodb_service = MongoDBService()