import time
import threading
from datetime import datetime
from services.service_manager import service_manager
import clamd
import io
import logging

logger = logging.getLogger(__name__)

# ==========================================================
# THREAD STARTER
# ==========================================================
def start_background_threads():
    """Start background workers for S3 sync & AI analysis."""
    try:
        # 🚀 Start S3 sync worker
        if service_manager.s3 and service_manager.s3.is_available():
            threading.Thread(
                target=sync_to_s3_worker,
                daemon=True,
                name="s3-sync-worker"
            ).start()
            logger.info("🚀 S3 sync thread started")
            print("🚀 [THREAD] S3 sync worker started")
        else:
            logger.info("ℹ️ S3 sync disabled (no AWS credentials)")
            print("ℹ️ [THREAD] S3 sync disabled (no AWS credentials)")

        # 🧠 Start AI analysis worker
        if service_manager.ai and service_manager.ai.is_available():
            threading.Thread(
                target=ai_analysis_worker,
                daemon=True,
                name="ai-analysis-worker"
            ).start()
            logger.info("🧠 AI analysis worker started")
            print("🧠 [THREAD] AI analysis worker started")
        else:
            logger.info("ℹ️ AI analysis disabled (no API key)")
            print("ℹ️ [THREAD] AI analysis disabled (no API key)")

    except Exception as e:
        logger.error(f"❌ Failed to start background threads: {e}", exc_info=True)
        print(f"❌ [THREAD] Failed to start background threads: {e}")


# ==========================================================
# S3 SYNC WORKER (WITH VIRUS SCANNING)
# ==========================================================
def sync_to_s3_worker():
    """Background worker that syncs clean MinIO files to AWS S3."""
    logger.info("🔄 S3 sync worker started")
    print("🔄 [S3 Worker] Started syncing process...")

    # Try connecting to ClamAV
    try:
        cd = clamd.ClamdNetworkSocket(host="localhost", port=3310)
        cd.ping()
        logger.info("🛡️ Connected to ClamAV successfully.")
        print("🛡️ [S3 Worker] Connected to ClamAV successfully at localhost:3310")
    except Exception as e:
        logger.error(f"❌ Could not connect to ClamAV: {e}")
        print(f"❌ [S3 Worker] Could not connect to ClamAV: {e}")
        cd = None

    while True:
        try:
            # Fetch all files
            files = service_manager.mongodb.get_all_files()
            if not files:
                print("📭 [S3 Worker] No files found. Sleeping 30s...")
                time.sleep(30)
                continue

            # Filter unsynced files
            files_to_sync = [
                f for f in files
                if f.get("status") not in ("uploaded-to-s3", "infected", "sync-failed")
                and service_manager.s3.is_available()
            ]

            print(f"📂 [S3 Worker] Found {len(files_to_sync)} files to check for sync...")

            for file_data in files_to_sync:
                filename = file_data.get("filename")
                user_id = file_data.get("user_id")

                if not filename or not user_id:
                    continue

                print(f"🔍 [S3 Worker] Checking {filename} (User: {user_id})...")

                try:
                    # Step 1: Retrieve file bytes from MinIO
                    file_bytes = service_manager.minio.get_file(user_id, filename)
                    if not file_bytes:
                        print(f"⚠️ [S3 Worker] File missing in MinIO: {user_id}/{filename}")
                        service_manager.mongodb.update_file(
                            filename,
                            {"status": "sync-failed", "sync_error": "File missing in MinIO"},
                            user_id=user_id
                        )
                        continue

                    # Step 2: Run ClamAV scan
                    if cd:
                        scan_result = cd.instream(io.BytesIO(file_bytes))
                        result = list(scan_result.values())[0]
                        if result[0] == "FOUND":
                            virus_name = result[1]
                            print(f"🦠 [S3 Worker] VIRUS DETECTED in {filename}: {virus_name}")
                            service_manager.mongodb.update_file(
                                filename,
                                {
                                    "status": "infected",
                                    "scan_status": "infected",
                                    "virus_name": virus_name,
                                    "scanned_at": datetime.utcnow().isoformat()
                                },
                                user_id=user_id
                            )
                            continue  # skip upload
                        else:
                            print(f"✅ [S3 Worker] {filename} is CLEAN.")
                    else:
                        print("⚠️ [S3 Worker] ClamAV unavailable. Skipping scan.")

                    # Step 3: Upload clean file to S3
                    print(f"☁️ [S3 Worker] Uploading {filename} to AWS S3...")
                    uploaded = service_manager.s3.upload_file(
                        user_id,
                        filename,
                        file_bytes,
                        file_data.get("content_type")
                    )

                    if uploaded:
                        s3_preview_url, s3_download_url = service_manager.s3.generate_presigned_urls(user_id, filename)
                        update_data = {
                            "status": "uploaded-to-s3",
                            "s3_preview_url": s3_preview_url,
                            "s3_download_url": s3_download_url,
                            "s3_synced_at": datetime.utcnow().isoformat(),
                        }
                        service_manager.mongodb.update_file(filename, update_data, user_id=user_id)
                        print(f"✅ [S3 Worker] Synced {filename} → AWS S3 successfully!")
                    else:
                        print(f"❌ [S3 Worker] Failed to upload {filename} to S3.")
                        service_manager.mongodb.update_file(
                            filename,
                            {"status": "sync-failed", "sync_error": "S3 upload failed"},
                            user_id=user_id
                        )

                except Exception as e:
                    logger.error(f"❌ Error syncing {user_id}/{filename}: {e}", exc_info=True)
                    print(f"❌ [S3 Worker] Error syncing {user_id}/{filename}: {e}")
                    service_manager.mongodb.update_file(
                        filename,
                        {"status": "sync-failed", "sync_error": str(e)},
                        user_id=user_id
                    )

        except Exception as e:
            logger.error(f"❌ Error in S3 sync worker loop: {e}", exc_info=True)
            print(f"❌ [S3 Worker] Error in sync loop: {e}")

        print("😴 [S3 Worker] Sleeping 30 seconds before next scan cycle...\n")
        time.sleep(30)


# ==========================================================
# AI ANALYSIS WORKER
# ==========================================================
def ai_analysis_worker():
    """Background worker for performing AI analysis on pending files."""
    logger.info("🧠 AI analysis worker started")
    print("🧠 [AI Worker] Started AI analysis worker...")

    while True:
        try:
            files = service_manager.mongodb.get_all_files()
            if not files:
                print("📭 [AI Worker] No files found. Sleeping 60s...")
                time.sleep(60)
                continue

            pending_files = [
                f for f in files
                if f.get("ai_analysis_status") == "pending"
            ]

            print(f"📄 [AI Worker] Found {len(pending_files)} files for AI analysis...")

            if not pending_files:
                time.sleep(60)
                continue

            for file_data in pending_files:
                filename = file_data.get("filename")
                user_id = file_data.get("user_id")

                if not filename or not user_id:
                    continue

                print(f"🧠 [AI Worker] Analyzing file: {filename} (User: {user_id})")

                try:
                    # Mark as processing
                    service_manager.mongodb.update_file(
                        filename, {"ai_analysis_status": "processing"}, user_id=user_id
                    )

                    # Get file bytes
                    file_bytes = service_manager.minio.get_file(user_id, filename)
                    if not file_bytes:
                        print(f"⚠️ [AI Worker] Missing file in MinIO: {filename}")
                        service_manager.mongodb.update_file(
                            filename,
                            {"ai_analysis_status": "failed", "ai_error": "File missing"},
                            user_id=user_id
                        )
                        continue

                    # Extract text for AI
                    text = service_manager.file_processor.extract_text(filename, file_bytes)
                    if not text or len(text.strip()) < 20:
                        print(f"⚠️ [AI Worker] Not enough text to analyze: {filename}")
                        service_manager.mongodb.update_file(
                            filename,
                            {"ai_analysis_status": "failed", "ai_error": "Insufficient content"},
                            user_id=user_id
                        )
                        continue

                    # Perform AI analysis
                    analysis_result = service_manager.ai.analyze_text(text, filename)
                    if analysis_result:
                        print(f"✅ [AI Worker] Analysis complete for {filename}")
                        update_data = {
                            "ai_analysis": analysis_result,
                            "ai_analysis_status": "completed",
                            "ai_analysis_completed_at": datetime.utcnow().isoformat(),
                        }
                        service_manager.mongodb.update_file(filename, update_data, user_id=user_id)
                    else:
                        print(f"⚠️ [AI Worker] AI returned no result for {filename}")
                        service_manager.mongodb.update_file(
                            filename,
                            {"ai_analysis_status": "failed", "ai_error": "Empty result"},
                            user_id=user_id
                        )

                except Exception as e:
                    print(f"❌ [AI Worker] Error analyzing {filename}: {e}")
                    logger.error(f"❌ AI error for {filename}: {e}", exc_info=True)
                    service_manager.mongodb.update_file(
                        filename,
                        {"ai_analysis_status": "failed", "ai_error": str(e)},
                        user_id=user_id
                    )

        except Exception as e:
            print(f"❌ [AI Worker] Loop error: {e}")
            logger.error(f"❌ AI worker loop error: {e}", exc_info=True)

        print("😴 [AI Worker] Sleeping 60 seconds before next cycle...\n")
        time.sleep(60)
