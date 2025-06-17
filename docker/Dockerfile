# Use official Python image with system dependencies
FROM python:3.11-slim

# install bash
RUN apt-get update && apt-get install -y bash

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy dependencies and source
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure scripts are executable
RUN chmod +x scripts/*.sh

# Create necessary folders
RUN mkdir -p uploads logs data

# Default command
CMD ["./scripts/run.sh"]

