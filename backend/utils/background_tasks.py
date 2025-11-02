import time
import threading
from datetime import datetime
from services.service_manager import service_manager
import logging

logger = logging.getLogger(__name__)

def start_background_threads():
    """Start all background threads"""
    # Start S3 sync thread if S3 is available
    if service_manager.s3.is_available():
        threading.Thread(target=sync_to_s3_worker, daemon=True).start()
        print("🚀 S3 sync thread started")
    else:
        print("ℹ️ S3 sync disabled - no AWS credentials")
    
    # Start AI analysis worker if AI is available
    if service_manager.ai and service_manager.ai.is_available():
        threading.Thread(target=ai_analysis_worker, daemon=True).start()
        print("🧠 AI analysis worker started")
    else:
        print("ℹ️ AI analysis disabled - no AI API key")

def sync_to_s3_worker():
    """Background worker to sync MinIO files to S3"""
    while True:
        try:
            # Get files that are in MinIO but not yet in S3
            files = service_manager.mongodb.get_all_files()
            
            for file_data in files:
                if file_data.get("status") == "minio" and service_manager.s3.is_available():
                    filename = file_data["filename"]
                    print(f"🔄 Syncing {filename} to S3...")
                    
                    # Get file from MinIO
                    file_bytes = service_manager.minio.get_file(filename)
                    if not file_bytes:
                        continue
                    
                    # Upload to S3
                    if service_manager.s3.upload_file(filename, file_bytes, file_data.get("content_type")):
                        # Generate S3 URLs
                        s3_preview_url, s3_download_url = service_manager.s3.generate_presigned_urls(filename)
                        
                        # Update file metadata
                        update_data = {
                            "status": "uploaded-to-s3",
                            "s3_preview_url": s3_preview_url,
                            "s3_download_url": s3_download_url,
                            "s3_synced_at": datetime.utcnow().isoformat()
                        }
                        service_manager.mongodb.update_file(filename, update_data)
                        print(f"✅ Synced {filename} → AWS S3")
                    
        except Exception as e:
            logger.error(f"Error in S3 sync worker: {e}")
        
        time.sleep(30)  # Check every 30 seconds

def ai_analysis_worker():
    """Background worker for AI analysis of uploaded files"""
    while True:
        try:
            # Get files pending analysis
            pending_files = service_manager.mongodb.get_pending_analysis_files()
            
            for file_data in pending_files:
                filename = file_data["filename"]
                print(f"🧠 Analyzing {filename} with AI...")
                
                try:
                    # Get file from MinIO
                    file_bytes = service_manager.minio.get_file(filename)
                    if not file_bytes:
                        continue
                    
                    # Extract text
                    text = service_manager.file_processor.extract_text(filename, file_bytes)
                    
                    if text and len(text) > 10:
                        # Perform AI analysis
                        analysis_result = service_manager.ai.analyze_text(text, filename)
                        
                        if analysis_result:
                            # Update file metadata
                            update_data = {
                                "ai_analysis": analysis_result,
                                "ai_analysis_status": "completed"
                            }
                            service_manager.mongodb.update_file(filename, update_data)
                            print(f"✅ AI analysis completed for {filename}")
                        else:
                            update_data = {"ai_analysis_status": "failed"}
                            service_manager.mongodb.update_file(filename, update_data)
                            print(f"⚠️ AI analysis failed for {filename}")
                    else:
                        update_data = {"ai_analysis_status": "failed"}
                        service_manager.mongodb.update_file(filename, update_data)
                        print(f"⚠️ Not enough text for AI analysis: {filename}")
                        
                except Exception as e:
                    print(f"❌ Error analyzing {filename}: {e}")
                    update_data = {"ai_analysis_status": "failed"}
                    service_manager.mongodb.update_file(filename, update_data)
                    
        except Exception as e:
            logger.error(f"Error in AI analysis worker: {e}")
        
        time.sleep(60)  # Check every minute