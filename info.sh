echo "--- Directory Structure ---"
ls -RF .

echo ""
echo "--- Relevant File Contents (First 5 Lines) ---"

# This command finds all regular files (not directories)
# It explicitly excludes common non-source directories and file types like binaries or logs.
find . -type f \
    -not -path "./.git/*" \
    -not -path "./__pycache__/*" \
    -not -path "./node_modules/*" \
    -not -path "./.venv/*" \
    -not -path "./logs/*" \
    -not -name "*.pyc" \
    -not -name "*.log" \
    -not -name "*.sqlite3" \
    -not -name "*.db" \
    -not -name "*.DS_Store" \
    -not -name "*.tar" \
    -not -name "*.zip" \
    -not -name "*.gz" \
    -not -name "*.rar" \
    -not -name "*.pdf" \
    -not -name "*.jpg" \
    -not -name "*.jpeg" \
    -not -name "*.png" \
    -not -name "*.gif" \
    -not -name "*.bmp" \
    -not -name "*.ico" \
    -not -name "*.svg" \
    -print0 | while IFS= read -r -d $'\0' file; do
    echo "=========================================="
    echo "FILE: $file"
    echo "=========================================="
    head -n 5 "$file" # This is the change: only output the first 5 lines
    echo "" # Add a newline for separation between file contents
done
