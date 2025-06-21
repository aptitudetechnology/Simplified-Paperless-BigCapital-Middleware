"""
Custom exceptions for document processing
"""


class ProcessingError(Exception):
    """Base exception for document processing errors"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "PROCESSING_ERROR"
        self.details = details or {}
    
    def to_dict(self):
        """Convert exception to dictionary for API responses"""
        return {
            'error': self.error_code,
            'message': self.message,
            'details': self.details
        }


class ValidationError(ProcessingError):
    """Exception raised when document validation fails"""
    
    def __init__(self, message: str, field: str = None, value: str = None):
        super().__init__(message, "VALIDATION_ERROR")
        if field:
            self.details['field'] = field
        if value:
            self.details['value'] = value


class OCRError(ProcessingError):
    """Exception raised when OCR processing fails"""
    
    def __init__(self, message: str, file_path: str = None):
        super().__init__(message, "OCR_ERROR")
        if file_path:
            self.details['file_path'] = file_path


class ExtractionError(ProcessingError):
    """Exception raised when data extraction fails"""
    
    def __init__(self, message: str, extraction_type: str = None, file_path: str = None):
        super().__init__(message, "EXTRACTION_ERROR")
        if extraction_type:
            self.details['extraction_type'] = extraction_type
        if file_path:
            self.details['file_path'] = file_path


class BigCapitalError(ProcessingError):
    """Exception raised when BigCapital API integration fails"""
    
    def __init__(self, message: str, api_endpoint: str = None, status_code: int = None):
        super().__init__(message, "BIGCAPITAL_ERROR")
        if api_endpoint:
            self.details['api_endpoint'] = api_endpoint
        if status_code:
            self.details['status_code'] = status_code


class DatabaseError(ProcessingError):
    """Exception raised when database operations fail"""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(message, "DATABASE_ERROR")
        if operation:
            self.details['operation'] = operation


class FileError(ProcessingError):
    """Exception raised when file operations fail"""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        super().__init__(message, "FILE_ERROR")
        if file_path:
            self.details['file_path'] = file_path
        if operation:
            self.details['operation'] = operation


class ConfigurationError(ProcessingError):
    """Exception raised when configuration is invalid"""
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, "CONFIGURATION_ERROR")
        if config_key:
            self.details['config_key'] = config_key


class AuthenticationError(ProcessingError):
    """Exception raised when authentication fails"""
    
    def __init__(self, message: str, service: str = None):
        super().__init__(message, "AUTHENTICATION_ERROR")
        if service:
            self.details['service'] = service


class RateLimitError(ProcessingError):
    """Exception raised when rate limits are exceeded"""
    
    def __init__(self, message: str, service: str = None, retry_after: int = None):
        super().__init__(message, "RATE_LIMIT_ERROR")
        if service:
            self.details['service'] = service
        if retry_after:
            self.details['retry_after'] = retry_after


class NetworkError(ProcessingError):
    """Exception raised when network operations fail"""
    
    def __init__(self, message: str, url: str = None, timeout: bool = False):
        super().__init__(message, "NETWORK_ERROR")
        if url:
            self.details['url'] = url
        if timeout:
            self.details['timeout'] = timeout
