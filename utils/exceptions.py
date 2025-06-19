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
