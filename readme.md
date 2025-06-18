# Paperless-BigCapital Middleware - Phase 1

A minimal Flask application with Tesseract OCR for document processing, featuring automatic invoice data extraction and web-based management interface.

## Overview

This middleware processes uploaded invoices and receipts using OCR technology to extract structured data. Built with Flask, Tesseract OCR, and SQLite for simplicity and ease of deployment.

## Features

- 📄 **Document Upload**: Web interface for uploading PDF and image files
- 🔍 **OCR Processing**: Tesseract-powered text extraction from documents
- 📊 **Data Extraction**: Automatic parsing of invoice data (vendor, amount, date, etc.)
- 💾 **Database Storage**: SQLite database for document metadata and extracted data
- 🌐 **Web Dashboard**: View processed documents and extraction results
- 📈 **Statistics**: Processing metrics and success rates
- 🐳 **Docker Support**: Containerized deployment

## Directory Structure

```
paperless-bigcapital-middleware/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Centralized configuration management
│   └── config.ini.example   # Template configuration file
├── core/
│   ├── __init__.py
│   ├── ocr_processor.py     # Tesseract OCR processing
│   ├── text_extractor.py    # Extract invoice data from OCR text
│   └── processor.py         # Main processing logic
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
│   ├── templates/         # HTML templates
|   |   |-- 404.html
│   │   ├── base.html     # File upload interface
│   │   └── dashboard.html   # OCR results display
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
│   ├── test_ocr.py        # OCR processing tests
│   ├── test_database.py   # Database tests
│   └── test_web.py        # Web interface tests
├── uploads/               # Directory for uploaded files
├── sample_documents/      # Test PDFs/images for development
├── docker/
│   ├── Dockerfile         # Application Dockerfile
│   └── docker-compose.yml # Docker Compose configuration
├── scripts/
│   ├── init.sh           # Database initialization script
│   └── run.sh            # Application startup script
├── logs/                 # Application logs (created at runtime)
├── requirements.txt      # Python dependencies
├── config.ini           # Main configuration file
├── .env.example         # Environment variables template
├── .gitignore
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
   git clone <repository-url>
   cd paperless-bigcapital-middleware
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
   - Open your browser to `http://localhost:5000`
   - Upload documents and view results

### Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Access the application**
   - Web interface: `http://localhost:5000`

## Configuration

### Main Configuration (`config.ini`)

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
| GET | `/` | Upload interface |
| POST | `/upload` | Handle file uploads |
| GET | `/documents` | List processed documents |
| GET | `/document/<id>` | View document details |
| GET | `/api/stats` | Processing statistics (JSON) |

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
```

## Development

### Adding New File Types

1. Update `allowed_extensions` in `config.ini`
2. Modify `core/ocr_processor.py` to handle the new format
3. Add test cases in `tests/test_ocr.py`

### Improving Data Extraction

1. Edit regex patterns in `core/text_extractor.py`
2. Add new extraction rules for specific document types
3. Test with sample documents in `sample_documents/`

## Troubleshooting

### Common Issues

**OCR not working**
- Ensure Tesseract is installed and in PATH
- Check OCR language packs: `tesseract --list-langs`

**PDF processing fails**
- Verify Poppler is installed
- Check file permissions in uploads directory

**Database errors**
- Ensure `data/` directory exists and is writable
- Run database initialization script

### Logging

Application logs are stored in `logs/middleware.log`. Adjust logging level in `config.ini`:

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

## Roadmap

### Phase 2 (Planned)
- PostgreSQL database upgrade
- Enhanced data extraction algorithms
- Batch processing capabilities

### Phase 3 (Planned)
- BigCapital API integration
- Automated data synchronization
- Advanced document classification

### Phase 4 (Future)
- File system monitoring
- Machine learning-based extraction
- Multi-language OCR support

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Create an issue for bugs or feature requests
- Check the troubleshooting section for common problems
- Review the test suite for usage examples
