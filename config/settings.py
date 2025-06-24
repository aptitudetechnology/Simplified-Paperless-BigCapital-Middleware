# config/settings.py
import os
import configparser
from pathlib import Path

class Config:
    def __init__(self, config_file='config.ini'):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        self.config['database'] = {
            'type': 'sqlite',
            'path': 'data/middleware.db'
        }
        self.config['ocr'] = {
            'language': 'eng',
            'confidence_threshold': '60',
            'dpi': '300'
        }
        self.config['processing'] = {
            'upload_folder': 'uploads',
            'max_file_size': '10485760',
            'allowed_extensions': 'pdf,png,jpg,jpeg,tiff'
        }
        self.config['web_interface'] = {
            'host': '0.0.0.0',
            'port': '5000',
            'debug': 'false',
            'secret_key': 'dev-secret-key-change-in-production'
        }
        self.config['logging'] = {
            'level': 'INFO',
            'file': 'logs/middleware.log'
        }

        self.config['currency'] = {
             'default': 'USD',
             'supported': 'USD,EUR,GBP,AUD,CAD'
     }
        
        with open(self.config_file, 'w') as f:
            self.config.write(f)
    
    def get(self, section, key, fallback=None):
        return self.config.get(section, key, fallback=fallback)
    
    def getint(self, section, key, fallback=None):
        return self.config.getint(section, key, fallback=fallback)
    
    def getboolean(self, section, key, fallback=None):
        return self.config.getboolean(section, key, fallback=fallback)

# database/models.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100))
    upload_date = Column(DateTime, default=datetime.utcnow)
    processed_date = Column(DateTime)
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    
    # OCR Results
    ocr_text = Column(Text)
    ocr_confidence = Column(Float)
    
    # Extracted Data
    vendor_name = Column(String(255))
    invoice_number = Column(String(100))
    invoice_date = Column(DateTime)
    total_amount = Column(Float)
    currency = Column(String(10))
    
    # Processing metadata
    processing_error = Column(Text)
    extraction_method = Column(String(50))  # tesseract, manual, etc.

class ProcessingStats(Base):
    __tablename__ = 'processing_stats'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.utcnow)
    documents_processed = Column(Integer, default=0)
    successful_extractions = Column(Integer, default=0)
    failed_extractions = Column(Integer, default=0)
    avg_processing_time = Column(Float)

# database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base
from config.settings import Config
import os

class DatabaseManager:
    def __init__(self, config: Config):
        self.config = config
        self.engine = None
        self.Session = None
        self.init_database()
    
    def init_database(self):
        db_type = self.config.get('database', 'type')
        db_path = self.config.get('database', 'path')
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        if db_type == 'sqlite':
            database_url = f'sqlite:///{db_path}'
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        self.engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        return self.Session()

# core/ocr_processor.py
import pytesseract
from PIL import Image
import pdf2image
import pypdf
from pathlib import Path
import tempfile
import os
from utils.exceptions import OCRProcessingError
from utils.logger import get_logger

logger = get_logger(__name__)

class OCRProcessor:
    def __init__(self, config):
        self.config = config
        self.language = config.get('ocr', 'language', 'eng')
        self.dpi = config.getint('ocr', 'dpi', 300)
        self.confidence_threshold = config.getint('ocr', 'confidence_threshold', 60)
    
    def process_document(self, file_path: str) -> dict:
        """Process document and extract text using OCR"""
        try:
            file_path = Path(file_path)
            file_extension = file_path.suffix.lower()
            
            if file_extension == '.pdf':
                return self._process_pdf(file_path)
            elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                return self._process_image(file_path)
            else:
                raise OCRProcessingError(f"Unsupported file type: {file_extension}")
        
        except Exception as e:
            logger.error(f"OCR processing failed for {file_path}: {str(e)}")
            raise OCRProcessingError(f"Failed to process document: {str(e)}")
    
    def _process_pdf(self, file_path: Path) -> dict:
        """Process PDF file - try text extraction first, then OCR"""
        # First try to extract text directly from PDF
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                if text.strip():  # If we got meaningful text
                    logger.info(f"Extracted text directly from PDF: {file_path}")
                    return {
                        'text': text,
                        'confidence': 100,  # Direct text extraction
                        'method': 'direct_pdf'
                    }
        except Exception as e:
            logger.warning(f"Direct PDF text extraction failed: {e}")
        
        # If direct extraction failed, use OCR on PDF pages
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Convert PDF to images
                pages = pdf2image.convert_from_path(
                    file_path, 
                    dpi=self.dpi,
                    output_folder=temp_dir
                )
                
                all_text = ""
                total_confidence = 0
                
                for i, page in enumerate(pages):
                    result = self._ocr_image(page)
                    all_text += f"--- Page {i+1} ---\n{result['text']}\n"
                    total_confidence += result['confidence']
                
                avg_confidence = total_confidence / len(pages) if pages else 0
                
                return {
                    'text': all_text,
                    'confidence': avg_confidence,
                    'method': 'ocr_pdf',
                    'pages': len(pages)
                }
                
        except Exception as e:
            logger.error(f"PDF OCR processing failed: {e}")
            raise OCRProcessingError(f"Failed to process PDF: {str(e)}")
    
    def _process_image(self, file_path: Path) -> dict:
        """Process image file using OCR"""
        try:
            image = Image.open(file_path)
            return self._ocr_image(image)
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            raise OCRProcessingError(f"Failed to process image: {str(e)}")
    
    def _ocr_image(self, image: Image.Image) -> dict:
        """Perform OCR on a PIL Image"""
        try:
            # Get detailed OCR data
            data = pytesseract.image_to_data(
                image, 
                lang=self.language, 
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text
            text = pytesseract.image_to_string(image, lang=self.language)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                'text': text,
                'confidence': avg_confidence,
                'method': 'tesseract_ocr'
            }
            
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            raise OCRProcessingError(f"OCR processing failed: {str(e)}")

# core/text_extractor.py
import re
from datetime import datetime
from typing import Dict, Optional, List
from utils.logger import get_logger

logger = get_logger(__name__)

class InvoiceDataExtractor:
    def __init__(self):
        # Common patterns for different data types
        self.amount_patterns = [
            r'total[:\s]*\$?([0-9,]+\.?[0-9]*)',
            r'amount[:\s]*\$?([0-9,]+\.?[0-9]*)',
            r'balance[:\s]*\$?([0-9,]+\.?[0-9]*)',
            r'\$([0-9,]+\.?[0-9]*)',
            r'([0-9,]+\.?[0-9]*)\s*(?:USD|EUR|GBP|AUD|CAD)'
        ]
        
        self.invoice_number_patterns = [
            r'invoice\s*#?[:\s]*([A-Za-z0-9\-]+)',
            r'inv[:\s]*([A-Za-z0-9\-]+)',
            r'receipt\s*#?[:\s]*([A-Za-z0-9\-]+)',
            r'#([A-Za-z0-9\-]{3,})'
        ]
        
        self.date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4})',
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})'
        ]
        
        self.vendor_patterns = [
            r'from[:\s]*([A-Za-z\s&.,]+)',
            r'vendor[:\s]*([A-Za-z\s&.,]+)',
            r'company[:\s]*([A-Za-z\s&.,]+)',
            r'billed\s+by[:\s]*([A-Za-z\s&.,]+)'
        ]
    
    def extract_data(self, text: str) -> Dict:
        """Extract structured data from OCR text"""
        text_lower = text.lower()
        
        extracted_data = {
            'vendor_name': self._extract_vendor(text, text_lower),
            'invoice_number': self._extract_invoice_number(text, text_lower),
            'invoice_date': self._extract_date(text, text_lower),
            'total_amount': self._extract_amount(text, text_lower),
            'currency': self._extract_currency(text, text_lower),
            'line_items': self._extract_line_items(text, text_lower)
        }
        
        logger.info(f"Extracted data: {extracted_data}")
        return extracted_data
    
    def _extract_amount(self, text: str, text_lower: str) -> Optional[float]:
        """Extract total amount from text"""
        amounts = []
        
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                try:
                    # Remove commas and convert to float
                    amount = float(match.replace(',', ''))
                    amounts.append(amount)
                except ValueError:
                    continue
        
        # Return the largest amount found (likely the total)
        return max(amounts) if amounts else None
    
    def _extract_invoice_number(self, text: str, text_lower: str) -> Optional[str]:
        """Extract invoice number from text"""
        for pattern in self.invoice_number_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None
    
    def _extract_date(self, text: str, text_lower: str) -> Optional[datetime]:
        """Extract date from text"""
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Try to parse the date
                    date_obj = self._parse_date(match)
                    if date_obj:
                        return date_obj
                except:
                    continue
        return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string into datetime object"""
        date_formats = [
            '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y', '%d-%m-%Y',
            '%Y/%m/%d', '%Y-%m-%d',
            '%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y',
            '%m/%d/%y', '%m-%d-%y', '%d/%m/%y', '%d-%m-%y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
    
    def _extract_vendor(self, text: str, text_lower: str) -> Optional[str]:
        """Extract vendor name from text"""
        # Look for common vendor patterns
        for pattern in self.vendor_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                vendor = match.group(1).strip()
                # Clean up vendor name
                vendor = re.sub(r'[^\w\s&.,]', '', vendor)
                return vendor.title()
        
        # If no pattern matches, try to get the first meaningful line
        lines = text.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if len(line) > 3 and not re.match(r'^\d', line):
                # Remove common invoice-related words
                clean_line = re.sub(r'\b(invoice|receipt|bill|statement)\b', '', line, flags=re.IGNORECASE)
                clean_line = clean_line.strip()
                if clean_line:
                    return clean_line.title()
        
        return None
    
    def _extract_currency(self, text: str, text_lower: str) -> str:
        """Extract currency from text"""
        if '$' in text:
            return 'USD'
        elif '€' in text:
            return 'EUR'
        elif '£' in text:
            return 'GBP'
        elif re.search(r'\b(usd|dollar)\b', text_lower):
            return 'USD'
        elif re.search(r'\b(eur|euro)\b', text_lower):
            return 'EUR'
        elif re.search(r'\b(gbp|pound)\b', text_lower):
            return 'GBP'
        elif re.search(r'\b(aud)\b', text_lower):
            return 'AUD'
        else:
            return 'USD'  # Default to USD
    
    def _extract_line_items(self, text: str, text_lower: str) -> List[Dict]:
        """Extract line items from text (basic implementation)"""
        # This is a basic implementation - can be enhanced based on specific needs
        line_items = []
        lines = text.split('\n')
        
        for line in lines:
            # Look for lines that might contain item descriptions and amounts
            if re.search(r'\d+\.?\d*\s*\$?\d+\.?\d*', line):
                # This line might contain quantity and amount
                line_items.append({
                    'description': line.strip(),
                    'raw_text': line.strip()
                })
        
        return line_items[:10]  # Limit to first 10 items

# core/processor.py
from datetime import datetime
import os
from pathlib import Path
from database.connection import DatabaseManager
from database.models import Document, ProcessingStats
from core.ocr_processor import OCRProcessor
from core.text_extractor import InvoiceDataExtractor
from utils.logger import get_logger
from utils.exceptions import ProcessingError

logger = get_logger(__name__)

class DocumentProcessor:
    def __init__(self, config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.ocr_processor = OCRProcessor(config)
        self.data_extractor = InvoiceDataExtractor()
        
        # Ensure upload directory exists
        upload_folder = config.get('processing', 'upload_folder')
        os.makedirs(upload_folder, exist_ok=True)
    
    def process_document(self, file_path: str, original_filename: str) -> Document:
        """Process a document through OCR and data extraction"""
        session = self.db_manager.get_session()
        
        try:
            # Create document record
            file_size = os.path.getsize(file_path)
            document = Document(
                filename=os.path.basename(file_path),
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                status='processing'
            )
            
            session.add(document)
            session.commit()
            
            logger.info(f"Processing document {document.id}: {original_filename}")
            
            # Perform OCR
            start_time = datetime.now()
            ocr_result = self.ocr_processor.process_document(file_path)
            
            # Store OCR results
            document.ocr_text = ocr_result['text']
            document.ocr_confidence = ocr_result['confidence']
            document.extraction_method = ocr_result['method']
            
            # Extract structured data
            extracted_data = self.data_extractor.extract_data(ocr_result['text'])
            
            # Store extracted data
            document.vendor_name = extracted_data.get('vendor_name')
            document.invoice_number = extracted_data.get('invoice_number')
            document.invoice_date = extracted_data.get('invoice_date')
            document.total_amount = extracted_data.get('total_amount')
            document.currency = extracted_data.get('currency')
            
            # Mark as completed
            document.status = 'completed'
            document.processed_date = datetime.now()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Document {document.id} processed successfully in {processing_time:.2f}s")
            
            # Update processing stats
            self._update_stats(session, processing_time, success=True)
            
            session.commit()
            return document
            
        except Exception as e:
            logger.error(f"Failed to process document {original_filename}: {str(e)}")
            
            if 'document' in locals():
                document.status = 'failed'
                document.processing_error = str(e)
                document.processed_date = datetime.now()
                session.commit()
            
            self._update_stats(session, 0, success=False)
            raise ProcessingError(f"Document processing failed: {str(e)}")
        
        finally:
            session.close()
    
    def _update_stats(self, session, processing_time: float, success: bool):
        """Update processing statistics"""
        today = datetime.now().date()
        
        # Get or create today's stats
        stats = session.query(ProcessingStats).filter(
            ProcessingStats.date >= datetime.combine(today, datetime.min.time())
        ).first()
        
        if not stats:
            stats = ProcessingStats(date=datetime.now())
            session.add(stats)
        
        stats.documents_processed += 1
        if success:
            stats.successful_extractions += 1
        else:
            stats.failed_extractions += 1
        
        # Update average processing time
        if stats.avg_processing_time:
            stats.avg_processing_time = (stats.avg_processing_time + processing_time) / 2
        else:
            stats.avg_processing_time = processing_time

# utils/logger.py
import logging
import os
from datetime import datetime

def setup_logging(config):
    """Setup logging configuration"""
    log_level = config.get('logging', 'level', 'INFO')
    log_file = config.get('logging', 'file', 'logs/middleware.log')
    
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def get_logger(name):
    """Get logger instance"""
    return logging.getLogger(name)

# utils/exceptions.py
class MiddlewareError(Exception):
    """Base exception for middleware errors"""
    pass

class OCRProcessingError(MiddlewareError):
    """Raised when OCR processing fails"""
    pass

class ProcessingError(MiddlewareError):
    """Raised when document processing fails"""
    pass

class DatabaseError(MiddlewareError):
    """Raised when database operations fail"""
    pass

# requirements.txt content
"""
Flask==2.3.3
SQLAlchemy==2.0.21
pytesseract==0.3.10
Pillow==10.0.1
PyPDF2==3.0.1
pdf2image==1.16.3
python-dotenv==1.0.0
pytest==7.4.2
Werkzeug==2.3.7
"""
