# Use official Python image with system dependencies
FROM python:3.11-slim

# Install bash
RUN apt-get update && apt-get install -y bash

# Install system dependencies including enhanced OCR support for paperless-ngx integration
RUN apt-get update && apt-get install -y \
    # Core OCR dependencies
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-script-latn \
    poppler-utils \
    # Image processing and manipulation
    imagemagick \
    ghostscript \
    # PDF processing
    qpdf \
    unpaper \
    # Additional language support (can be extended)
    tesseract-ocr-osd \
    # System utilities
    curl \
    wget \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configure ImageMagick policy for PDF processing (required for paperless-ngx compatibility)
RUN sed -i 's/<policy domain="coder" rights="none" pattern="PDF" \/>/<policy domain="coder" rights="read|write" pattern="PDF" \/>/g' /etc/ImageMagick-6/policy.xml

# Set work directory
WORKDIR /app

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# OCR Configuration Environment Variables (for paperless-ngx integration)
ENV PAPERLESS_OCR_LANGUAGE=eng+osd
ENV PAPERLESS_OCR_MODE=redo
ENV PAPERLESS_OCR_CLEAN=clean
ENV PAPERLESS_OCR_DESKEW=true
ENV PAPERLESS_OCR_ROTATE_PAGES=true
ENV PAPERLESS_OCR_PAGES=0
ENV PAPERLESS_OCR_IMAGE_DPI=300
ENV PAPERLESS_OCR_OUTPUT_TYPE=pdfa-2
ENV PAPERLESS_OCR_SKIP_ARCHIVE_FILE=never
ENV PAPERLESS_TIME_ZONE=Australia/Perth

# Performance and memory settings
ENV PAPERLESS_CONVERT_MEMORY_LIMIT=256MB
ENV PAPERLESS_TASK_WORKERS=1
ENV PAPERLESS_THREADS_PER_WORKER=1

# Copy dependencies and source
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure scripts are executable
RUN chmod +x scripts/*.sh

# Create necessary folders
RUN mkdir -p uploads logs data

# Create OCR processing directories
RUN mkdir -p ocr/temp ocr/processed ocr/failed

# Set proper permissions for OCR processing
RUN chmod 755 ocr ocr/temp ocr/processed ocr/failed

# Default command
CMD ["./scripts/run.sh"]
