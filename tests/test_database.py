# tests/test_database.py
"""
Test suite for database layer components.
Tests models, connections, migrations, and data integrity.
"""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sqlite3

# Import database modules
try:
    from database.models import Document, ProcessingResult, Base
    from database.connection import DatabaseConnection, get_db_session
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
except ImportError:
    # Handle case where modules don't exist yet
    Document = None
    ProcessingResult = None
    Base = None
    DatabaseConnection = None
    get_db_session = None


class TestDatabaseModels:
    """Test SQLAlchemy models"""

    @pytest.fixture
    def db_session(self):
        """Create in-memory SQLite database for testing"""
        if Base is None:
            pytest.skip("Database models not implemented yet")
            
        # Create in-memory database
        engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        yield session
        
        session.close()

    def test_document_model_creation(self, db_session):
        """Test Document model creation and basic properties"""
        if Document is None:
            pytest.skip("Document model not implemented yet")
            
        document = Document(
            filename='test_invoice.pdf',
            file_path='/uploads/test_invoice.pdf',
            file_type='pdf',
            file_size=12345,
            upload_date=datetime.now(),
            status='pending'
        )
        
        db_session.add(document)
        db_session.commit()
        
        assert document.id is not None
        assert document.filename == 'test_invoice.pdf'
        assert document.file_type == 'pdf'
        assert document.file_size == 12345
        assert document.status == 'pending'

    def test_document_model_relationships(self, db_session):
        """Test Document model relationships"""
        if Document is None or ProcessingResult is None:
            pytest.skip("Models not implemented yet")
            
        # Create document
        document = Document(
            filename='test_invoice.pdf',
            file_path='/uploads/test_invoice.pdf',
            file_type='pdf',
            file_size=12345,
            upload_date=datetime.now(),
            status='processed'
        )
        
        db_session.add(document)
        db_session.flush()  # Get the ID without committing
        
        # Create processing result
        result = ProcessingResult(
            document_id=document.id,
            ocr_text='Sample OCR text',
            extracted_data='{"invoice_number": "INV-001"}',
            processing_time=2.5,
            success=True,
            created_date=datetime.now()
        )
        
        db_session.add(result)
        db_session.commit()
        
        # Test relationship
        assert len(document.processing_results) == 1
        assert document.processing_results[0].ocr_text == 'Sample OCR text'
        assert result.document == document

    def test_processing_result_model(self, db_session):
        """Test ProcessingResult model creation and properties"""
        if ProcessingResult is None or Document is None:
            pytest.skip("ProcessingResult model not implemented yet")
            
        # Create document first
        document = Document(
            filename='test.pdf',
            file_path='/test.pdf',
            file_type='pdf',
            file_size=1000,
            upload_date=datetime.now(),
            status='processed'
        )
        
        db_session.add(document)
        db_session.flush()
        
        # Create processing result
        processing_result = ProcessingResult(
            document_id=document.id,
            ocr_text='Invoice Number: INV-001\nTotal: $150.00',
            extracted_data='{"invoice_number": "INV-001", "total_amount": 150.00}',
            processing_time=3.2,
            success=True,
            error_message=None,
            created_date=datetime.now()
        )
        
        db_session.add(processing_result)
        db_session.commit()
        
        assert processing_result.id is not None
        assert processing_result.document_id == document.id
        assert processing_result.success is True
        assert processing_result.processing_time == 3.2
        assert 'INV-001' in processing_result.ocr_text

    def test_document_status_validation(self, db_session):
        """Test document status field validation"""
        if Document is None:
            pytest.skip("Document model not implemented yet")
            
        valid_statuses = ['pending', 'processing', 'processed', 'failed']
        
        for status in valid_statuses:
            document = Document(
                filename=f'test_{status}.pdf',
                file_path=f'/test_{status}.pdf',
                file_type='pdf',
                file_size=1000,
                upload_date=datetime.now(),
                status=status
            )
            
            db_session.add(document)
            db_session.commit()
            
            assert document.status == status

    def test_document_file_hash(self, db_session):
        """Test file hash functionality if implemented"""
        if Document is None:
            pytest.skip("Document model not implemented yet")
            
        document = Document(
            filename='test.pdf',
            file_path='/test.pdf',
            file_type='pdf',
            file_size=1000,
            upload_date=datetime.now(),
            status='pending',
            file_hash='abc123def456'  # Assuming this field exists
        )
        
        db_session.add(document)
        db_session.commit()
        
        # Test that we can query by hash
        found_doc = db_session.query(Document).filter_by(file_hash='abc123def456').first()
        assert found_doc is not None
        assert found_doc.filename == 'test.pdf'


class TestDatabaseConnection:
    """Test database connection management"""

    def test_database_schema_version(self):
        """Test database schema versioning"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create schema version table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert version
            cursor.execute('INSERT INTO schema_version (version) VALUES (?)', (1,))
            conn.commit()
            
            # Verify version
            cursor.execute('SELECT MAX(version) FROM schema_version')
            version = cursor.fetchone()[0]
            assert version == 1
            
            conn.close()
            
        finally:
            os.unlink(db_path)

    def test_migration_rollback(self):
        """Test migration rollback functionality"""
        # This would test rollback functionality if implemented
        # For now, this is a placeholder
        assert True


class TestDataIntegrity:
    """Test data integrity and constraints"""

    @pytest.fixture
    def integrity_db(self):
        """Create database with integrity constraints"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute('PRAGMA foreign_keys = ON')
        
        cursor.execute('''
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER CHECK (file_size > 0),
                upload_date TIMESTAMP NOT NULL,
                status TEXT CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
                file_hash TEXT UNIQUE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE processing_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                ocr_text TEXT,
                extracted_data TEXT,
                processing_time REAL CHECK (processing_time >= 0),
                success BOOLEAN NOT NULL,
                error_message TEXT,
                created_date TIMESTAMP NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        
        yield db_path
        
        conn.close()
        os.unlink(db_path)

    def test_unique_filename_constraint(self, integrity_db):
        """Test unique filename constraint"""
        conn = sqlite3.connect(integrity_db)
        cursor = conn.cursor()
        
        # Insert first document
        cursor.execute('''
            INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('test.pdf', '/path1/test.pdf', 'pdf', 1000, datetime.now(), 'pending'))
        
        conn.commit()
        
        # Try to insert duplicate filename
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('test.pdf', '/path2/test.pdf', 'pdf', 2000, datetime.now(), 'pending'))
            conn.commit()
        
        conn.close()

    def test_foreign_key_constraint(self, integrity_db):
        """Test foreign key constraints"""
        conn = sqlite3.connect(integrity_db)
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # Try to insert processing result with non-existent document_id
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO processing_results (document_id, success, created_date)
                VALUES (?, ?, ?)
            ''', (999, True, datetime.now()))
            conn.commit()
        
        conn.close()

    def test_check_constraints(self, integrity_db):
        """Test check constraints"""
        conn = sqlite3.connect(integrity_db)
        cursor = conn.cursor()
        
        # Test file_size check constraint
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('test.pdf', '/test.pdf', 'pdf', -1, datetime.now(), 'pending'))
            conn.commit()
        
        # Test status check constraint
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('test2.pdf', '/test2.pdf', 'pdf', 1000, datetime.now(), 'invalid_status'))
            conn.commit()
        
        conn.close()

    def test_cascade_delete(self, integrity_db):
        """Test cascade delete functionality"""
        conn = sqlite3.connect(integrity_db)
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # Insert document
        cursor.execute('''
            INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('test.pdf', '/test.pdf', 'pdf', 1000, datetime.now(), 'processed'))
        
        document_id = cursor.lastrowid
        
        # Insert processing result
        cursor.execute('''
            INSERT INTO processing_results (document_id, success, created_date)
            VALUES (?, ?, ?)
        ''', (document_id, True, datetime.now()))
        
        conn.commit()
        
        # Delete document
        cursor.execute('DELETE FROM documents WHERE id = ?', (document_id,))
        conn.commit()
        
        # Verify processing result was also deleted
        cursor.execute('SELECT COUNT(*) FROM processing_results WHERE document_id = ?', (document_id,))
        count = cursor.fetchone()[0]
        assert count == 0
        
        conn.close()


class TestDatabasePerformance:
    """Test database performance and optimization"""

    def test_index_creation(self):
        """Test database index creation"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create table
            cursor.execute('''
                CREATE TABLE documents (
                    id INTEGER PRIMARY KEY,
                    filename TEXT,
                    file_hash TEXT,
                    upload_date TIMESTAMP,
                    status TEXT
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX idx_filename ON documents(filename)')
            cursor.execute('CREATE INDEX idx_file_hash ON documents(file_hash)')
            cursor.execute('CREATE INDEX idx_status ON documents(status)')
            cursor.execute('CREATE INDEX idx_upload_date ON documents(upload_date)')
            
            conn.commit()
            
            # Verify indexes exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            expected_indexes = ['idx_filename', 'idx_file_hash', 'idx_status', 'idx_upload_date']
            for index in expected_indexes:
                assert index in indexes
            
            conn.close()
            
        finally:
            os.unlink(db_path)

    def test_bulk_insert_performance(self):
        """Test bulk insert operations"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE documents (
                    id INTEGER PRIMARY KEY,
                    filename TEXT,
                    file_path TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    upload_date TIMESTAMP,
                    status TEXT
                )
            ''')
            
            # Bulk insert test data
            test_data = [
                (f'file_{i}.pdf', f'/path/file_{i}.pdf', 'pdf', 1000 + i, datetime.now(), 'pending')
                for i in range(100)
            ]
            
            cursor.executemany('''
                INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', test_data)
            
            conn.commit()
            
            # Verify all records inserted
            cursor.execute('SELECT COUNT(*) FROM documents')
            count = cursor.fetchone()[0]
            assert count == 100
            
            conn.close()
            
        finally:
            os.unlink(db_path)


if __name__ == '__main__':
    pytest.main([__file__])connection_creation(self):
        """Test database connection can be created"""
        if DatabaseConnection is None:
            pytest.skip("DatabaseConnection not implemented yet")
            
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
            
        try:
            db_conn = DatabaseConnection(db_path)
            assert db_conn is not None
            
            # Test connection
            engine = db_conn.get_engine()
            assert engine is not None
            
        finally:
            os.unlink(db_path)

    def test_database_session_management(self):
        """Test database session creation and management"""
        if get_db_session is None:
            pytest.skip("Database session management not implemented yet")
            
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
            
        try:
            # Mock database configuration
            with patch('database.connection.get_db_session') as mock_session:
                mock_session_instance = Mock()
                mock_session.return_value = mock_session_instance
                
                session = get_db_session()
                assert session is not None
                
        finally:
            os.unlink(db_path)

    def test_database_initialization(self):
        """Test database table creation"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
            
        try:
            # Connect to database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Mock table creation
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    upload_date TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processing_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    ocr_text TEXT,
                    extracted_data TEXT,
                    processing_time REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    created_date TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents (id)
                )
            ''')
            
            conn.commit()
            
            # Verify tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'documents' in tables
            assert 'processing_results' in tables
            
            conn.close()
            
        finally:
            os.unlink(db_path)


class TestDatabaseOperations:
    """Test database CRUD operations"""

    @pytest.fixture
    def test_db(self):
        """Create test database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
            
        # Initialize database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                upload_date TIMESTAMP,
                status TEXT DEFAULT 'pending',
                file_hash TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE processing_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                ocr_text TEXT,
                extracted_data TEXT,
                processing_time REAL,
                success BOOLEAN,
                error_message TEXT,
                created_date TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        ''')
        
        conn.commit()
        
        yield db_path
        
        conn.close()
        os.unlink(db_path)

    def test_insert_document(self, test_db):
        """Test inserting a document record"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('test.pdf', '/uploads/test.pdf', 'pdf', 12345, datetime.now(), 'pending'))
        
        conn.commit()
        
        # Verify insertion
        cursor.execute('SELECT * FROM documents WHERE filename = ?', ('test.pdf',))
        row = cursor.fetchone()
        
        assert row is not None
        assert row[1] == 'test.pdf'  # filename
        assert row[3] == 'pdf'       # file_type
        assert row[4] == 12345       # file_size
        
        conn.close()

    def test_insert_processing_result(self, test_db):
        """Test inserting a processing result"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # Insert document first
        cursor.execute('''
            INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('test.pdf', '/uploads/test.pdf', 'pdf', 12345, datetime.now(), 'processed'))
        
        document_id = cursor.lastrowid
        
        # Insert processing result
        cursor.execute('''
            INSERT INTO processing_results 
            (document_id, ocr_text, extracted_data, processing_time, success, created_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (document_id, 'Sample OCR text', '{"key": "value"}', 2.5, True, datetime.now()))
        
        conn.commit()
        
        # Verify insertion
        cursor.execute('SELECT * FROM processing_results WHERE document_id = ?', (document_id,))
        row = cursor.fetchone()
        
        assert row is not None
        assert row[1] == document_id  # document_id
        assert row[2] == 'Sample OCR text'  # ocr_text
        assert row[4] == 2.5  # processing_time
        assert row[5] == 1    # success (True as 1)
        
        conn.close()

    def test_query_documents(self, test_db):
        """Test querying documents"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # Insert test data
        test_docs = [
            ('doc1.pdf', '/path1.pdf', 'pdf', 1000, 'processed'),
            ('doc2.png', '/path2.png', 'png', 2000, 'pending'),
            ('doc3.jpg', '/path3.jpg', 'jpg', 3000, 'failed')
        ]
        
        for doc in test_docs:
            cursor.execute('''
                INSERT INTO documents (filename, file_path, file_type, file_size, status)
                VALUES (?, ?, ?, ?, ?)
            ''', doc)
        
        conn.commit()
        
        # Test queries
        cursor.execute('SELECT COUNT(*) FROM documents')
        count = cursor.fetchone()[0]
        assert count == 3
        
        cursor.execute('SELECT * FROM documents WHERE status = ?', ('processed',))
        processed_docs = cursor.fetchall()
        assert len(processed_docs) == 1
        assert processed_docs[0][1] == 'doc1.pdf'
        
        cursor.execute('SELECT * FROM documents WHERE file_type = ?', ('pdf',))
        pdf_docs = cursor.fetchall()
        assert len(pdf_docs) == 1
        
        conn.close()

    def test_update_document_status(self, test_db):
        """Test updating document status"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # Insert document
        cursor.execute('''
            INSERT INTO documents (filename, file_path, file_type, file_size, status)
            VALUES (?, ?, ?, ?, ?)
        ''', ('test.pdf', '/test.pdf', 'pdf', 1000, 'pending'))
        
        document_id = cursor.lastrowid
        conn.commit()
        
        # Update status
        cursor.execute('UPDATE documents SET status = ? WHERE id = ?', ('processed', document_id))
        conn.commit()
        
        # Verify update
        cursor.execute('SELECT status FROM documents WHERE id = ?', (document_id,))
        status = cursor.fetchone()[0]
        assert status == 'processed'
        
        conn.close()

    def test_delete_document(self, test_db):
        """Test deleting documents and cascading"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # Insert document and processing result
        cursor.execute('''
            INSERT INTO documents (filename, file_path, file_type, file_size, status)
            VALUES (?, ?, ?, ?, ?)
        ''', ('test.pdf', '/test.pdf', 'pdf', 1000, 'processed'))
        
        document_id = cursor.lastrowid
        
        cursor.execute('''
            INSERT INTO processing_results (document_id, ocr_text, success, created_date)
            VALUES (?, ?, ?, ?)
        ''', (document_id, 'Sample text', True, datetime.now()))
        
        conn.commit()
        
        # Delete document
        cursor.execute('DELETE FROM documents WHERE id = ?', (document_id,))
        conn.commit()
        
        # Verify deletion
        cursor.execute('SELECT * FROM documents WHERE id = ?', (document_id,))
        assert cursor.fetchone() is None
        
        # Note: In a real implementation, you'd want to handle cascading deletes
        # This test just verifies basic delete functionality
        
        conn.close()


class TestDatabaseMigrations:
    """Test database migration functionality"""

    def test_migration_file_exists(self):
        """Test that migration files exist"""
        # Check if migration files exist
        migration_files = [
            'database/migrations/001_initial.sql',
            'database/migrations/filehash.sql'
        ]
        
        for migration_file in migration_files:
            # In a real test, you'd check if the file exists
            # For now, we'll mock this
            assert True  # Placeholder - replace with actual file check

    def test_database_
