#!/bin/bash
echo "Run script is running..."
# You can add real app startup commands here later
echo "✅ Flask Middleware container is running!"
echo "Starting Flask app..."
exec python app.py
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

