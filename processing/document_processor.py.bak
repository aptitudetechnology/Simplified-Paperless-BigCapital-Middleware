"""
Document processor for handling file uploads and processing
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime


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

        # Ensure upload folder exists
        os.makedirs(self.upload_folder, exist_ok=True)

        self.logger.info(f"DocumentProcessor initialized with upload folder: {self.upload_folder}")

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

    def extract_text(self, filepath: str) -> str:
        """
        Placeholder for text extraction logic.
        This method should extract text from the given file (e.g., PDF, image).

        Args:
            filepath: The path to the document file.

        Returns:
            str: The extracted text from the document.
        """
        self.logger.info(f"Extracting text from {filepath} (placeholder)")
        # In a real implementation, you would use libraries like PyPDF2, Tesseract (for OCR), etc.
        # For demonstration, returning a dummy text.
        return f"Extracted text from {os.path.basename(filepath)}: This is a dummy text."

    def process_with_ai(self, extracted_text: str) -> Dict[str, Any]:
        """
        Placeholder for AI processing logic.
        This method should send the extracted text to an AI model
        to extract information like vendor and amount.

        Args:
            extracted_text: The text extracted from the document.

        Returns:
            dict: A dictionary containing processed data (e.g., 'vendor', 'amount', 'raw_response').
        """
        self.logger.info(f"Processing with AI (placeholder) for text: {extracted_text[:50]}...")
        # In a real implementation, you would interact with an AI API.
        # For demonstration, returning dummy data.
        return {
            'vendor': 'Dummy Vendor Inc.',
            'amount': 123.45,
            'raw_response': '{"vendor": "Dummy Vendor Inc.", "amount": 123.45, "confidence": 0.95}'
        }

    def process_document(self, file_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a document file

        Args:
            file_path: Path to the document file
            metadata: Additional metadata for the document

        Returns:
            dict: Processing result with status and details
        """
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
                'metadata': metadata or {}
            }

            self.logger.info(f"Processing document: {filename}")

            # TODO: Add actual document processing logic here
            # This is where you would:
            # 1. Extract text from PDFs
            # 2. Perform OCR on images
            # 3. Parse invoice data
            # 4. Send to BigCapital API

            # For now, just mark as processed
            processing_data['status'] = 'completed'
            processing_data['processed_at'] = datetime.now().isoformat()

            # Store in database (if database methods exist)
            try:
                if hasattr(self.db_manager, 'store_document'):
                    doc_id = self.db_manager.store_document(processing_data)
                    processing_data['document_id'] = doc_id
            except Exception as db_error:
                self.logger.warning(f"Failed to store in database: {db_error}")

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
                'message': f"Failed to process document: {str(e)}"
            }

    def process_document_by_id(self, doc_id: int):
        """Process document by database ID - updates existing record instead of creating new one"""
        try:
            # Get the existing document from database
            doc = self.db_manager.get_document(doc_id)
            if not doc:
                raise ValueError(f"Document with ID {doc_id} not found in database")

            print(f"Processing document ID: {doc_id}, File: {doc.get('filename', 'Unknown')}")

            # Update status to processing
            self.db_manager.update_document(doc_id, status='processing')

            # Get the file path from the document record
            filepath = doc.get('filepath') or doc.get('file_path')
            if not filepath:
                raise ValueError(f"No filepath found for document ID {doc_id}")

            # Verify file exists
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {filepath}")

            # Extract text from the document
            extracted_text = self.extract_text(filepath)
            if not extracted_text:
                raise ValueError("No text could be extracted from document")

            # Process with AI to extract vendor and amount
            processed_data = self.process_with_ai(extracted_text)

            # Update the existing document record with extracted data
            update_data = {
                'status': 'completed',
                'vendor': processed_data.get('vendor', 'Unknown'),
                'amount': processed_data.get('amount', 0.0),
                'extracted_text': extracted_text,
                'processed_date': datetime.now().isoformat(),
                'ai_response': processed_data.get('raw_response', '')
            }

            self.db_manager.update_document(doc_id, **update_data)

            print(f"Successfully processed document ID: {doc_id}")
            print(f"Vendor: {processed_data.get('vendor', 'Unknown')}")
            print(f"Amount: {processed_data.get('amount', 0.0)}")

            return processed_data

        except Exception as e:
            error_msg = f"Error processing document ID {doc_id}: {str(e)}"
            print(error_msg)

            # Update status to failed with error message
            self.db_manager.update_document(doc_id,
                                            status='failed',
                                            error_message=str(e),
                                            processed_date=datetime.now().isoformat())
            raise

    def get_processing_status(self, document_id: str) -> Dict[str, Any]:
        """
        Get the processing status of a document

        Args:
            document_id: ID of the document

        Returns:
            dict: Document status information
        """
        try:
            # TODO: Implement database lookup
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
            # TODO: Implement database query
            if hasattr(self.db_manager, 'list_documents'):
                return self.db_manager.list_documents(limit=limit, offset=offset)
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
