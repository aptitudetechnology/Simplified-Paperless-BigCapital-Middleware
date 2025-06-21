
"""
Processing module for document handling and BigCapital integration
"""

from .document_processor import DocumentProcessor
from .exceptions import (
    ProcessingError,
    ValidationError,
    OCRError,
    ExtractionError,
    BigCapitalError,
    DatabaseError,
    FileError,
    ConfigurationError,
    AuthenticationError,
    RateLimitError,
    NetworkError
)

__all__ = [
    'DocumentProcessor',
    'ProcessingError',
    'ValidationError',
    'OCRError',
    'ExtractionError',
    'BigCapitalError',
    'DatabaseError',
    'FileError',
    'ConfigurationError',
    'AuthenticationError',
    'RateLimitError',
    'NetworkError'
]
