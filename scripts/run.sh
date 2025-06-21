#!/bin/bash

echo "🚀 Starting Paperless-BigCapital Middleware..."

# Set Python path to include the project root
export PYTHONPATH=/home/runner/workspace:$PYTHONPATH

# Create necessary directories
#mkdir -p logs
#mkdir -p uploads
#mkdir -p data

echo "📁 Created necessary directories"

# Initialize database if needed
if [ ! -f "data/middleware.db" ]; then
    echo "🗄️  Initializing database..."
    # Add database initialization commands here if needed
fi

echo "🐍 Starting Python application..."

# Run the Flask application
python -m web.app
