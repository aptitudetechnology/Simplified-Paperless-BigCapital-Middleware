# database/migrations/001_initial.sql
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(100),
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_date DATETIME,
    status VARCHAR(50) DEFAULT 'pending',
    
    -- OCR Results
    ocr_text TEXT,
    ocr_confidence REAL,
    
    -- Extracted Data
    vendor_name VARCHAR(255),
    invoice_number VARCHAR(100),
    invoice_date DATETIME,
    total_amount REAL,
    currency VARCHAR(10),
    
    -- Processing metadata
    processing_error TEXT,
    extraction_method VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS processing_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    documents_processed INTEGER DEFAULT 0,
    successful_extractions INTEGER DEFAULT 0,
    failed_extractions INTEGER DEFAULT 0,
    avg_processing_time REAL
);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON documents(upload_date);
CREATE INDEX IF NOT EXISTS idx_processing_stats_date ON processing_stats(date);

# config.ini.example
[database]
type = sqlite
path = data/middleware.db

[ocr]
language = eng
confidence_threshold = 60
dpi = 300

[processing]
upload_folder = uploads
max_file_size = 10485760
allowed_extensions = pdf,png,jpg,jpeg,tiff

[web_interface]
host = 0.0.0.0
port = 5000
debug = false
secret_key = your-secret-key-change-in-production

[logging]
level = INFO
file = logs/middleware.log

# .env.example
# Environment variables for development
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///data/middleware.db

# scripts/init.sh
#!/bin/bash

# Paperless-BigCapital Middleware Initialization Script

echo "Initializing Paperless-BigCapital Middleware..."

# Create necessary directories
echo "Creating directories..."
mkdir -p data
mkdir -p uploads
mkdir -p logs
mkdir -p sample_documents

# Copy configuration files if they don't exist
if [ ! -f "config.ini" ]; then
    echo "Creating config.ini from template..."
    cp config.ini.example config.ini
fi

if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
fi

# Initialize database
echo "Initializing database..."
python3 -c "
from config.settings import Config
from database.connection import DatabaseManager
from database.models import Base

config = Config()
db_manager = DatabaseManager(config)
print('Database initialized successfully!')
"

# Set permissions
echo "Setting permissions..."
chmod 755 uploads
chmod 755 logs
chmod 755 data

echo "Initialization complete!"
echo ""
echo "Next steps:"
echo "1. Edit config.ini with your settings"
echo "2. Install dependencies: pip install -r requirements.txt"
echo "3. Run the application: ./scripts/run.sh"

# scripts/run.sh
#!/bin/bash

# Paperless-BigCapital Middleware Run Script

echo "Starting Paperless-BigCapital Middleware..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if config exists
if [ ! -f "config.ini" ]; then
    echo "Config file not found. Running initialization..."
    ./scripts/init.sh
fi

# Run the application
echo "Starting Flask application..."
python -m web.app

# docker/Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data uploads logs

# Set permissions
RUN chmod +x scripts/*.sh

# Initialize database
RUN python -c "from config.settings import Config; from database.connection import DatabaseManager; config = Config(); db_manager = DatabaseManager(config)"

# Expose port
EXPOSE 5000

# Run application
CMD ["python", "-m", "web.app"]

# docker/docker-compose.yml
version: '3.8'

services:
  paperless-bigcapital:
    build: 
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "5000:5000"
    volumes:
      - ../uploads:/app/uploads
      - ../data:/app/data
      - ../logs:/app/logs
      - ../config.ini:/app/config.ini
    environment:
      - FLASK_ENV=production
