# core/__init__.py
"""
Core modules for simplified-paperless-bigcapital-middleware
"""

from .ocr_processor import OCRProcessor, extract_text_from_file

__all__ = ['OCRProcessor', 'extract_text_from_file']
