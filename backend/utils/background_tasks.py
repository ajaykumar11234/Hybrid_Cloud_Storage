import time
import threading
from datetime import datetime
from services.service_manager import service_manager
import logging

logger = logging.getLogger(__name__)

def start_background_threads():
    """Start background workers for S3 sync & AI analysis."""
    try:
        if service_manager.s3 and service_manager.s3.is_available():
            threading.Thread(target=sync_to_s3_worker, daemon=True, name="s3-sync-worker").start()
            logger.info("🚀 S3 sync thread started")
        else:
            logger.info("ℹ️ S3 sync disabled (no AWS credentials)")

        if service_manager.ai and service_manager.ai.is_available():
            threading.Thread(target=ai_analysis_worker, daemon=True, name="ai-analysis-worker").start()
            logger.info("🧠 AI analysis worker started")
        else:
            logger.info("ℹ️ AI analysis disabled (no API key)")
    except Exception as e:
        logger.error(f"❌ Failed to start background threads: {e}")

# ==========================================================
# S3 SYNC WORKER
# ==========================================================
def sync_to_s3_worker():
    """Background worker that syncs MinIO files to S3."""
    logger.info("🔄 S3 sync worker started")
    
    while True:
        try:
            # Get all files and filter locally for those that need syncing
            files = service_manager.mongodb.get_all_files()
            if not files:
                time.sleep(30)
                continue

            files_to_sync = [
                file_data for file_data in files 
                if file_data.get("status") != "uploaded-to-s3" 
                and service_manager.s3.is_available()
            ]

            for file_data in files_to_sync:
                filename = file_data.get("filename")
                user_id = file_data.get("user_id")
                
                if not filename or not user_id:
                    continue

                logger.info(f"🔄 Syncing {filename} (user: {user_id}) to S3...")
                
                try:
                    # Get file bytes from MinIO
                    file_bytes = service_manager.minio.get_file(user_id, filename)
                    if not file_bytes:
                        logger.warning(f"⚠️ Missing file in MinIO: {user_id}/{filename}")
                        # Mark as failed to avoid repeated attempts
                        service_manager.mongodb.update_file(
                            filename, 
                            {"status": "sync-failed", "sync_error": "File missing in MinIO"}, 
                            user_id=user_id
                        )
                        continue

                    # Upload to S3
                    uploaded = service_manager.s3.upload_file(user_id, filename, file_bytes, file_data.get("content_type"))
                    if uploaded:
                        # Generate presigned URLs
                        s3_preview_url, s3_download_url = service_manager.s3.generate_presigned_urls(user_id, filename)
                        update_data = {
                            "status": "uploaded-to-s3",
                            "s3_preview_url": s3_preview_url,
                            "s3_download_url": s3_download_url,
                            "s3_synced_at": datetime.utcnow().isoformat()
                        }
                        service_manager.mongodb.update_file(filename, update_data, user_id=user_id)
                        logger.info(f"✅ Synced {filename} → AWS S3 (user: {user_id})")
                    else:
                        logger.error(f"❌ Failed to upload {filename} to S3")
                        service_manager.mongodb.update_file(
                            filename, 
                            {"status": "sync-failed", "sync_error": "S3 upload failed"}, 
                            user_id=user_id
                        )

                except Exception as e:
                    logger.error(f"❌ Error syncing {user_id}/{filename}: {e}")
                    try:
                        service_manager.mongodb.update_file(
                            filename, 
                            {"status": "sync-failed", "sync_error": str(e)}, 
                            user_id=user_id
                        )
                    except Exception as update_error:
                        logger.error(f"❌ Failed to update sync status: {update_error}")

        except Exception as e:
            logger.error(f"❌ Error in S3 sync worker: {e}", exc_info=True)

        time.sleep(30)

# ==========================================================
# AI ANALYSIS WORKER
# ==========================================================
def ai_analysis_worker():
    """Background worker for performing AI analysis on pending files."""
    logger.info("🧠 AI analysis worker started")
    
    while True:
        try:
            # Get all files and filter for pending AI analysis
            files = service_manager.mongodb.get_all_files()
            if not files:
                time.sleep(60)
                continue

            pending_files = [
                file_data for file_data in files 
                if file_data.get("ai_analysis_status") == "pending"
            ]

            if not pending_files:
                time.sleep(60)
                continue

            for file_data in pending_files:
                filename = file_data.get("filename")
                user_id = file_data.get("user_id")
                
                if not filename or not user_id:
                    continue

                logger.info(f"🧠 Analyzing {filename} (user: {user_id}) with AI...")
                
                try:
                    # Mark as processing to prevent duplicate processing
                    service_manager.mongodb.update_file(
                        filename, 
                        {"ai_analysis_status": "processing"}, 
                        user_id=user_id
                    )

                    # Get file bytes from MinIO
                    file_bytes = service_manager.minio.get_file(user_id, filename)
                    if not file_bytes:
                        logger.warning(f"⚠️ File missing in MinIO for AI: {user_id}/{filename}")
                        service_manager.mongodb.update_file(
                            filename, 
                            {"ai_analysis_status": "failed", "ai_error": "File missing in MinIO"}, 
                            user_id=user_id
                        )
                        continue

                    # Extract text
                    text = service_manager.file_processor.extract_text(filename, file_bytes)
                    if not text or len(text.strip()) < 20:
                        logger.info(f"⚠️ Not enough text to analyze: {user_id}/{filename}")
                        service_manager.mongodb.update_file(
                            filename, 
                            {"ai_analysis_status": "failed", "ai_error": "Insufficient text content"}, 
                            user_id=user_id
                        )
                        continue

                    # Run analysis
                    analysis_result = service_manager.ai.analyze_text(text, filename)
                    if analysis_result:
                        update_data = {
                            "ai_analysis": analysis_result,
                            "ai_analysis_status": "completed",
                            "ai_analysis_completed_at": datetime.utcnow().isoformat()
                        }
                        service_manager.mongodb.update_file(filename, update_data, user_id=user_id)
                        logger.info(f"✅ AI analysis completed for {user_id}/{filename}")
                    else:
                        logger.warning(f"⚠️ AI returned no result for {user_id}/{filename}")
                        service_manager.mongodb.update_file(
                            filename, 
                            {"ai_analysis_status": "failed", "ai_error": "AI service returned no result"}, 
                            user_id=user_id
                        )

                except Exception as e:
                    logger.error(f"❌ Error analyzing {user_id}/{filename}: {e}", exc_info=True)
                    try:
                        service_manager.mongodb.update_file(
                            filename, 
                            {"ai_analysis_status": "failed", "ai_error": str(e)}, 
                            user_id=user_id
                        )
                    except Exception as update_error:
                        logger.error(f"❌ Failed to update AI analysis status: {update_error}")

        except Exception as e:
            logger.error(f"❌ Error in AI analysis worker: {e}", exc_info=True)

        time.sleep(60)