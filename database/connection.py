"""
Database connection management for the middleware application
"""
import sqlite3
import os
from typing import Optional, Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self, config=None):
        """
        Initialize database manager

        Args:
            config: Configuration object with database settings
        """
        self.config = config
        self.db_path = self._get_db_path()
        self._ensure_db_directory()
        self._initialize_database()

    def _get_db_path(self) -> str:
        """Get database path from config or use default"""
        if self.config:
            return self.config.get('database', 'path', 'data/middleware.db')
        return 'data/middleware.db'

    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _initialize_database(self):
        """Initialize database with required tables"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Create documents table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        original_filename TEXT,
                        file_path TEXT NOT NULL,
                        file_size INTEGER,
                        content_type TEXT,
                        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_date TIMESTAMP,
                        status TEXT DEFAULT 'pending',
                        ocr_text TEXT,
                        extracted_data TEXT,
                        error_message TEXT,
                        vendor TEXT,
                        amount REAL,
                        extracted_text TEXT,
                        ai_response TEXT
                    )
                ''')

                # Create extracted_data table (might be redundant if documents table stores all)
                # Keeping it for now based on your initial structure, but consider if all data
                # can be normalized into the 'documents' table.
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS extracted_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id INTEGER,
                        vendor_name TEXT,
                        invoice_number TEXT,
                        invoice_date TEXT,
                        total_amount REAL,
                        currency TEXT,
                        line_items TEXT,
                        extraction_confidence REAL,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents (id)
                    )
                ''')

                # Create processing_stats table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processing_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        documents_processed INTEGER DEFAULT 0,
                        successful_extractions INTEGER DEFAULT 0,
                        failed_extractions INTEGER DEFAULT 0,
                        total_processing_time REAL DEFAULT 0.0
                    )
                ''')

                conn.commit()
                logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute a SELECT query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()

    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.rowcount

    def store_document(self, data: Dict[str, Any]) -> int:
        """
        Insert a new document record into the 'documents' table.
        This replaces the old 'insert_document' to be more generic.
        """
        # Filter data to only include columns present in the documents table
        # This list should ideally be maintained or fetched dynamically from schema
        allowed_columns = [
            'filename', 'original_filename', 'file_path', 'file_size',
            'content_type', 'upload_date', 'processed_date', 'status',
            'ocr_text', 'extracted_data', 'error_message', 'vendor',
            'amount', 'extracted_text', 'ai_response'
        ]
        
        insert_data = {k: v for k, v in data.items() if k in allowed_columns}

        columns = ', '.join(insert_data.keys())
        placeholders = ', '.join(['?' for _ in insert_data.values()])
        query = f"INSERT INTO documents ({columns}) VALUES ({placeholders})"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(insert_data.values()))
            conn.commit()
            return cursor.lastrowid

    def update_document(self, doc_id: int, **kwargs) -> bool:
        """Update document by ID with provided fields"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Build the SET clause dynamically
                set_clauses = []
                values = []

                for key, value in kwargs.items():
                    set_clauses.append(f"{key} = ?")
                    values.append(value)

                if not set_clauses:
                    return False

                # Add doc_id to values for WHERE clause
                values.append(doc_id)

                set_clause = ", ".join(set_clauses)
                query = f"UPDATE documents SET {set_clause} WHERE id = ?"

                cursor.execute(query, values)
                conn.commit()

                # Check if any rows were updated
                if cursor.rowcount > 0:
                    print(f"Updated document ID {doc_id} with {len(kwargs)} fields")
                    return True
                else:
                    print(f"No document found with ID {doc_id}")
                    return False

        except sqlite3.Error as e:
            print(f"Database error updating document {doc_id}: {e}")
            return False

    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
                row = cursor.fetchone()

                if row:
                    # conn.row_factory = sqlite3.Row makes rows behave like dicts
                    return dict(row)
                return None

        except sqlite3.Error as e:
            print(f"Database error getting document {doc_id}: {e}")
            return None

    def list_documents(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get list of documents"""
        query = "SELECT * FROM documents ORDER BY upload_date DESC LIMIT ? OFFSET ?"
        results = self.execute_query(query, (limit, offset))
        return [dict(row) for row in results]

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        stats = {}

        # Total documents
        result = self.execute_query("SELECT COUNT(*) as count FROM documents")
        stats['total_documents'] = result[0]['count'] if result else 0

        # Processed documents
        result = self.execute_query("SELECT COUNT(*) as count FROM documents WHERE status = 'completed'")
        stats['processed_documents'] = result[0]['count'] if result else 0

        # Failed documents
        result = self.execute_query("SELECT COUNT(*) as count FROM documents WHERE status = 'failed'")
        stats['failed_documents'] = result[0]['count'] if result else 0

        # Pending documents
        result = self.execute_query("SELECT COUNT(*) as count FROM documents WHERE status = 'pending'")
        stats['pending_documents'] = result[0]['count'] if result else 0

        return stats

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document by ID"""
        try:
            with self.get_connection() as conn:
                cursor =
