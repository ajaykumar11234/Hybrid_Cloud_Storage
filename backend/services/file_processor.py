import PyPDF2
import pytesseract
from PIL import Image
import tempfile
import os
import io
import platform


class FileProcessor:
    """File processing service for extracting text from PDFs, images, or text files."""

    def __init__(self):
        """Initialize Tesseract OCR configuration for both Windows and Linux."""
        self._configure_tesseract()

    def _configure_tesseract(self):
        """Detect and set the correct Tesseract binary path."""
        system = platform.system()
        tesseract_paths = []

        if system == "Windows":
            # Common Windows installation paths
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
        elif system in ["Linux", "Darwin"]:
            # Linux/macOS path (Docker & Render)
            tesseract_paths = ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]

        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"✅ [Tesseract] Found at: {path}")
                return

        print("⚠️ [Tesseract] Not found in common locations. OCR features may not work.")

    # ---------------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ---------------------------------------------------------------------
    def extract_text(self, filename: str, file_data: bytes) -> str:
        """Extract text content from various file types."""
        if not filename or not file_data:
            print("⚠️ [FileProcessor] Invalid input to extract_text()")
            return ""

        file_extension = filename.lower().split(".")[-1]

        try:
            if file_extension == "pdf":
                return self._extract_from_pdf(file_data)
            elif file_extension in ["png", "jpg", "jpeg", "tiff", "bmp"]:
                return self._extract_from_image(file_data)
            elif file_extension in ["txt", "csv", "json", "xml", "log", "md"]:
                return self._extract_from_text(file_data)
            elif file_extension in ["doc", "docx"]:
                return f"⚠️ Word document '{filename}' requires specialized library (e.g., python-docx)."
            else:
                print(f"⚠️ [FileProcessor] Unsupported file type: {file_extension}")
                return ""
        except Exception as e:
            print(f"❌ [FileProcessor] Unexpected error in extract_text(): {e}")
            return ""

    # ---------------------------------------------------------------------
    # PDF HANDLER
    # ---------------------------------------------------------------------
    def _extract_from_pdf(self, file_data: bytes) -> str:
        """Extract text from a PDF file using PyPDF2."""
        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file_data)
                tmp_file.flush()

            text = ""
            with open(tmp_file.name, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"

            return text.strip()
        except Exception as e:
            print(f"❌ [PDF] Error extracting text: {e}")
            return ""
        finally:
            if tmp_file and os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)

    # ---------------------------------------------------------------------
    # IMAGE HANDLER
    # ---------------------------------------------------------------------
    def _extract_from_image(self, file_data: bytes) -> str:
        """Extract text from an image using OCR (Tesseract)."""
        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                tmp_file.write(file_data)
                tmp_file.flush()

            image = Image.open(tmp_file.name)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            print(f"❌ [OCR] Error extracting text from image: {e}")
            return ""
        finally:
            if tmp_file and os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)

    # ---------------------------------------------------------------------
    # TEXT HANDLER
    # ---------------------------------------------------------------------
    def _extract_from_text(self, file_data: bytes) -> str:
        """Extract text from plain text or structured text files."""
        try:
            text = file_data.decode("utf-8", errors="ignore")
            return text.strip()
        except Exception as e:
            print(f"❌ [Text] Error decoding file: {e}")
            return ""


# ---------------------------------------------------------------------
# GLOBAL INSTANCE
# ---------------------------------------------------------------------
try:
    file_processor = FileProcessor()
    print("✅ [FileProcessor] Initialized successfully.")
except Exception as e:
    print(f"❌ [FileProcessor] Failed to initialize: {e}")
    file_processor = None
