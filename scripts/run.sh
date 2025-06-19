#!/bin/bash
echo "Run script is running..."
echo "✅ Flask Middleware container is running!"
echo "Starting Flask app..."
ls -poa
exec python web/app.py
