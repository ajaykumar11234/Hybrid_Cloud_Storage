import clamd
import io
import logging

logger = logging.getLogger(__name__)

def scan_file(file_bytes: bytes):
    """Scan file bytes using ClamAV and return (is_clean, virus_name)"""
    try:
        cd = clamd.ClamdNetworkSocket(host='localhost', port=3310)
        result = cd.instream(io.BytesIO(file_bytes))
        status, virus_name = result['stream']

        if status == 'FOUND':
            logger.warning(f"🚨 Virus detected: {virus_name}")
            return False, virus_name
        logger.info("✅ File is clean")
        return True, None

    except Exception as e:
        logger.error(f"❌ ClamAV scan error: {e}", exc_info=True)
        # Fail-safe: if scanner fails, block upload
        return False, "ScanError"
