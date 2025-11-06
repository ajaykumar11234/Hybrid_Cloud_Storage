import logging
from services.minio_service import MinioService
from services.s3_service import S3Service
from services.mongodb_service import MongoDBService

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# OPTIONAL IMPORTS
# ------------------------------------------------------------
try:
    from services.file_processor import FileProcessor
except ImportError:
    FileProcessor = None
    logger.warning("⚠️ FileProcessor module not found — OCR/analysis may be limited.")

# AI: Prefer Groq, fallback to OpenAI
try:
    from services.groq_service import GroqService
    AIService = GroqService
    ai_provider = "Groq"
except ImportError:
    try:
        from services.openai_service import OpenAIService
        AIService = OpenAIService
        ai_provider = "OpenAI"
    except ImportError:
        AIService = None
        ai_provider = None
        logger.warning("⚠️ No AI service available (Groq/OpenAI missing).")

# ------------------------------------------------------------
# SERVICE MANAGER CLASS
# ------------------------------------------------------------
class ServiceManager:
    """Centralized manager for all backend services."""

    def __init__(self):
        # Predeclare attributes
        self.mongodb = None
        self.minio = None
        self.s3 = None
        self.file_processor = None
        self.ai = None

        self.initialize_services()

    # --------------------------------------------------
    # INITIALIZATION
    # --------------------------------------------------
    def initialize_services(self):
        """Initialize all configured services safely."""
        logger.info("🚀 Initializing backend services...")

        # MongoDB
        try:
            self.mongodb = MongoDBService()
            if self.mongodb and getattr(self.mongodb, "client", None):
                logger.info("✅ MongoDB service initialized successfully.")
            else:
                logger.warning("⚠️ MongoDB client unavailable after initialization.")
        except Exception as e:
            self.mongodb = None
            logger.error(f"❌ MongoDB initialization failed: {e}", exc_info=True)

        # MinIO
        try:
            self.minio = MinioService()
            if self.minio and getattr(self.minio, "client", None):
                logger.info("✅ MinIO service initialized successfully.")
            else:
                logger.warning("⚠️ MinIO client unavailable after initialization.")
        except Exception as e:
            self.minio = None
            logger.error(f"❌ MinIO initialization failed: {e}", exc_info=True)

        # AWS S3
        try:
            self.s3 = S3Service()
            if self.s3 and getattr(self.s3, "client", None):
                logger.info("✅ S3 service initialized successfully.")
            else:
                logger.warning("⚠️ S3 client unavailable after initialization.")
        except Exception as e:
            self.s3 = None
            logger.error(f"❌ S3 initialization failed: {e}", exc_info=True)

        # File Processor
        if FileProcessor:
            try:
                self.file_processor = FileProcessor()
                logger.info("✅ File processor initialized successfully.")
            except Exception as e:
                self.file_processor = None
                logger.error(f"❌ File processor initialization failed: {e}", exc_info=True)
        else:
            logger.info("ℹ️ File processor not configured or unavailable.")

        # AI Service (Groq or OpenAI)
        if AIService:
            try:
                self.ai = AIService()
                if getattr(self.ai, "is_available", lambda: False)():
                    logger.info(f"🤖 {ai_provider} AI service initialized successfully.")
                else:
                    logger.warning(f"⚠️ {ai_provider} AI service not available (missing API key?).")
            except Exception as e:
                self.ai = None
                logger.error(f"❌ Failed to initialize {ai_provider} AI service: {e}", exc_info=True)
        else:
            logger.warning("⚠️ No AI service available (Groq/OpenAI not installed).")

        logger.info("✅ Service initialization process complete.")

    # --------------------------------------------------
    # DIAGNOSTICS
    # --------------------------------------------------
    def get_service_status(self) -> dict:
        """Return service availability states for diagnostics."""
        return {
            "mongodb": bool(self.mongodb and getattr(self.mongodb, "client", None)),
            "minio": bool(self.minio and getattr(self.minio, "client", None)),
            "s3": bool(self.s3 and getattr(self.s3, "client", None)),
            "file_processor": self.file_processor is not None,
            "ai_service": ai_provider if (self.ai and getattr(self.ai, "is_available", lambda: False)()) else None,
        }

    # --------------------------------------------------
    # RELOAD SERVICES
    # --------------------------------------------------
    def reload_services(self):
        """Reinitialize all services without restarting the app."""
        logger.info("🔁 Reloading all backend services...")
        self.initialize_services()
        logger.info("✅ All backend services reloaded successfully.")


# ------------------------------------------------------------
# GLOBAL SINGLETON INSTANCE
# ------------------------------------------------------------
try:
    service_manager = ServiceManager()
    logger.info("🌍 Global ServiceManager instance created successfully.")
except Exception as e:
    logger.exception(f"❌ Failed to create ServiceManager instance: {e}")
    service_manager = None
