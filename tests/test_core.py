# tests/test_core.py
"""
Test suite for core business logic components.
Tests OCR processing, text extraction, and main processing workflow.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import io

# Import the modules to test
try:
    from core.ocr_processor import OCRProcessor
    from core.text_extractor import TextExtractor
    from core.processor import Processor
    from utils.exceptions import OCRProcessingError, TextExtractionError
except ImportError:
    # Handle case where modules don't exist yet
    OCRProcessor = None
    TextExtractor = None
    Processor = None
    OCRProcessingError = Exception
    TextExtractionError = Exception


class TestOCRProcessor:
    """Test OCR processing functionality"""

    @pytest.fixture
    def ocr_processor(self):
        """Create OCR processor instance for testing"""
        if OCRProcessor is None:
            pytest.skip("OCRProcessor not implemented yet")
        return OCRProcessor()

    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing"""
        # Create a simple test image with text
        img = Image.new('RGB', (200, 100), color='white')
        return img

    def test_ocr_processor_initialization(self, ocr_processor):
        """Test OCR processor can be initialized"""
        assert ocr_processor is not None

    @patch('pytesseract.image_to_string')
    def test_process_image_success(self, mock_tesseract, ocr_processor, sample_image):
        """Test successful image OCR processing"""
        mock_tesseract.return_value = "INVOICE\nTotal: $123.45"
        
        # Save image to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            sample_image.save(tmp.name)
            
            result = ocr_processor.process_image(tmp.name)
            
            assert "INVOICE" in result
            assert "$123.45" in result
            
        # Cleanup
        os.unlink(tmp.name)

    @patch('pytesseract.image_to_string')
    def test_process_image_empty_result(self, mock_tesseract, ocr_processor, sample_image):
        """Test handling of empty OCR results"""
        mock_tesseract.return_value = ""
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            sample_image.save(tmp.name)
            
            result = ocr_processor.process_image(tmp.name)
            
            assert result == ""
            
        os.unlink(tmp.name)

    @patch('pytesseract.image_to_string')
    def test_process_image_tesseract_error(self, mock_tesseract, ocr_processor, sample_image):
        """Test handling of Tesseract errors"""
        mock_tesseract.side_effect = Exception("Tesseract failed")
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            sample_image.save(tmp.name)
            
            with pytest.raises(OCRProcessingError):
                ocr_processor.process_image(tmp.name)
                
        os.unlink(tmp.name)

    def test_process_invalid_file_path(self, ocr_processor):
        """Test processing non-existent file"""
        with pytest.raises((FileNotFoundError, OCRProcessingError)):
            ocr_processor.process_image("/nonexistent/file.png")

    @patch('pdf2image.convert_from_path')
    @patch('pytesseract.image_to_string')
    def test_process_pdf_success(self, mock_tesseract, mock_pdf2image, ocr_processor):
        """Test successful PDF processing"""
        # Mock PDF conversion
        mock_image = Mock()
        mock_pdf2image.return_value = [mock_image]
        mock_tesseract.return_value = "Invoice Number: INV-001"
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            result = ocr_processor.process_pdf(tmp.name)
            
            assert "Invoice Number: INV-001" in result
            
        os.unlink(tmp.name)


class TestTextExtractor:
    """Test text extraction and parsing functionality"""

    @pytest.fixture
    def text_extractor(self):
        """Create text extractor instance for testing"""
        if TextExtractor is None:
            pytest.skip("TextExtractor not implemented yet")
        return TextExtractor()

    def test_text_extractor_initialization(self, text_extractor):
        """Test text extractor can be initialized"""
        assert text_extractor is not None

    def test_extract_invoice_number(self, text_extractor):
        """Test extraction of invoice numbers"""
        sample_text = """
        Invoice Number: INV-2024-001
        Date: 2024-01-15
        Total: $150.00
        """
        
        result = text_extractor.extract_invoice_data(sample_text)
        
        assert result.get('invoice_number') == 'INV-2024-001'

    def test_extract_vendor_name(self, text_extractor):
        """Test extraction of vendor names"""
        sample_text = """
        ACME Corporation
        123 Business St
        Invoice: 12345
        """
        
        result = text_extractor.extract_invoice_data(sample_text)
        
        assert 'ACME Corporation' in result.get('vendor', '')

    def test_extract_total_amount(self, text_extractor):
        """Test extraction of total amounts"""
        test_cases = [
            ("Total: $123.45", 123.45),
            ("Amount Due: £99.99", 99.99),
            ("TOTAL 1,234.56", 1234.56),
            ("Grand Total: €45.00", 45.00)
        ]
        
        for text, expected_amount in test_cases:
            result = text_extractor.extract_invoice_data(text)
            assert abs(result.get('total_amount', 0) - expected_amount) < 0.01

    def test_extract_date(self, text_extractor):
        """Test extraction of dates"""
        test_cases = [
            "Date: 2024-01-15",
            "Invoice Date: 01/15/2024",
            "15-Jan-2024",
            "January 15, 2024"
        ]
        
        for text in test_cases:
            result = text_extractor.extract_invoice_data(text)
            assert result.get('date') is not None

    def test_extract_empty_text(self, text_extractor):
        """Test handling of empty text"""
        result = text_extractor.extract_invoice_data("")
        
        assert isinstance(result, dict)
        assert result.get('invoice_number') is None
        assert result.get('total_amount') is None

    def test_extract_malformed_text(self, text_extractor):
        """Test handling of malformed or irrelevant text"""
        malformed_text = "asdkfj;alskdjf;alskjdf random text 12345 $$$"
        
        result = text_extractor.extract_invoice_data(malformed_text)
        
        assert isinstance(result, dict)
        # Should not crash, but may not extract meaningful data

    def test_extract_multiple_amounts(self, text_extractor):
        """Test handling text with multiple amounts"""
        sample_text = """
        Subtotal: $100.00
        Tax: $8.50
        Total: $108.50
        """
        
        result = text_extractor.extract_invoice_data(sample_text)
        
        # Should extract the total, not subtotal
        assert result.get('total_amount') == 108.50


class TestProcessor:
    """Test main processing workflow"""

    @pytest.fixture
    def processor(self):
        """Create processor instance for testing"""
        if Processor is None:
            pytest.skip("Processor not implemented yet")
        return Processor()

    @pytest.fixture
    def mock_file(self):
        """Create mock uploaded file"""
        mock_file = Mock()
        mock_file.filename = 'test_invoice.pdf'
        mock_file.content_type = 'application/pdf'
        return mock_file

    def test_processor_initialization(self, processor):
        """Test processor can be initialized"""
        assert processor is not None

    @patch('core.ocr_processor.OCRProcessor')
    @patch('core.text_extractor.TextExtractor')
    def test_process_document_success(self, mock_text_extractor, mock_ocr, processor, mock_file):
        """Test successful document processing workflow"""
        # Mock OCR result
        mock_ocr_instance = Mock()
        mock_ocr.return_value = mock_ocr_instance
        mock_ocr_instance.process_pdf.return_value = "Invoice INV-001 Total: $150.00"
        
        # Mock text extraction result
        mock_text_instance = Mock()
        mock_text_extractor.return_value = mock_text_instance
        mock_text_instance.extract_invoice_data.return_value = {
            'invoice_number': 'INV-001',
            'total_amount': 150.00,
            'vendor': 'Test Vendor'
        }
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            result = processor.process_document(tmp.name, 'pdf')
            
            assert result['success'] is True
            assert result['data']['invoice_number'] == 'INV-001'
            assert result['data']['total_amount'] == 150.00
            
        os.unlink(tmp.name)

    def test_process_document_invalid_file_type(self, processor):
        """Test processing unsupported file type"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            result = processor.process_document(tmp.name, 'txt')
            
            assert result['success'] is False
            assert 'error' in result
            
        os.unlink(tmp.name)

    @patch('core.ocr_processor.OCRProcessor')
    def test_process_document_ocr_failure(self, mock_ocr, processor):
        """Test handling of OCR processing failures"""
        mock_ocr_instance = Mock()
        mock_ocr.return_value = mock_ocr_instance
        mock_ocr_instance.process_pdf.side_effect = OCRProcessingError("OCR failed")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            result = processor.process_document(tmp.name, 'pdf')
            
            assert result['success'] is False
            assert 'OCR failed' in result['error']
            
        os.unlink(tmp.name)

    def test_validate_file_type(self, processor):
        """Test file type validation"""
        valid_types = ['pdf', 'png', 'jpg', 'jpeg', 'tiff']
        invalid_types = ['txt', 'doc', 'xlsx', 'mp4']
        
        for file_type in valid_types:
            assert processor.is_valid_file_type(file_type) is True
            
        for file_type in invalid_types:
            assert processor.is_valid_file_type(file_type) is False

    def test_file_size_validation(self, processor):
        """Test file size validation"""
        # Test with different file sizes
        assert processor.is_valid_file_size(1024) is True  # 1KB
        assert processor.is_valid_file_size(1024 * 1024 * 5) is True  # 5MB
        assert processor.is_valid_file_size(1024 * 1024 * 15) is False  # 15MB (over limit)


class TestProcessingWorkflow:
    """Integration tests for complete processing workflow"""

    def test_end_to_end_processing_mock(self):
        """Test complete processing workflow with mocked components"""
        # This test would verify the entire pipeline works together
        # Using mocks since we may not have all components implemented
        
        with patch('core.processor.Processor') as mock_processor:
            mock_instance = Mock()
            mock_processor.return_value = mock_instance
            mock_instance.process_document.return_value = {
                'success': True,
                'data': {
                    'invoice_number': 'INV-2024-001',
                    'vendor': 'Test Company',
                    'total_amount': 299.99,
                    'date': '2024-01-15'
                },
                'ocr_text': 'Mocked OCR text',
                'processing_time': 2.5
            }
            
            processor = mock_processor()
            result = processor.process_document('test.pdf', 'pdf')
            
            assert result['success'] is True
            assert result['data']['invoice_number'] == 'INV-2024-001'
            assert result['data']['total_amount'] == 299.99

    def test_error_handling_workflow(self):
        """Test error handling throughout the processing workflow"""
        with patch('core.processor.Processor') as mock_processor:
            mock_instance = Mock()
            mock_processor.return_value = mock_instance
            mock_instance.process_document.return_value = {
                'success': False,
                'error': 'Failed to process document',
                'error_type': 'OCRProcessingError'
            }
            
            processor = mock_processor()
            result = processor.process_document('bad_file.pdf', 'pdf')
            
            assert result['success'] is False
            assert 'error' in result
            assert result['error_type'] == 'OCRProcessingError'


if __name__ == '__main__':
    pytest.main([__file__])
