-- Add file hash column to documents table
ALTER TABLE documents ADD COLUMN file_hash TEXT;

-- Create index for efficient duplicate detection
CREATE INDEX idx_documents_file_hash ON documents(file_hash);

-- Optional: Add hash algorithm type for future flexibility
ALTER TABLE documents ADD COLUMN hash_algorithm VARCHAR(20) DEFAULT 'SHA256';

-- Create a view for duplicate detection
CREATE VIEW IF NOT EXISTS duplicate_documents AS
SELECT 
    file_hash,
    hash_algorithm,
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(id) as document_ids,
    GROUP_CONCAT(original_filename) as filenames,
    MIN(upload_date) as first_upload,
    MAX(upload_date) as last_upload
FROM documents 
WHERE file_hash IS NOT NULL 
GROUP BY file_hash, hash_algorithm
HAVING COUNT(*) > 1;

-- Add a trigger to prevent duplicate file uploads (optional)
CREATE TRIGGER IF NOT EXISTS prevent_duplicate_files
    BEFORE INSERT ON documents
    FOR EACH ROW
    WHEN NEW.file_hash IS NOT NULL 
    AND EXISTS (SELECT 1 FROM documents WHERE file_hash = NEW.file_hash)
    BEGIN
        SELECT RAISE(ABORT, 'Duplicate file detected: ' || NEW.file_hash);
    END;

-- Alternative softer approach - mark duplicates instead of preventing
-- CREATE TRIGGER IF NOT EXISTS mark_duplicate_files
--     AFTER INSERT ON documents
--     FOR EACH ROW
--     WHEN NEW.file_hash IS NOT NULL
--     BEGIN
--         UPDATE documents 
--         SET status = 'duplicate',
--             processing_error = 'Duplicate of document ID: ' || 
--                 (SELECT MIN(id) FROM documents 
--                  WHERE file_hash = NEW.file_hash AND id != NEW.id)
--         WHERE id = NEW.id 
--         AND EXISTS (SELECT 1 FROM documents 
--                    WHERE file_hash = NEW.file_hash AND id != NEW.id);
--     END;

-- Update the document_summary view to include duplicate information
DROP VIEW IF EXISTS document_summary;
CREATE VIEW IF NOT EXISTS document_summary AS
SELECT 
    d.*,
    COUNT(li.id) as line_item_count,
    COALESCE(SUM(li.line_total), 0) as calculated_total,
    v.bigcapital_vendor_id,
    CASE 
        WHEN EXISTS (SELECT 1 FROM documents d2 
                    WHERE d2.file_hash = d.file_hash 
                    AND d2.id != d.id 
                    AND d.file_hash IS NOT NULL) 
        THEN 'duplicate' 
        ELSE 'unique' 
    END as duplicate_status
FROM documents d
LEFT JOIN document_line_items li ON d.id = li.document_id
LEFT JOIN vendors v ON LOWER(TRIM(d.vendor_name)) = v.normalized_name
GROUP BY d.id;
