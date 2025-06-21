# core/ocr_processor.py
"""
OCR Processor for Paperless-BigCapital Middleware
Handles Optical Character Recognition for document processing
"""

import logging
import os
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path

# Try to import OCR libraries (they might not be installed)
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

logger = logging.getLogger(__name__)

class OCRProcessor:
    """
    OCR Processor for extracting text from documents and images
    """
    
    def __init__(self, engine: str = 'tesseract', language: str = 'eng'):
        """
        Initialize OCR Processor
        
        Args:
            engine: OCR engine to use ('tesseract' or 'easyocr')
            language: Language code for OCR (default: 'eng')
        """
        self.engine = engine.lower()
        self.language = language
        self.reader = None
        
        # Initialize the selected OCR engine
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the selected OCR engine"""
        if self.engine == 'tesseract':
            if not TESSERACT_AVAILABLE:
                logger.warning("Tesseract not available. Install pytesseract and PIL: pip install pytesseract pillow")
                self.engine = 'mock'
            else:
                logger.info("Using Tesseract OCR engine")
        
        elif self.engine == 'easyocr':
            if not EASYOCR_AVAILABLE:
                logger.warning("EasyOCR not available. Install easyocr: pip install easyocr")
                self.engine = 'mock'
            else:
                try:
                    self.reader = easyocr.Reader([self.language])
                    logger.info("Using EasyOCR engine")
                except Exception as e:
                    logger.error(f"Failed to initialize EasyOCR: {e}")
                    self.engine = 'mock'
        
        else:
            logger.info("Using mock OCR engine (for development)")
            self.engine = 'mock'
    
    def extract_text(self, file_path: str) -> str:
        """
        Extract text from an image or PDF file
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Extracted text as string
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_extension = Path(file_path).suffix.lower()
        
        try:
            if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
                return self._extract_from_image(file_path)
            elif file_extension == '.pdf':
                return self._extract_from_pdf(file_path)
            else:
                logger.warning(f"Unsupported file type: {file_extension}")
                return ""
        
        except Exception as e:
            logger.error(f"OCR extraction failed for {file_path}: {e}")
            return ""
    
    def _extract_from_image(self, image_path: str) -> str:
        """Extract text from an image file"""
        if self.engine == 'tesseract':
            return self._tesseract_extract_image(image_path)
        elif self.engine == 'easyocr':
            return self._easyocr_extract_image(image_path)
        else:
            return self._mock_extract(image_path)
    
    def _extract_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file"""
        # For PDF processing, you might want to convert pages to images first
        # This is a simplified implementation
        logger.info(f"PDF OCR not fully implemented for {pdf_path}")
        return self._mock_extract(pdf_path)
    
    def _tesseract_extract_image(self, image_path: str) -> str:
        """Extract text using Tesseract"""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang=self.language)
            return text.strip()
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            return ""
    
    def _easyocr_extract_image(self, image_path: str) -> str:
        """Extract text using EasyOCR"""
        try:
            results = self.reader.readtext(image_path)
            text = ' '.join([result[1] for result in results])
            return text.strip()
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}")
            return ""
    
    def _mock_extract(self, file_path: str) -> str:
        """Mock OCR extraction for development/testing"""
        filename = os.path.basename(file_path)
        return f"[MOCK OCR] Extracted text from {filename}. Install OCR libraries for real text extraction."
    
    def get_supported_formats(self) -> list:
        """Get list of supported file formats"""
        return ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.pdf']
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the OCR system
        
        Returns:
            Dict with health check results
        """
        status = {
            'engine': self.engine,
            'language': self.language,
            'tesseract_available': TESSERACT_AVAILABLE,
            'easyocr_available': EASYOCR_AVAILABLE,
            'status': 'healthy' if self.engine != 'mock' else 'mock_mode'
        }
        
        if self.engine == 'tesseract' and TESSERACT_AVAILABLE:
            try:
                # Test tesseract installation
                pytesseract.get_tesseract_version()
                status['tesseract_version'] = pytesseract.get_tesseract_version()
            except Exception as e:
                status['status'] = 'error'
                status['error'] = str(e)
        
        return status

# Convenience function for quick OCR
def extract_text_from_file(file_path: str, engine: str = 'tesseract', language: str = 'eng') -> str:
    """
    Convenience function to extract text from a file
    
    Args:
        file_path: Path to the file
        engine: OCR engine to use
        language: Language code
        
    Returns:
        Extracted text
    """
    processor = OCRProcessor(engine=engine, language=language)
    return processor.extract_text(file_path)
