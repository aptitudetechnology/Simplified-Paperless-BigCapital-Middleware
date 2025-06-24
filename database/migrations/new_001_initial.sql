# database/migrations/001_initial.sql

-- Core Documents Table with Enhanced Fields
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

    -- Enhanced OCR Results
    ocr_text TEXT,
    ocr_confidence REAL,
    ocr_confidence_scores TEXT, -- JSON: per-region confidence data
    ocr_metadata TEXT, -- JSON: OCR engine details, processing parameters
    ocr_regions TEXT, -- JSON: bounding boxes and text regions

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

    -- Enhanced Extraction Debug Information
    extraction_attempts TEXT, -- JSON: detailed extraction attempt logs
    extraction_patterns_tried TEXT, -- JSON: patterns/methods attempted per field
    field_extraction_reasons TEXT, -- JSON: per-field success/failure explanations
    extraction_debug_info TEXT, -- JSON: comprehensive debug information

    -- Enhanced Processing Status
    extraction_status VARCHAR(50) DEFAULT 'pending', -- 'complete', 'partial', 'needs_review', 'failed'
    overall_confidence_score REAL, -- Calculated overall extraction confidence
    requires_manual_review BOOLEAN DEFAULT FALSE,
    processing_flags TEXT, -- JSON: processing warnings and flags

    -- Manual Corrections Support
    manual_corrections TEXT, -- JSON: user-applied corrections
    correction_history TEXT, -- JSON: correction history with timestamps
    is_manually_verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(100), -- User who verified the document
    verified_at DATETIME,

    -- Enhanced File Management
    preview_image_path VARCHAR(500), -- Path to generated preview/thumbnail
    document_pages INTEGER DEFAULT 1, -- Number of pages in document
    preferred_preview_page INTEGER DEFAULT 1,

    -- Enhanced Processing Metadata
    processing_error TEXT,
    extraction_method VARCHAR(50),
    processing_duration REAL,
    retry_count INTEGER DEFAULT 0,
    detailed_processing_log TEXT, -- JSON: step-by-step processing timeline
    processing_stages_completed TEXT, -- JSON: completed processing stages
    last_manual_update DATETIME, -- When manual corrections were last made

    -- BigCapital integration
    bigcapital_id INTEGER,
    bigcapital_status VARCHAR(50),
    bigcapital_sync_date DATETIME,
    bigcapital_error TEXT,

    -- File integrity
    file_hash TEXT,
    hash_algorithm VARCHAR(20) DEFAULT 'SHA256',

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

-- Field-Level Extraction Details Table
CREATE TABLE IF NOT EXISTS document_field_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    field_type VARCHAR(50) NOT NULL, -- 'text', 'date', 'amount', 'number'
    
    -- Extraction attempts and methods
    extraction_method VARCHAR(100), -- 'regex', 'ml_model', 'heuristic', 'manual'
    patterns_tried TEXT, -- JSON: array of patterns attempted
    raw_matches TEXT, -- JSON: array of raw pattern matches
    
    -- Extraction results
    extracted_value TEXT,
    confidence_score REAL,
    extraction_status VARCHAR(50), -- 'extracted', 'partial', 'failed', 'manual'
    failure_reason TEXT,
    
    -- Manual corrections
    original_value TEXT,
    corrected_value TEXT,
    correction_reason TEXT,
    corrected_by VARCHAR(100),
    corrected_at DATETIME,
    
    -- Text context and positioning
    source_text_snippet TEXT, -- Context where value was found
    text_position_start INTEGER, -- Character position in OCR text
    text_position_end INTEGER,
    bounding_box TEXT, -- JSON: coordinates if available
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
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

    -- Enhanced processing statistics
    documents_requiring_review INTEGER DEFAULT 0,
    manual_corrections_applied INTEGER DEFAULT 0,
    avg_overall_confidence REAL,

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

-- Enhanced Document Processing Log
CREATE TABLE IF NOT EXISTS processing_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    job_id INTEGER,
    level VARCHAR(20) NOT NULL, -- 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    message TEXT NOT NULL,
    details TEXT, -- JSON additional details
    
    -- Enhanced logging fields
    processing_stage VARCHAR(100), -- 'ocr', 'extraction', 'validation', 'correction'
    field_name VARCHAR(100), -- Specific field being processed
    execution_time_ms INTEGER, -- Execution time for this step
    memory_usage_mb REAL, -- Memory usage at this step
    context_data TEXT, -- JSON: additional context for this log entry

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

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON documents(upload_date);
CREATE INDEX IF NOT EXISTS idx_documents_vendor ON documents(vendor_name);
CREATE INDEX IF NOT EXISTS idx_documents_invoice_date ON documents(invoice_date);
CREATE INDEX IF NOT EXISTS idx_documents_bigcapital_status ON documents(bigcapital_status);
CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);

-- Enhanced indexes for new fields
CREATE INDEX IF NOT EXISTS idx_documents_extraction_status ON documents(extraction_status);
CREATE INDEX IF NOT EXISTS idx_documents_requires_review ON documents(requires_manual_review);
CREATE INDEX IF NOT EXISTS idx_documents_verified ON documents(is_manually_verified);
CREATE INDEX IF NOT EXISTS idx_documents_confidence ON documents(overall_confidence_score);

CREATE INDEX IF NOT EXISTS idx_line_items_document ON document_line_items(document_id);
CREATE INDEX IF NOT EXISTS idx_line_items_product ON document_line_items(product_code);

-- Field extractions indexes
CREATE INDEX IF NOT EXISTS idx_field_extractions_document ON document_field_extractions(document_id);
CREATE INDEX IF NOT EXISTS idx_field_extractions_field ON document_field_extractions(field_name);
CREATE INDEX IF NOT EXISTS idx_field_extractions_status ON document_field_extractions(extraction_status);
CREATE INDEX IF NOT EXISTS idx_field_extractions_method ON document_field_extractions(extraction_method);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON processing_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_queued ON processing_jobs(queued_at);
CREATE INDEX IF NOT EXISTS idx_jobs_priority ON processing_jobs(priority DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_document ON processing_jobs(document_id);

CREATE INDEX IF NOT EXISTS idx_processing_stats_date ON processing_stats(date);

CREATE INDEX IF NOT EXISTS idx_sessions_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

-- Enhanced processing log indexes
CREATE INDEX IF NOT EXISTS idx_processing_log_document ON processing_log(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_log_job ON processing_log(job_id);
CREATE INDEX IF NOT EXISTS idx_processing_log_level ON processing_log(level);
CREATE INDEX IF NOT EXISTS idx_processing_log_created ON processing_log(created_at);
CREATE INDEX IF NOT EXISTS idx_processing_log_stage ON processing_log(processing_stage);
CREATE INDEX IF NOT EXISTS idx_processing_log_field ON processing_log(field_name);

CREATE INDEX IF NOT EXISTS idx_vendors_name ON vendors(normalized_name);
CREATE INDEX IF NOT EXISTS idx_vendors_bigcapital ON vendors(bigcapital_vendor_id);

-- Insert default configuration values
INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, description) VALUES
-- Original configuration
('ocr_confidence_threshold', '60', 'integer', 'Minimum OCR confidence threshold'),
('max_retry_attempts', '3', 'integer', 'Maximum retry attempts for failed jobs'),
('processing_timeout', '300', 'integer', 'Processing timeout in seconds'),
('bigcapital_api_url', '', 'string', 'BigCapital API base URL'),
('bigcapital_sync_enabled', 'false', 'boolean', 'Enable BigCapital synchronization'),
('auto_process_uploads', 'true', 'boolean', 'Automatically process uploaded documents'),
('cleanup_processed_files', 'false', 'boolean', 'Delete original files after successful processing'),
('max_file_age_days', '90', 'integer', 'Maximum age in days before archiving old files'),
('webhook_enabled', 'false', 'boolean', 'Enable webhook notifications'),
('webhook_url', '', 'string', 'Webhook notification URL'),

-- Enhanced configuration options
('detailed_logging_enabled', 'true', 'boolean', 'Enable detailed extraction logging'),
('ocr_region_confidence_threshold', '70', 'integer', 'Minimum confidence for OCR regions'),
('extraction_debug_mode', 'true', 'boolean', 'Enable extraction debugging information'),
('manual_review_confidence_threshold', '80', 'integer', 'Below this confidence, flag for manual review'),
('generate_preview_images', 'true', 'boolean', 'Generate preview images for documents'),
('preview_image_dpi', '150', 'integer', 'DPI for preview image generation'),
('max_extraction_patterns_per_field', '10', 'integer', 'Maximum patterns to try per field'),
('field_extraction_timeout', '30', 'integer', 'Timeout per field extraction in seconds'),
('enable_field_level_tracking', 'true', 'boolean', 'Enable granular field-level extraction tracking'),
('confidence_score_algorithm', 'weighted_average', 'string', 'Algorithm for calculating overall confidence'),
('auto_flag_low_confidence', 'true', 'boolean', 'Automatically flag low confidence extractions for review');

-- Create triggers for updated_at timestamps
CREATE TRIGGER IF NOT EXISTS update_documents_timestamp
    AFTER UPDATE ON documents
    FOR EACH ROW
    BEGIN
        UPDATE documents SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_field_extractions_timestamp
    AFTER UPDATE ON document_field_extractions
    FOR EACH ROW
    BEGIN
        UPDATE document_field_extractions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
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

-- Trigger to auto-flag documents for manual review based on confidence
CREATE TRIGGER IF NOT EXISTS auto_flag_low_confidence_documents
    AFTER UPDATE ON documents
    FOR EACH ROW
    WHEN NEW.overall_confidence_score IS NOT NULL 
    AND NEW.overall_confidence_score < (
        SELECT CAST(config_value AS REAL) / 100.0 
        FROM system_config 
        WHERE config_key = 'manual_review_confidence_threshold'
    )
    BEGIN
        UPDATE documents 
        SET requires_manual_review = TRUE,
            processing_flags = CASE 
                WHEN processing_flags IS NULL THEN '["low_confidence"]'
                ELSE JSON_INSERT(processing_flags, '$[#]', 'low_confidence')
            END
        WHERE id = NEW.id;
    END;

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

-- Enhanced Views for common queries

-- Enhanced document summary view
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
    END as duplicate_status,
    -- Field extraction summary
    (SELECT COUNT(*) FROM document_field_extractions dfe 
     WHERE dfe.document_id = d.id AND dfe.extraction_status = 'extracted') as fields_extracted,
    (SELECT COUNT(*) FROM document_field_extractions dfe 
     WHERE dfe.document_id = d.id AND dfe.extraction_status = 'failed') as fields_failed,
    (SELECT COUNT(*) FROM document_field_extractions dfe 
     WHERE dfe.document_id = d.id AND dfe.corrected_value IS NOT NULL) as fields_corrected,
    (SELECT COUNT(*) FROM document_field_extractions dfe 
     WHERE dfe.document_id = d.id) as total_tracked_fields
FROM documents d
LEFT JOIN document_line_items li ON d.id = li.document_id
LEFT JOIN vendors v ON LOWER(TRIM(d.vendor_name)) = v.normalized_name
GROUP BY d.id;

-- View for processing queue with enhanced information
CREATE VIEW IF NOT EXISTS processing_queue_view AS
SELECT
    pj.*,
    d.filename,
    d.original_filename,
    d.status as document_status,
    d.extraction_status,
    d.overall_confidence_score,
    d.requires_manual_review
FROM processing_jobs pj
JOIN documents d ON pj.document_id = d.id
WHERE pj.status IN ('pending', 'processing')
ORDER BY pj.priority DESC, pj.queued_at ASC;

-- View for documents needing review
CREATE VIEW IF NOT EXISTS documents_needing_review AS
SELECT 
    d.id,
    d.filename,
    d.original_filename,
    d.extraction_status,
    d.overall_confidence_score,
    d.requires_manual_review,
    d.processed_date,
    d.processing_flags,
    COUNT(dfe.id) as total_fields,
    COUNT(CASE WHEN dfe.extraction_status = 'failed' THEN 1 END) as failed_fields,
    COUNT(CASE WHEN dfe.confidence_score < 0.7 THEN 1 END) as low_confidence_fields,
    COUNT(CASE WHEN dfe.corrected_value IS NOT NULL THEN 1 END) as corrected_fields
FROM documents d
LEFT JOIN document_field_extractions dfe ON d.id = dfe.document_id
WHERE d.requires_manual_review = TRUE 
   OR d.overall_confidence_score < 0.8
   OR d.extraction_status IN ('partial', 'needs_review')
GROUP BY d.id
ORDER BY d.processed_date DESC;

-- View for extraction performance analysis
CREATE VIEW IF NOT EXISTS extraction_performance AS
SELECT 
    field_name,
    COUNT(*) as total_attempts,
    COUNT(CASE WHEN extraction_status = 'extracted' THEN 1 END) as successful_extractions,
    COUNT(CASE WHEN extraction_status = 'failed' THEN 1 END) as failed_extractions,
    ROUND(AVG(confidence_score), 3) as avg_confidence,
    extraction_method,
    COUNT(CASE WHEN corrected_value IS NOT NULL THEN 1 END) as manual_corrections,
    ROUND(
        CAST(COUNT(CASE WHEN extraction_status = 'extracted' THEN 1 END) AS REAL) / 
        COUNT(*) * 100, 2
    ) as success_rate
FROM document_field_extractions
GROUP BY field_name, extraction_method
ORDER BY field_name, successful_extractions DESC;

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

-- View for processing timeline and debugging
CREATE VIEW IF NOT EXISTS processing_timeline AS
SELECT 
    pl.document_id,
    d.filename,
    pl.processing_stage,
    pl.field_name,
    pl.level,
    pl.message,
    pl.execution_time_ms,
    pl.created_at,
    ROW_NUMBER() OVER (
        PARTITION BY pl.document_id 
        ORDER BY pl.created_at
    ) as step_number
FROM processing_log pl
JOIN documents d ON pl.document_id = d.id
ORDER BY pl.document_id, pl.created_at;

PRAGMA foreign_keys = ON;
