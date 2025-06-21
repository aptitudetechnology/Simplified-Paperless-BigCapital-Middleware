# core/text_extractor.py
"""
Text extraction and invoice data processing for simplified-paperless-bigcapital-middleware
Handles extraction of structured data from invoices and documents
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json

logger = logging.getLogger(__name__)

class InvoiceDataExtractor:
    """
    Extract structured data from invoice text
    Handles various invoice formats and extracts key information
    """
    
    def __init__(self):
        """Initialize the invoice data extractor"""
        self.currency_patterns = {
            'USD': [r'\$', r'USD', r'US\$'],
            'EUR': [r'€', r'EUR', r'EURO'],
            'GBP': [r'£', r'GBP', r'POUND'],
            'AUD': [r'A\$', r'AUD', r'AU\$'],
        }
        
        # Common invoice field patterns
        self.patterns = {
            'invoice_number': [
                r'invoice\s*#?\s*:?\s*([A-Z0-9\-]+)',
                r'inv\s*#?\s*:?\s*([A-Z0-9\-]+)',
                r'number\s*:?\s*([A-Z0-9\-]+)',
            ],
            'date': [
                r'date\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                r'issued\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            ],
            'total': [
                r'total\s*:?\s*[\$€£]?(\d+(?:\.\d{2})?)',
                r'amount\s*due\s*:?\s*[\$€£]?(\d+(?:\.\d{2})?)',
                r'balance\s*:?\s*[\$€£]?(\d+(?:\.\d{2})?)',
            ],
            'tax': [
                r'tax\s*:?\s*[\$€£]?(\d+(?:\.\d{2})?)',
                r'vat\s*:?\s*[\$€£]?(\d+(?:\.\d{2})?)',
                r'gst\s*:?\s*[\$€£]?(\d+(?:\.\d{2})?)',
            ],
            'subtotal': [
                r'subtotal\s*:?\s*[\$€£]?(\d+(?:\.\d{2})?)',
                r'sub\s*total\s*:?\s*[\$€£]?(\d+(?:\.\d{2})?)',
            ],
        }
    
    def extract_invoice_data(self, text: str) -> Dict[str, Any]:
        """
        Extract structured data from invoice text
        
        Args:
            text: Raw text from invoice document
            
        Returns:
            Dictionary with extracted invoice data
        """
        if not text or not text.strip():
            return self._empty_result("No text provided")
        
        text_lower = text.lower()
        
        try:
            result = {
                'invoice_number': self._extract_invoice_number(text_lower),
                'date': self._extract_date(text_lower),
                'total_amount': self._extract_total(text_lower),
                'tax_amount': self._extract_tax(text_lower),
                'subtotal': self._extract_subtotal(text_lower),
                'currency': self._detect_currency(text),
                'line_items': self._extract_line_items(text),
                'vendor_info': self._extract_vendor_info(text),
                'customer_info': self._extract_customer_info(text),
                'confidence_score': 0.0,
                'raw_text': text[:500] + "..." if len(text) > 500 else text,  # Truncated for storage
                'extraction_timestamp': datetime.utcnow().isoformat(),
            }
            
            # Calculate confidence score
            result['confidence_score'] = self._calculate_confidence(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Invoice data extraction failed: {e}")
            return self._empty_result(f"Extraction error: {str(e)}")
    
    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number from text"""
        for pattern in self.patterns['invoice_number']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract invoice date from text"""
        for pattern in self.patterns['date']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                # Try to normalize the date format
                try:
                    # Handle various date formats
                    for fmt in ['%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y', '%m.%d.%Y', '%d.%m.%Y']:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            return parsed_date.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
                    return date_str  # Return as-is if parsing fails
                except:
                    return date_str
        return None
    
    def _extract_total(self, text: str) -> Optional[float]:
        """Extract total amount from text"""
        for pattern in self.patterns['total']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None
    
    def _extract_tax(self, text: str) -> Optional[float]:
        """Extract tax amount from text"""
        for pattern in self.patterns['tax']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None
    
    def _extract_subtotal(self, text: str) -> Optional[float]:
        """Extract subtotal from text"""
        for pattern in self.patterns['subtotal']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None
    
    def _detect_currency(self, text: str) -> str:
        """Detect currency from text"""
        for currency, patterns in self.currency_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return currency
        return 'USD'  # Default currency
    
    def _extract_line_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract line items from invoice (simplified implementation)"""
        line_items = []
        
        # Look for common line item patterns
        lines = text.split('\n')
        for line in lines:
            # Simple pattern for quantity, description, price
            pattern = r'(\d+)\s+(.+?)\s+[\$€£]?(\d+(?:\.\d{2})?)'
            match = re.search(pattern, line.strip())
            if match:
                try:
                    line_items.append({
                        'quantity': int(match.group(1)),
                        'description': match.group(2).strip(),
                        'unit_price': float(match.group(3)),
                        'total_price': int(match.group(1)) * float(match.group(3))
                    })
                except ValueError:
                    continue
        
        return line_items[:10]  # Limit to 10 items to avoid too much data
    
    def _extract_vendor_info(self, text: str) -> Dict[str, str]:
        """Extract vendor information (simplified)"""
        vendor_info = {}
        
        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            vendor_info['email'] = email_match.group()
        
        # Look for phone numbers
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            vendor_info['phone'] = phone_match.group()
        
        return vendor_info
    
    def _extract_customer_info(self, text: str) -> Dict[str, str]:
        """Extract customer information (simplified)"""
        # This is a placeholder - in a real implementation you'd have more sophisticated
        # parsing logic to distinguish between vendor and customer information
        return {}
    
    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score based on extracted data"""
        score = 0.0
        max_score = 7.0
        
        # Score based on what we successfully extracted
        if result.get('invoice_number'):
            score += 2.0
        if result.get('date'):
            score += 1.5
        if result.get('total_amount'):
            score += 2.0
        if result.get('tax_amount'):
            score += 0.5
        if result.get('subtotal'):
            score += 0.5
        if result.get('line_items'):
            score += 0.5
        
        return min(score / max_score, 1.0)
    
    def _empty_result(self, error_message: str = "") -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'invoice_number': None,
            'date': None,
            'total_amount': None,
            'tax_amount': None,
            'subtotal': None,
            'currency': 'USD',
            'line_items': [],
            'vendor_info': {},
            'customer_info': {},
            'confidence_score': 0.0,
            'raw_text': '',
            'extraction_timestamp': datetime.utcnow().isoformat(),
            'error': error_message if error_message else None,
        }
    
    def validate_extraction(self, result: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate extracted data and return validation results
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for required fields
        if not result.get('invoice_number'):
            errors.append("Invoice number not found")
        
        if not result.get('total_amount'):
            errors.append("Total amount not found")
        
        # Validate numeric fields
        total = result.get('total_amount')
        if total is not None and total < 0:
            errors.append("Total amount cannot be negative")
        
        # Check date format
        date_str = result.get('date')
        if date_str:
            try:
                datetime.fromisoformat(date_str)
            except:
                errors.append("Invalid date format")
        
        return len(errors) == 0, errors
    
    def get_extraction_summary(self, result: Dict[str, Any]) -> str:
        """Get a human-readable summary of the extraction results"""
        if result.get('error'):
            return f"Extraction failed: {result['error']}"
        
        summary_parts = []
        
        if result.get('invoice_number'):
            summary_parts.append(f"Invoice #{result['invoice_number']}")
        
        if result.get('date'):
            summary_parts.append(f"Date: {result['date']}")
        
        if result.get('total_amount'):
            currency = result.get('currency', 'USD')
            summary_parts.append(f"Total: {currency} {result['total_amount']:.2f}")
        
        confidence = result.get('confidence_score', 0) * 100
        summary_parts.append(f"Confidence: {confidence:.1f}%")
        
        return " | ".join(summary_parts) if summary_parts else "No data extracted"

# Convenience function for quick extraction
def extract_invoice_data(text: str) -> Dict[str, Any]:
    """
    Convenience function to extract invoice data from text
    
    Args:
        text: Raw text from invoice
        
    Returns:
        Extracted invoice data dictionary
    """
    extractor = InvoiceDataExtractor()
    return extractor.extract_invoice_data(text)
