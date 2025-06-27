# ⚠️ **CRITICAL WARNING - READ BEFORE PROCEEDING** ⚠️

> ## 🚨 PRE-ALPHA SOFTWARE - NOT FUNCTIONAL 🚨
> 
> **THIS PROJECT IS CURRENTLY IN PRE-ALPHA DEVELOPMENT AND IS NOT YET FUNCTIONAL.**
> 
> ### ❌ DO NOT USE FOR:
> - Production environments
> - Business-critical data
> - Live financial systems
> - Any mission-critical applications
> 
> ### ⚠️ IMPORTANT DISCLAIMERS:
> - **DATA LOSS RISK**: This software may corrupt, lose, or mishandle your data
> - **NO RELIABILITY GUARANTEE**: Features may not work as expected or at all
> - **BREAKING CHANGES**: API and functionality will change without notice
> - **NO SUPPORT**: Limited or no support available during pre-alpha phase
> 
> ### 🔬 INTENDED FOR:
> - Development and testing purposes only
> - Contributors and early adopters willing to accept risks
> - Non-critical experimentation environments
> 
> **By using this software, you acknowledge and accept full responsibility for any potential data loss, system issues, or other consequences.**

---


# Paperless-BigCapital Middleware - Phase 1

A minimal Flask application with Tesseract OCR for document processing, featuring automatic invoice data extraction and web-based management interface.

## Overview

This middleware processes uploaded invoices and receipts using OCR technology to extract structured data. Built with a modular architecture using Flask, Tesseract OCR, and SQLite for simplicity and ease of deployment.

## Features

- 📄 **Document Upload**: Web interface for uploading PDF and image files
- 🔍 **OCR Processing**: Tesseract-powered text extraction from documents
- 📊 **Data Extraction**: Automatic parsing of invoice data (vendor, amount, date, etc.)
- 💾 **Database Storage**: SQLite database for document metadata and extracted data
- 🌐 **Web Dashboard**: View processed documents and extraction results
- 📈 **Statistics**: Processing metrics and success rates
- 🏗️ **Modular Architecture**: Clean separation of concerns for easy maintenance
- 🐳 **Docker Support**: Containerized deployment

## Directory Structure

```
paperless-bigcapital-middleware/
├── config/
│   ├── __init__.py
│   ├── settings.py              # Centralized configuration management
│   └── config.ini.example       # Template configuration file
├── core/
│   ├── __init__.py
│   ├── ocr_processor.py         # Tesseract OCR processing
│   ├── text_extractor.py        # Extract invoice data from OCR text
│   ├── processor.py             # Main processing logic
│   ├── bigcapital_client.py     # BigCapital integration (planned)
│   └── paperless_client.py      # Paperless-ngx integration (planned)
├── database/
│   ├── __init__.py
│   ├── models.py               # SQLAlchemy models (SQLite compatible)
│   ├── connection.py           # Database connection management
│   ├── create_tables.py        # Database table creation
│   ├── check_db.py            # Database verification utilities
│   └── migrations/            # Database schema files
│       ├── 001_initial.sql
│       └── filehash.sql
├── processing/
│   ├── __init__.py
│   ├── document_processor.py   # Document processing logic
│   └── exceptions.py          # Processing-specific exceptions
├── web/
│   ├── __init__.py
│   ├── app.py                 # Flask application
│   ├── legacy_routes.py       # Legacy route compatibility
│   ├── routes/                # Modular routing system
│   │   ├── __init__.py
│   │   ├── api_routes.py      # API endpoints
│   │   ├── web_routes.py      # Web interface routes
│   │   └── utils.py           # Route utilities
│   ├── templates/             # HTML templates
│   │   ├── base.html
│   │   ├── dashboard.html     # Main dashboard
│   │   ├── upload.html        # File upload interface
│   │   ├── documents.html     # Document listing
│   │   ├── document_detail.html # Document details view
│   │   ├── config.html        # Configuration interface (mock-up)
│   │   ├── 404.html
│   │   └── errors/            # Error templates
│   │       ├── 404.html
│   │       └── 500.html
│   └── static/                # Static web assets
│       ├── css/
│       │   └── style.css
│       └── js/
├── utils/
│   ├── __init__.py
│   ├── logger.py              # Logging configuration
│   └── exceptions.py          # Custom exception classes
├── tests/
│   ├── __init__.py
│   ├── test_core.py           # Core functionality tests
│   ├── test_ocr.py            # OCR processing tests
│   ├── test_database.py       # Database tests
│   ├── test_web.py            # Web interface tests
│   └── test_clients.py        # Client integration tests
├── docker/
│   ├── Dockerfile             # Application Dockerfile
│   └── docker-compose.yml     # Docker Compose configuration
├── scripts/
│   ├── init.sh               # Database initialization script
│   └── run.sh                # Application startup script
├── logs/                     # Application logs (created at runtime)
├── requirements.txt          # Python dependencies
├── config.ini.example        # Configuration template
├── .env.example             # Environment variables template
├── .gitignore
├── Makefile                 # Build and development commands
└── README.md
```

## Prerequisites

### System Dependencies

- Python 3.11+
- Tesseract OCR
- Poppler utilities (for PDF processing)

### Installation

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr poppler-utils
```

## Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/aptitudetechnology/simplified-paperless-bigcapital-middleware
   cd simplified-paperless-bigcapital-middleware
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the application**
   ```bash
   cp config.ini.example config.ini
   cp .env.example .env
   # Edit config.ini with your settings
   ```

5. **Initialize database**
   ```bash
   ./scripts/init.sh
   ```

6. **Run the application**
   ```bash
   ./scripts/run.sh
   # Or directly: python -m web.app
   ```

7. **Access the web interface**
   - Open your browser to http://localhost:5000
   - Upload documents and view results

### Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Access the application**
   - Web interface: http://localhost:5000

### Using Makefile

```bash
# Initialize the project
make init

# Run the application
make run

# Run tests
make test

# Clean up
make clean
```

## Configuration

### Main Configuration (config.ini)

```ini
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
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Main dashboard |
| GET | /upload | Upload interface |
| POST | /upload | Handle file uploads |
| GET | /documents | List processed documents |
| GET | /document/<id> | View document details |
| GET | /config | Configuration interface (mock-up) |
| GET | /api/stats | Processing statistics (JSON) |
| GET | /api/documents | List documents (JSON) |
| GET | /api/document/<id> | Get document data (JSON) |

## Data Extraction

The system automatically extracts the following information from documents:

- **Vendor/Supplier Name**: Company or individual issuing the invoice
- **Invoice Number**: Unique identifier for the document
- **Date**: Invoice or receipt date
- **Total Amount**: Final amount due or paid
- **Line Items**: Individual products/services (when detectable)

## Testing

Run the complete test suite:
```bash
pytest
```

Run specific test categories:
```bash
# OCR processing tests
pytest tests/test_ocr.py

# Database tests
pytest tests/test_database.py

# Web interface tests
pytest tests/test_web.py

# Client integration tests
pytest tests/test_clients.py
```

## Development

### Adding New File Types

1. Update `allowed_extensions` in config.ini
2. Modify `core/ocr_processor.py` to handle the new format
3. Add test cases in `tests/test_ocr.py`

### Improving Data Extraction

1. Edit regex patterns in `core/text_extractor.py`
2. Add new extraction rules for specific document types
3. Test with sample documents

### Adding New Routes

1. Add API routes to `web/routes/api_routes.py`
2. Add web routes to `web/routes/web_routes.py`
3. Shared utilities go in `web/routes/utils.py`

## Troubleshooting

### Common Issues

**OCR not working**
- Ensure Tesseract is installed and in PATH
- Check OCR language packs: `tesseract --list-langs`

**PDF processing fails**
- Verify Poppler is installed
- Check file permissions in uploads directory

**Database errors**
- Ensure data/ directory exists and is writable
- Run database initialization script: `./scripts/init.sh`

### Logging

Application logs are stored in `logs/middleware.log`. Adjust logging level in config.ini:

```ini
[logging]
level = DEBUG  # For detailed debugging
```

## Dependencies

### Python Packages

- **Flask 2.3.3**: Web framework
- **SQLAlchemy 2.0.21**: Database ORM
- **pytesseract 0.3.10**: Tesseract OCR wrapper
- **Pillow 10.0.1**: Image processing
- **PyPDF2 3.0.1**: PDF text extraction
- **pdf2image 1.16.3**: PDF to image conversion
- **python-dotenv 1.0.0**: Environment variable management
- **pytest 7.4.2**: Testing framework

# Roadmap

## Phase 1 (Current) ✅
- [x] Modular architecture implementation
- [x] Basic OCR processing and data extraction
- [x] SQLite database storage
- [x] Web dashboard and API endpoints
- [x] Docker deployment support
      
## Phase 1.1 (In Progess)
- [ ] **BigCapital API Integration**: Automatic invoice data synchronization
- [ ] **Paperless-ngx Integration**: Document retrieval and status updates
      
## Phase 2 (Core Integrations) 🔄

- [ ] **Redis + Celery Queue System**: Asynchronous document processing
- [ ] **Enhanced Error Handling**: Retry logic and failure recovery
- [ ] **Processing Status Tracking**: Real-time job status and progress indicators

## Phase 3 (Enhanced Processing) 📋
- [ ] **Improved Data Extraction**: Template-based extraction and confidence scoring
- [ ] **Batch Processing**: Handle multiple documents simultaneously via queue
- [ ] **Manual Review Interface**: Human validation for low-confidence extractions

## Phase 4 (Production Features) 🚀
- [ ] **PostgreSQL Support**: Optional database upgrade path
- [ ] **Authentication & Authorization**: Secure access controls
- [ ] **Monitoring & Metrics**: Processing analytics and system health
- [ ] **Advanced Document Classification**: Automatic document type detection
- [ ] **Webhook Support**: Event-driven notifications and integrations

## Phase 5 (Advanced Automation) 🤖
- [ ] **Workflow Automation**: Configurable processing pipelines
- [ ] **File System Monitoring**: Automatic processing of watched directories
- [ ] **Machine Learning**: AI-powered extraction improvements
- [ ] **Multi-language OCR**: Extended language support
- [ ] **Advanced Analytics**: Detailed processing insights and reporting
      
## Architecture Notes

The application follows a modular architecture with clear separation of concerns:

- **Core**: Business logic and processing
- **Web**: User interface and API endpoints (modular routing)
- **Database**: Data models and connection management
- **Processing**: Document processing workflows
- **Utils**: Shared utilities and logging
- **Config**: Centralized configuration management

This structure facilitates easy testing, maintenance, and future feature additions.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- Create an issue for bugs or feature requests
- Check the troubleshooting section for common problems
- Review the test suite for usage examples
