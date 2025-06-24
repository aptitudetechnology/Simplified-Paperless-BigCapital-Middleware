"""
Document processor for handling file uploads and processing
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# OCR and document processing imports
try:
    import pytesseract
    from PIL import Image
    import fitz  # PyMuPDF for PDF processing
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Configuration for simulation vs real processing
USE_SIMULATION = not OCR_AVAILABLE  # Set to False to use real OCR when libraries are available


class DocumentProcessor:
    """Handles document processing and integration with BigCapital"""
    
    def __init__(self, config, db_manager):
        """
        Initialize the document processor
        
        Args:
            config: Configuration object
            db_manager: Database manager instance
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Get processing configuration
        self.max_file_size = int(config.get('processing', 'max_file_size', '10485760'))  # 10MB default
        self.allowed_extensions = config.get('processing', 'allowed_extensions', 'pdf,jpg,jpeg,png,txt').split(',')
        self.upload_folder = config.get('processing', 'upload_folder', 'uploads')
        
        # OCR configuration
        self.tesseract_path = config.get('ocr', 'tesseract_path', None)
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        
        # Ensure upload folder exists
        os.makedirs(self.upload_folder, exist_ok=True)
        
        # Log OCR status
        if USE_SIMULATION:
            self.logger.warning("Using simulation mode - OCR libraries not available or disabled")
        else:
            self.logger.info("OCR processing enabled")
        
        self.logger.info(f"DocumentProcessor initialized with upload folder: {self.upload_folder}")
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            dict: File information including size, name, extension, etc.
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            file_extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            
            return {
                'filename': filename,
                'file_path': file_path,
                'file_size': file_size,
                'extension': file_extension,
                'is_allowed': self.is_allowed_file(filename),
                'size_valid': file_size <= self.max_file_size,
                'exists': True
            }
        except Exception as e:
            self.logger.error(f"Error getting file info for {file_path}: {str(e)}")
            return {
                'filename': os.path.basename(file_path) if file_path else '',
                'file_path': file_path,
                'file_size': 0,
                'extension': '',
                'is_allowed': False,
                'size_valid': False,
                'exists': False,
                'error': str(e)
            }
    
    def is_allowed_file(self, filename: str) -> bool:
        """
        Check if the file extension is allowed
        
        Args:
            filename: Name of the file to check
            
        Returns:
            bool: True if file extension is allowed
        """
        if not filename:
            return False
        
        extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return extension in [ext.strip().lower() for ext in self.allowed_extensions]
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file using PyMuPDF (faster performance)
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            str: Extracted text
        """
        if USE_SIMULATION:
            return "Sample PDF text content for simulation"
        
        try:
            text = ""
            pdf_document = fitz.open(file_path)
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                text += page.get_text() + "\n"
            
            pdf_document.close()
            return text.strip()
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
            raise
    
    def extract_text_from_image(self, file_path: str) -> str:
        """
        Extract text from image file using OCR
        
        Args:
            file_path: Path to the image file
            
        Returns:
            str: Extracted text
        """
        if USE_SIMULATION:
            return "Sample OCR text content for simulation"
        
        try:
            image = Image.open(file_path)
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Use pytesseract to extract text
            text = pytesseract.image_to_string(image, config='--psm 6')
            return text.strip()
        except Exception as e:
            self.logger.error(f"Error extracting text from image {file_path}: {str(e)}")
            raise
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """
        Extract text from plain text file
        
        Args:
            file_path: Path to the text file
            
        Returns:
            str: File content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as file:
                return file.read().strip()
        except Exception as e:
            self.logger.error(f"Error reading text file {file_path}: {str(e)}")
            raise
    
    def extract_text_from_document(self, file_path: str, file_extension: str) -> str:
        """
        Extract text from document based on file type
        
        Args:
            file_path: Path to the document
            file_extension: File extension (without dot)
            
        Returns:
            str: Extracted text
        """
        file_extension = file_extension.lower()
        
        if file_extension == 'pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_extension in ['jpg', 'jpeg', 'png']:
            return self.extract_text_from_image(file_path)
        elif file_extension == 'txt':
            return self.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    def parse_invoice_data(self, ocr_text: str) -> Dict[str, Any]:
        """
        Parse invoice data from OCR text
        This is a basic implementation - would be enhanced with ML/AI in production
        
        Args:
            ocr_text: Text extracted from document
            
        Returns:
            dict: Parsed invoice data
        """
        if USE_SIMULATION:
            return {
                'vendor_name': 'Sample Vendor Ltd.',
                'invoice_number': 'INV-2024-001',
                'invoice_date': '2024-01-15',
                'due_date': '2024-02-14',
                'total_amount': 1250.00,
                'subtotal': 1000.00,
                'tax_amount': 250.00,
                'currency': 'USD',
                'line_items': [
                    {
                        'description': 'Professional Services',
                        'quantity': 10,
                        'unit_price': 100.00,
                        'total': 1000.00
                    }
                ],
                'extraction_confidence': 0.85,
                'extraction_method': 'simulation'
            }
        
        # Basic pattern matching for invoice data
        import re
        
        invoice_data = {
            'vendor_name': None,
            'invoice_number': None,
            'invoice_date': None,
            'due_date': None,
            'total_amount': None,
            'subtotal': None,
            'tax_amount': None,
            'currency': 'USD',  # Default currency
            'line_items': [],
            'extraction_confidence': 0.5,  # Lower confidence for basic parsing
            'extraction_method': 'basic_ocr'
        }
        
        # Look for invoice number
        invoice_patterns = [
            r'invoice\s*#?\s*:?\s*([A-Z0-9\-]+)',
            r'inv\.\s*#?\s*:?\s*([A-Z0-9\-]+)',
            r'bill\s*#?\s*:?\s*([A-Z0-9\-]+)'
        ]
        
        for pattern in invoice_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                invoice_data['invoice_number'] = match.group(1)
                break
        
        # Look for dates
        date_pattern = r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})'
        dates = re.findall(date_pattern, ocr_text)
        if dates:
            invoice_data['invoice_date'] = dates[0]  # First date found
            if len(dates) > 1:
                invoice_data['due_date'] = dates[1]  # Second date might be due date
        
        # Look for total amount
        amount_patterns = [
            r'total\s*:?\s*\$?(\d+\.?\d*)',
            r'amount\s*due\s*:?\s*\$?(\d+\.?\d*)',
            r'balance\s*:?\s*\$?(\d+\.?\d*)'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                try:
                    invoice_data['total_amount'] = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        # Look for vendor name (first line that's not a number or date)
        lines = ocr_text.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and not re.match(r'^\d+[\/\-]\d+[\/\-]\d+', line) and not re.match(r'^[\d\$\.\-\s]+$', line):
                if len(line) > 3:  # Reasonable length for company name
                    invoice_data['vendor_name'] = line
                    break
        
        return invoice_data
    
    def process_document_by_id(self, doc_id: int) -> Dict[str, Any]:
        """
        Process a document by its database ID
        
        Args:
            doc_id: Database ID of the document to process
            
        Returns:
            dict: Processing result with status and details
        """
        try:
            # Get document from database
            doc = self.db_manager.get_document(doc_id)
            if not doc:
                raise ValueError(f"Document {doc_id} not found in database")
            
            self.logger.info(f"Starting processing for document ID {doc_id}: {doc['filename']}")
            
            # Update status to processing
            self.db_manager.update_document(doc_id, status='processing')
            
            # Validate file exists
            file_path = doc['file_path']
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Validate file
            if not self.is_allowed_file(doc['filename']):
                raise ValueError(f"File type not allowed: {doc['filename']}")
            
            # Get file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                raise ValueError(f"File too large: {file_size} bytes (max: {self.max_file_size})")
            
            # Extract file extension
            filename = doc['filename']
            file_extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            
            # Phase 1 Processing Steps:
            # 1. Extract text from document (OCR for images, text extraction for PDFs)
            self.logger.info(f"Extracting text from {filename} (type: {file_extension})")
            ocr_text = self.extract_text_from_document(file_path, file_extension)
            
            # 2. Parse invoice data from extracted text
            self.logger.info("Parsing invoice data from extracted text")
            extracted_data = self.parse_invoice_data(ocr_text)
            
            # 3. Save extracted data to database (Phase 1 complete here)
            self.logger.info("Saving extracted data to database")
            self.db_manager.update_document(
                doc_id,
                status='completed',
                processed_date=datetime.now(),
                extracted_data=json.dumps(extracted_data),
                ocr_text=ocr_text
            )
            
            self.logger.info(f"Successfully processed document ID {doc_id}: {doc['filename']}")
            
            return {
                'success': True,
                'document_id': doc_id,
                'data': extracted_data,
                'ocr_text_length': len(ocr_text),
                'simulation_mode': USE_SIMULATION,
                'message': f"Document {doc['filename']} processed successfully"
            }
            
        except Exception as e:
            # Update document status to failed
            error_msg = str(e)
            self.logger.error(f"Error processing document ID {doc_id}: {error_msg}")
            
            try:
                self.db_manager.update_document(
                    doc_id,
                    status='failed',
                    error_message=error_msg,
                    processed_date=datetime.now()
                )
            except Exception as db_error:
                self.logger.error(f"Failed to update document status to failed: {db_error}")
            
            return {
                'success': False,
                'document_id': doc_id,
                'error': error_msg,
                'simulation_mode': USE_SIMULATION,
                'message': f"Failed to process document: {error_msg}"
            }
    
    def process_document(self, file_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a document file (legacy method - kept for backward compatibility)
        
        Args:
            file_path: Path to the document file
            metadata: Additional metadata for the document
            
        Returns:
            dict: Processing result with status and details
        """
        self.logger.warning("process_document(file_path) is deprecated. Use process_document_by_id(doc_id) instead.")
        
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Get file info
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            
            # Validate file
            if not self.is_allowed_file(filename):
                raise ValueError(f"File type not allowed: {filename}")
            
            if file_size > self.max_file_size:
                raise ValueError(f"File too large: {file_size} bytes (max: {self.max_file_size})")
            
            # Create processing record
            processing_data = {
                'filename': filename,
                'file_path': file_path,
                'file_size': file_size,
                'status': 'processing',
                'created_at': datetime.now().isoformat(),
                'metadata': metadata or {},
                'simulation_mode': USE_SIMULATION
            }
            
            self.logger.info(f"Processing document: {filename}")
            
            # Extract text and parse data
            file_extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            ocr_text = self.extract_text_from_document(file_path, file_extension)
            extracted_data = self.parse_invoice_data(ocr_text)
            
            # Update processing record
            processing_data['status'] = 'completed'
            processing_data['processed_at'] = datetime.now().isoformat()
            processing_data['extracted_data'] = extracted_data
            processing_data['ocr_text'] = ocr_text
            
            self.logger.info(f"Successfully processed document: {filename}")
            return {
                'success': True,
                'data': processing_data,
                'message': f"Document {filename} processed successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error processing document {file_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'simulation_mode': USE_SIMULATION,
                'message': f"Failed to process document: {str(e)}"
            }
    
    def get_processing_status(self, document_id: str) -> Dict[str, Any]:
        """
        Get the processing status of a document
        
        Args:
            document_id: ID of the document
            
        Returns:
            dict: Document status information
        """
        try:
            if hasattr(self.db_manager, 'get_document'):
                return self.db_manager.get_document(document_id)
            else:
                return {
                    'document_id': document_id,
                    'status': 'unknown',
                    'message': 'Database lookup not implemented'
                }
        except Exception as e:
            self.logger.error(f"Error getting document status: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }
    
    def list_processed_documents(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get a list of processed documents
        
        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            list: List of document records
        """
        try:
            if hasattr(self.db_manager, 'get_documents'):
                return self.db_manager.get_documents(limit=limit, offset=offset)
            else:
                return []
        except Exception as e:
            self.logger.error(f"Error listing documents: {str(e)}")
            return []
    
    def delete_document(self, document_id: str) -> Dict[str, Any]:
        """
        Delete a processed document
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            dict: Deletion result
        """
        try:
            # TODO: Implement document deletion
            if hasattr(self.db_manager, 'delete_document'):
                result = self.db_manager.delete_document(document_id)
                return {
                    'success': True,
                    'message': f"Document {document_id} deleted successfully"
                }
            else:
                return {
                    'success': False,
                    'message': 'Document deletion not implemented'
                }
        except Exception as e:
            self.logger.error(f"Error deleting document: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_old_files(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up old processed files
        
        Args:
            days_old: Number of days after which files should be cleaned up
            
        Returns:
            dict: Cleanup result
        """
        try:
            # TODO: Implement file cleanup logic
            cleaned_count = 0
            self.logger.info(f"File cleanup completed. Removed {cleaned_count} files older than {days_old} days")
            
            return {
                'success': True,
                'cleaned_count': cleaned_count,
                'message': f"Cleanup completed. Removed {cleaned_count} files"
            }
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
