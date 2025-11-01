import PyPDF2
import pytesseract
from PIL import Image
import tempfile
import os
import io

class FileProcessor:
    """File processing service for text extraction"""
    
    def __init__(self):
        # Configure Tesseract for Windows
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
        ]
        
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"✅ Tesseract found at: {path}")
                break
        else:
            print("⚠️ Tesseract not found in common locations. OCR features may not work.")
    
    def extract_text(self, filename: str, file_data: bytes) -> str:
        """Extract text from file based on file type"""
        file_extension = filename.lower().split('.')[-1]
        
        if file_extension in ['pdf']:
            return self._extract_from_pdf(file_data)
        elif file_extension in ['png', 'jpg', 'jpeg', 'tiff', 'bmp']:
            return self._extract_from_image(file_data)
        elif file_extension in ['txt', 'csv', 'json', 'xml', 'log', 'md']:
            return self._extract_from_text(file_data)
        elif file_extension in ['doc', 'docx']:
            return f"Word document: {filename}. Content analysis requires additional libraries."
        else:
            return None
    
    def _extract_from_pdf(self, file_data: bytes) -> str:
        """Extract text from PDF file"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(file_data)
                tmp_file.flush()
                
                with open(tmp_file.name, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                
            os.unlink(tmp_file.name)
            return text.strip()
        except Exception as e:
            print(f"❌ Error extracting text from PDF: {e}")
            return None
    
    def _extract_from_image(self, file_data: bytes) -> str:
        """Extract text from image using OCR"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                tmp_file.write(file_data)
                tmp_file.flush()
                
                image = Image.open(tmp_file.name)
                text = pytesseract.image_to_string(image)
                
            os.unlink(tmp_file.name)
            return text.strip()
        except Exception as e:
            print(f"❌ Error extracting text from image: {e}")
            return None
    
    def _extract_from_text(self, file_data: bytes) -> str:
        """Extract text from plain text file"""
        try:
            return file_data.decode('utf-8')
        except Exception as e:
            print(f"❌ Error extracting text from text file: {e}")
            return None

# Global instance
file_processor = FileProcessor()