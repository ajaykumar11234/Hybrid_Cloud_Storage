from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from config import Config
from models.file_model import FileMetadata
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class MongoDBService:
    """MongoDB service for file metadata operations"""
    
    def __init__(self):
        try:
            self.client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
            self.db = self.client[Config.DB_NAME]
            self.files_collection: Collection = self.db[Config.COLLECTION_NAME]
            
            # Test connection
            self.client.admin.command('ping')
            print("✅ MongoDB connection established successfully")
            
            # Create indexes for better performance
            self.files_collection.create_index([("filename", 1)], unique=True)
            self.files_collection.create_index([("minio_uploaded_at", -1)])
            self.files_collection.create_index([("ai_analysis_status", 1)])
            self.files_collection.create_index([("status", 1)])
            print("✅ MongoDB indexes created")
            
        except PyMongoError as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            print(f"❌ MongoDB connection failed: {e}")
            raise
    
    def insert_file(self, file_metadata: FileMetadata) -> str:
        """Insert file metadata into MongoDB"""
        try:
            result = self.files_collection.insert_one(file_metadata.to_dict())
            logger.info(f"✅ File metadata inserted for: {file_metadata.filename}")
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.error(f"❌ Error inserting file metadata for {file_metadata.filename}: {e}")
            raise
    
    def get_file(self, filename: str) -> Optional[Dict]:
        """Get file metadata by filename as dictionary"""
        try:
            data = self.files_collection.find_one({"filename": filename})
            if data and '_id' in data:
                data['_id'] = str(data['_id'])  # Convert ObjectId to string
            return data
        except PyMongoError as e:
            logger.error(f"❌ Error getting file {filename}: {e}")
            return None
    
    def get_file_by_filename(self, filename: str) -> Optional[Dict]:
        """Alias for get_file method for compatibility"""
        return self.get_file(filename)
    
    def get_all_files(self) -> List[Dict]:
        """Get all file metadata as list of dictionaries"""
        try:
            cursor = self.files_collection.find({}).sort("minio_uploaded_at", DESCENDING)
            files = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                files.append(doc)
            logger.info(f"✅ Retrieved {len(files)} files from database")
            return files
        except PyMongoError as e:
            logger.error(f"❌ Error getting all files: {e}")
            return []
    
    def get_files_by_status(self, status: str) -> List[Dict]:
        """Get files by upload status"""
        try:
            cursor = self.files_collection.find({"status": status})
            files = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                files.append(doc)
            return files
        except PyMongoError as e:
            logger.error(f"❌ Error getting files by status {status}: {e}")
            return []
    
    def update_file(self, filename: str, update_data: dict) -> bool:
        """Update file metadata"""
        try:
            # Add timestamp for the update
            if update_data and not any(key.startswith('$') for key in update_data.keys()):
                update_data['last_updated'] = datetime.utcnow().isoformat()
            
            result = self.files_collection.update_one(
                {"filename": filename},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ File metadata updated for: {filename}")
                return True
            else:
                logger.warning(f"⚠️ No changes made for file: {filename}")
                return False
                
        except PyMongoError as e:
            logger.error(f"❌ Error updating file {filename}: {e}")
            return False
    
    def delete_file(self, filename: str) -> bool:
        """Delete file metadata"""
        try:
            result = self.files_collection.delete_one({"filename": filename})
            if result.deleted_count > 0:
                logger.info(f"✅ File metadata deleted for: {filename}")
                return True
            else:
                logger.warning(f"⚠️ File not found for deletion: {filename}")
                return False
        except PyMongoError as e:
            logger.error(f"❌ Error deleting file {filename}: {e}")
            return False
    
    def get_pending_analysis_files(self) -> List[Dict]:
        """Get files pending AI analysis as list of dictionaries"""
        try:
            cursor = self.files_collection.find({
                "ai_analysis_status": "pending"
            })
            files = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                files.append(doc)
            return files
        except PyMongoError as e:
            logger.error(f"❌ Error getting pending analysis files: {e}")
            return []
    
    def get_recent_files(self, limit: int = 50) -> List[Dict]:
        """Get most recently uploaded files"""
        try:
            cursor = self.files_collection.find({}).sort("minio_uploaded_at", DESCENDING).limit(limit)
            files = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                files.append(doc)
            return files
        except PyMongoError as e:
            logger.error(f"❌ Error getting recent files: {e}")
            return []
    
    def get_files_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get files uploaded within a date range"""
        try:
            cursor = self.files_collection.find({
                "minio_uploaded_at": {
                    "$gte": start_date.isoformat(),
                    "$lte": end_date.isoformat()
                }
            }).sort("minio_uploaded_at", DESCENDING)
            
            files = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                files.append(doc)
            return files
        except PyMongoError as e:
            logger.error(f"❌ Error getting files by date range: {e}")
            return []
    
    def get_analyzed_files(self) -> List[Dict]:
        """Get files that have AI analysis"""
        try:
            cursor = self.files_collection.find({
                "ai_analysis_status": "completed",
                "ai_analysis": {"$exists": True, "$ne": None}
            }).sort("minio_uploaded_at", DESCENDING)
            
            files = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                files.append(doc)
            return files
        except PyMongoError as e:
            logger.error(f"❌ Error getting analyzed files: {e}")
            return []
    
    def get_files_by_extension(self, extension: str) -> List[Dict]:
        """Get files by file extension"""
        try:
            cursor = self.files_collection.find({
                "filename": {"$regex": f"\\.{extension}$", "$options": "i"}
            }).sort("minio_uploaded_at", DESCENDING)
            
            files = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                files.append(doc)
            return files
        except PyMongoError as e:
            logger.error(f"❌ Error getting files by extension {extension}: {e}")
            return []
    
    def search_files(self, search_term: str) -> List[Dict]:
        """Search files by filename or AI analysis content"""
        try:
            cursor = self.files_collection.find({
                "$or": [
                    {"filename": {"$regex": search_term, "$options": "i"}},
                    {"ai_analysis.summary": {"$regex": search_term, "$options": "i"}},
                    {"ai_analysis.caption": {"$regex": search_term, "$options": "i"}},
                    {"ai_analysis.keywords": {"$in": [search_term]}}
                ]
            }).sort("minio_uploaded_at", DESCENDING)
            
            files = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                files.append(doc)
            return files
        except PyMongoError as e:
            logger.error(f"❌ Error searching files with term '{search_term}': {e}")
            return []
    
    def get_storage_stats(self) -> Dict:
        """Get comprehensive storage statistics"""
        try:
            all_files = self.get_all_files()
            
            total_files = len(all_files)
            total_size = sum(f.get('size', 0) for f in all_files)
            avg_file_size = total_size / total_files if total_files > 0 else 0
            
            files_analyzed = sum(1 for f in all_files if f.get('ai_analysis_status') == 'completed')
            
            status_distribution = {}
            for file in all_files:
                status = file.get('status', 'unknown')
                status_distribution[status] = status_distribution.get(status, 0) + 1
            
            return {
                "total_files": total_files,
                "total_size": total_size,
                "avg_file_size": avg_file_size,
                "status_distribution": status_distribution,
                "files_analyzed": files_analyzed
            }
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {
                "total_files": 0,
                "total_size": 0,
                "avg_file_size": 0,
                "status_distribution": {},
                "files_analyzed": 0
            }

    def get_upload_trends(self, days: int = 30) -> List[Dict]:
        """Get upload trends for the last N days"""
        try:
            all_files = self.get_all_files()
            
            uploads_by_date = {}
            for file in all_files:
                upload_date_str = file.get('minio_uploaded_at') or file.get('uploaded_at')
                if upload_date_str:
                    try:
                        if 'T' in upload_date_str:
                            upload_date = datetime.fromisoformat(upload_date_str.replace('Z', '+00:00'))
                        else:
                            upload_date = datetime.strptime(upload_date_str, '%Y-%m-%d %H:%M:%S')
                        
                        date_key = upload_date.strftime('%Y-%m-%d')
                        uploads_by_date[date_key] = uploads_by_date.get(date_key, 0) + 1
                    except (ValueError, AttributeError):
                        continue
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            daily_uploads = []
            
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                daily_uploads.append({
                    "_id": date_str,
                    "count": uploads_by_date.get(date_str, 0)
                })
                current_date += timedelta(days=1)
            
            return daily_uploads
        except Exception as e:
            logger.error(f"Error getting upload trends: {e}")
            return []

    def get_top_keywords(self, limit: int = 10) -> List[Dict]:
        """Get top keywords from AI analysis"""
        try:
            all_files = self.get_all_files()
            
            keyword_counts = {}
            for file in all_files:
                keywords = file.get('ai_analysis', {}).get('keywords', [])
                for keyword in keywords:
                    if keyword:
                        keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
            
            top_tags = [{"_id": k, "count": v} for k, v in keyword_counts.items()]
            top_tags.sort(key=lambda x: x["count"], reverse=True)
            top_tags = top_tags[:limit]
            
            return top_tags
        except Exception as e:
            logger.error(f"Error getting top keywords: {e}")
            return []
        
    def search_files_advanced(self, search_query=None, limit=100, skip=0):
        """Advanced search with query and pagination"""
        try:
            if search_query is None:
                search_query = {}
            
            cursor = self.files_collection.find(search_query).sort("minio_uploaded_at", -1).skip(skip).limit(limit)
            files = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                files.append(doc)
            return files
        except PyMongoError as e:
            logger.error(f"Advanced search error: {e}")
            return []

def get_search_count(self, search_query=None):
    """Get count of search results"""
    try:
        if search_query is None:
            search_query = {}
        return self.files_collection.count_documents(search_query)
    except PyMongoError as e:
        logger.error(f"Search count error: {e}")
        return 0
    
def close_connection(self):
        """Close MongoDB connection"""
        try:
            self.client.close()
            logger.info("✅ MongoDB connection closed")
        except PyMongoError as e:
            logger.error(f"❌ Error closing MongoDB connection: {e}")
def search_simple(self, query: str = "") -> List[Dict]:
    """Simple search in filename and keywords"""
    try:
        if not query:
            return self.get_all_files()
        
        all_files = self.get_all_files()
        results = []
        
        for file in all_files:
            # Search in filename
            filename = file.get('filename', '').lower()
            if query.lower() in filename:
                results.append(file)
                continue
            
            # Search in keywords
            keywords = file.get('ai_analysis', {}).get('keywords', [])
            if any(query.lower() in str(kw).lower() for kw in keywords):
                results.append(file)
        
        return results
    except Exception as e:
        logger.error(f"Simple search error: {e}")
        return []

def filter_files(self, filename_filter: str = "", keyword_filter: str = "") -> List[Dict]:
    """Filter files by filename and/or keywords"""
    try:
        all_files = self.get_all_files()
        filtered_files = []
        
        for file in all_files:
            # Apply filename filter
            if filename_filter:
                filename = file.get('filename', '').lower()
                if filename_filter.lower() not in filename:
                    continue
            
            # Apply keyword filter
            if keyword_filter:
                keywords = file.get('ai_analysis', {}).get('keywords', [])
                if not any(keyword_filter.lower() in str(kw).lower() for kw in keywords):
                    continue
            
            filtered_files.append(file)
        
        return filtered_files
    except Exception as e:
        logger.error(f"File filtering error: {e}")
        return []

# Global instance
mongodb_service = MongoDBService()
