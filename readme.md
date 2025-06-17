Simplified Paperless-BigCapital Middleware - Phase 1 Instructions
Overview

Build a minimal Flask application with Tesseract OCR for document processing, SQLite database, and basic testing. This eliminates the complexity of Paperless-NGX integration while maintaining the existing directory structure.
Directory Structure (Maintain Existing)

paperless-bigcapital-middleware/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Centralized configuration management
│   └── config.ini.example   # Template configuration file
├── core/
│   ├── __init__.py
│   ├── ocr_processor.py     # NEW: Tesseract OCR processing
│   ├── text_extractor.py    # NEW: Extract invoice data from OCR text
│   └── processor.py         # Main processing logic (simplified)
├── database/
│   ├── __init__.py
│   ├── models.py           # SQLAlchemy models (SQLite compatible)
│   ├── connection.py       # Database connection management
│   └── migrations/         # Database schema files
│       └── 001_initial.sql
├── web/
│   ├── __init__.py
│   ├── app.py             # Flask application
│   ├── routes.py          # API endpoints and web routes
│   ├── templates/         # NEW: HTML templates
│   │   ├── index.html     # File upload interface
│   │   └── results.html   # OCR results display
│   └── static/            # Static web assets
│       ├── css/
│       │   └── style.css
│       └── js/
├── utils/
│   ├── __init__.py
│   ├── logger.py          # Logging configuration
│   └── exceptions.py      # Custom exception classes
├── tests/
│   ├── __init__.py
│   ├── conftest.py        # Pytest fixtures
│   ├── test_core.py       # Core functionality tests
│   ├── test_ocr.py        # NEW: OCR processing tests
│   ├── test_database.py   # Database tests
│   └── test_web.py        # Web interface tests
├── uploads/               # NEW: Directory for uploaded files
├── sample_documents/      # NEW: Test PDFs/images for development
├── docker/
│   ├── Dockerfile         # Simplified Dockerfile
│   └── docker-compose.yml # Minimal compose file
├── scripts/
│   ├── init.sh           # Database initialization script
│   └── run.sh            # Application startup script
├── logs/                 # Application logs (created at runtime)
├── requirements.txt      # Python dependencies
├── config.ini           # Main configuration file
├── .env.example         # Environment variables template
├── .gitignore
└── README.md

Phase 1 Requirements
Core Functionality

    File Upload Interface
        Simple web form to upload PDF/image files
        Display uploaded files list
        Show processing status
    OCR Processing
        Use Tesseract OCR to extract text from uploaded documents
        Support PDF and common image formats (PNG, JPG, TIFF)
        Store OCR results in database
    Text Extraction
        Parse OCR text to extract invoice/receipt data:
            Vendor/supplier name
            Invoice number
            Date
            Total amount
            Line items (if possible)
        Use regex patterns and text parsing techniques
    Database Storage
        SQLite database for simplicity
        Store document metadata and extracted data
        Track processing status and errors
    Web Interface
        Dashboard showing recent documents
        View OCR results and extracted data
        Simple statistics (documents processed, success rate)

Technical Requirements
Dependencies (requirements.txt)

Flask==2.3.3
SQLAlchemy==2.0.21
pytesseract==0.3.10
Pillow==10.0.1
PyPDF2==3.0.1
pdf2image==1.16.3
python-dotenv==1.0.0
pytest==7.4.2
pytest-flask==1.2.1

System Dependencies

    Tesseract OCR
    Poppler (for PDF processing)

Configuration (config.ini)

ini

[database]
type = sqlite
path = data/middleware.db

[ocr]
language = eng
confidence_threshold = 60
dpi = 300

[processing]
upload_folder = uploads
max_file_size = 10485760  # 10MB
allowed_extensions = pdf,png,jpg,jpeg,tiff

[web_interface]
host = 0.0.0.0
port = 5000
debug = false
secret_key = your-secret-key-here

[logging]
level = INFO
file = logs/middleware.log

Implementation Tasks
1. Database Models (database/models.py)

Create SQLAlchemy models for:

    Document (filename, upload_date, file_path, processing_status)
    ExtractedData (document_id, vendor_name, invoice_number, date, total_amount)
    ProcessingLog (document_id, step, status, error_message, timestamp)

2. OCR Processor (core/ocr_processor.py)

    Function to process PDF/images with Tesseract
    Handle different file formats
    Return OCR text with confidence scores

3. Text Extractor (core/text_extractor.py)

    Parse OCR text using regex patterns
    Extract structured data from unstructured text
    Handle common invoice/receipt formats

4. Web Routes (web/routes.py)

    GET / - Upload interface
    POST /upload - Handle file uploads
    GET /documents - List processed documents
    GET /document/<id> - View document details
    GET /api/stats - Processing statistics JSON

5. Templates (web/templates/)

    Simple HTML templates with basic styling
    File upload form
    Results display
    Document list

6. Tests (tests/)

    Unit tests for OCR processing
    Database model tests
    Web interface tests
    Integration tests with sample documents

Docker Setup
Dockerfile

dockerfile

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN mkdir -p uploads logs data

EXPOSE 5000
CMD ["python", "-m", "web.app"]

docker-compose.yml (Minimal)

yaml

version: '3.8'
services:
  middleware:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./uploads:/app/uploads
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - FLASK_ENV=development

Success Criteria

    File upload works - Can upload PDF/image files through web interface
    OCR processing works - Tesseract successfully extracts text from documents
    Data extraction works - Can parse basic invoice information from OCR text
    Database storage works - Data is properly stored in SQLite
    Web interface works - Can view uploaded documents and extracted data
    Tests pass - Basic test suite validates core functionality
    Docker builds and runs - Container starts without errors

Sample Test Documents

Include in sample_documents/:

    Simple invoice PDF
    Receipt image (PNG/JPG)
    Multi-page invoice PDF

Development Workflow

    Create minimal Flask app with file upload
    Add Tesseract OCR integration
    Implement basic data extraction
    Add database models and storage
    Create web interface for viewing results
    Add comprehensive tests
    Containerize with Docker

Next Phase Preview

Once Phase 1 is working:

    Phase 2: Upgrade to PostgreSQL
    Phase 3: Add BigCapital API integration (mock first)
    Phase 4: Add file watching/automated processing
    Phase 5: Consider Paperless-NGX integration or keep standalone

Key Points for Implementation

    Start with the simplest possible version that works
    Focus on one component at a time
    Use SQLite to avoid database complexity
    Test with real sample documents
    Keep error handling simple but present
    Make it easy to run locally for development
    Ensure Docker setup is minimal and reliable

