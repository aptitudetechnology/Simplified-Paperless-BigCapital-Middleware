# database/migrations/001_initial.sql

-- Core Documents Table
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
    vendor_address TEXT,
    vendor_tax_id VARCHAR(50),
    invoice_number VARCHAR(100),
    invoice_date DATETIME,
    due_date DATETIME,
    total_amount REAL,
    tax_amount REAL,
    subtotal_amount REAL,
    currency VARCHAR(10) DEFAULT 'USD',

    -- Processing metadata
    processing_error TEXT,
    extraction_method VARCHAR(50),
    processing_duration REAL,
    retry_count INTEGER DEFAULT 0,

    -- BigCapital integration
    bigcapital_id INTEGER,
    bigcapital_status VARCHAR(50),
    bigcapital_sync_date DATETIME,
    bigcapital_error TEXT,

    -- Audit fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Invoice Line Items Table
CREATE TABLE IF NOT EXISTS document_line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    line_number INTEGER NOT NULL,
    description TEXT,
    quantity REAL,
    unit_price REAL,
    line_total REAL,
    tax_rate REAL,
    tax_amount REAL,
    product_code VARCHAR(100),
    unit_of_measure VARCHAR(50),

    -- BigCapital mapping
    bigcapital_item_id INTEGER,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Processing Queue/Jobs Table
CREATE TABLE IF NOT EXISTS processing_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    job_type VARCHAR(50) NOT NULL, -- 'ocr', 'extraction', 'bigcapital_sync'
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    priority INTEGER DEFAULT 0,

    -- Job data
    job_data TEXT, -- JSON data for job parameters
    result_data TEXT, -- JSON data for job results
    error_message TEXT,

    -- Timing
    queued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    processing_duration REAL,

    -- Retry logic
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at DATETIME,

    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Processing Statistics
CREATE TABLE IF NOT EXISTS processing_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE DEFAULT (DATE('now')),
    documents_processed INTEGER DEFAULT 0,
    successful_extractions INTEGER DEFAULT 0,
    failed_extractions INTEGER DEFAULT 0,
    avg_processing_time REAL,
    avg_ocr_confidence REAL,
    total_file_size INTEGER DEFAULT 0,

    -- BigCapital sync stats
    bigcapital_syncs INTEGER DEFAULT 0,
    successful_syncs INTEGER DEFAULT 0,
    failed_syncs INTEGER DEFAULT 0,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(date)
);

-- Configuration Storage Table
CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    config_type VARCHAR(50) DEFAULT 'string', -- 'string', 'integer', 'float', 'boolean', 'json'
    description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User Sessions Table (for web interface)
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    session_data TEXT, -- JSON session data
    ip_address VARCHAR(45),
    user_agent TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL
);

-- Document Processing Log
CREATE TABLE IF NOT EXISTS processing_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    job_id INTEGER,
    level VARCHAR(20) NOT NULL, -- 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    message TEXT NOT NULL,
    details TEXT, -- JSON additional details

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES processing_jobs(id) ON DELETE CASCADE
);

-- Vendor Master Data
CREATE TABLE IF NOT EXISTS vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255), -- For matching similar vendor names
    address TEXT,
    tax_id VARCHAR(50),
    email VARCHAR(255),
    phone VARCHAR(50),

    -- BigCapital integration
    bigcapital_vendor_id INTEGER,

    -- Statistics
    document_count INTEGER DEFAULT 0,
    total_amount REAL DEFAULT 0.0,
    last_invoice_date DATETIME,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(normalized_name)
);

-- Add file hash column to documents table
ALTER TABLE documents ADD COLUMN file_hash TEXT;

-- Optional: Add hash algorithm type for future flexibility
ALTER TABLE documents ADD COLUMN hash_algorithm VARCHAR(20) DEFAULT 'SHA256';


-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON documents(upload_date);
CREATE INDEX IF NOT EXISTS idx_documents_vendor ON documents(vendor_name);
CREATE INDEX IF NOT EXISTS idx_documents_invoice_date ON documents(invoice_date);
CREATE INDEX IF NOT EXISTS idx_documents_bigcapital_status ON documents(bigcapital_status);
CREATE INDEX idx_documents_file_hash ON documents(file_hash); -- Index for efficient duplicate detection

CREATE INDEX IF NOT EXISTS idx_line_items_document ON document_line_items(document_id);
CREATE INDEX IF NOT EXISTS idx_line_items_product ON document_line_items(product_code);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON processing_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_queued ON processing_jobs(queued_at);
CREATE INDEX IF NOT EXISTS idx_jobs_priority ON processing_jobs(priority DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_document ON processing_jobs(document_id);

CREATE INDEX IF NOT EXISTS idx_processing_stats_date ON processing_stats(date);

CREATE INDEX IF NOT EXISTS idx_sessions_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_processing_log_document ON processing_log(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_log_job ON processing_log(job_id);
CREATE INDEX IF NOT EXISTS idx_processing_log_level ON processing_log(level);
CREATE INDEX IF NOT EXISTS idx_processing_log_created ON processing_log(created_at);

CREATE INDEX IF NOT EXISTS idx_vendors_name ON vendors(normalized_name);
CREATE INDEX IF NOT EXISTS idx_vendors_bigcapital ON vendors(bigcapital_vendor_id);

-- Insert default configuration values
INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, description) VALUES
('ocr_confidence_threshold', '60', 'integer', 'Minimum OCR confidence threshold'),
('max_retry_attempts', '3', 'integer', 'Maximum retry attempts for failed jobs'),
('processing_timeout', '300', 'integer', 'Processing timeout in seconds'),
('bigcapital_api_url', '', 'string', 'BigCapital API base URL'),
('bigcapital_sync_enabled', 'false', 'boolean', 'Enable BigCapital synchronization'),
('auto_process_uploads', 'true', 'boolean', 'Automatically process uploaded documents'),
('cleanup_processed_files', 'false', 'boolean', 'Delete original files after successful processing'),
('max_file_age_days', '90', 'integer', 'Maximum age in days before archiving old files'),
('webhook_enabled', 'false', 'boolean', 'Enable webhook notifications'),
('webhook_url', '', 'string', 'Webhook notification URL');

-- Create triggers for updated_at timestamps
CREATE TRIGGER IF NOT EXISTS update_documents_timestamp
    AFTER UPDATE ON documents
    FOR EACH ROW
    BEGIN
        UPDATE documents SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_vendors_timestamp
    AFTER UPDATE ON vendors
    FOR EACH ROW
    BEGIN
        UPDATE vendors SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_config_timestamp
    AFTER UPDATE ON system_config
    FOR EACH ROW
    BEGIN
        UPDATE system_config SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Create triggers for vendor statistics
CREATE TRIGGER IF NOT EXISTS update_vendor_stats_on_insert
    AFTER INSERT ON documents
    FOR EACH ROW
    WHEN NEW.vendor_name IS NOT NULL
    BEGIN
        INSERT OR IGNORE INTO vendors (name, normalized_name)
        VALUES (NEW.vendor_name, LOWER(TRIM(NEW.vendor_name)));

        UPDATE vendors
        SET document_count = document_count + 1,
            total_amount = total_amount + COALESCE(NEW.total_amount, 0),
            last_invoice_date = CASE
                WHEN NEW.invoice_date > last_invoice_date OR last_invoice_date IS NULL
                THEN NEW.invoice_date
                ELSE last_invoice_date
            END
        WHERE normalized_name = LOWER(TRIM(NEW.vendor_name));
    END;

-- Add a trigger to prevent duplicate file uploads (optional - commented out to prefer the 'mark_duplicate_files' approach)
-- CREATE TRIGGER IF NOT EXISTS prevent_duplicate_files
--     BEFORE INSERT ON documents
--     FOR EACH ROW
--     WHEN NEW.file_hash IS NOT NULL
--     AND EXISTS (SELECT 1 FROM documents WHERE file_hash = NEW.file_hash)
--     BEGIN
--         SELECT RAISE(ABORT, 'Duplicate file detected: ' || NEW.file_hash);
--     END;

-- Alternative softer approach - mark duplicates instead of preventing
CREATE TRIGGER IF NOT EXISTS mark_duplicate_files
    AFTER INSERT ON documents
    FOR EACH ROW
    WHEN NEW.file_hash IS NOT NULL
    BEGIN
        UPDATE documents
        SET status = 'duplicate',
            processing_error = 'Duplicate of document ID: ' ||
                (SELECT MIN(id) FROM documents
                 WHERE file_hash = NEW.file_hash AND id != NEW.id)
        WHERE id = NEW.id
        AND EXISTS (SELECT 1 FROM documents
                    WHERE file_hash = NEW.file_hash AND id != NEW.id);
    END;


-- Views for common queries

-- Drop the old view before creating the new one to ensure updates
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


CREATE VIEW IF NOT EXISTS processing_queue_view AS
SELECT
    pj.*,
    d.filename,
    d.original_filename,
    d.status as document_status
FROM processing_jobs pj
JOIN documents d ON pj.document_id = d.id
WHERE pj.status IN ('pending', 'processing')
ORDER BY pj.priority DESC, pj.queued_at ASC;


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

-- Sample data for testing (optional)
-- INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
-- ('test_mode', 'true', 'boolean', 'Enable test mode for development');

PRAGMA foreign_keys = ON;
