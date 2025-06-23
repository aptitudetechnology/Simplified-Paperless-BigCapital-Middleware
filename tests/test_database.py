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
    from sqlalchemy.exc import IntegrityError # Import this for SQLAlchemy integrity errors
except ImportError:
    # Handle case where modules don't exist yet (e.g., during initial setup)
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
            pytest.skip("Database models (Document, ProcessingResult, Base) not implemented yet or not importable.")

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
            pytest.skip("Document model not implemented yet or not importable.")

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
            pytest.skip("Document or ProcessingResult models not implemented yet or not importable.")

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
            pytest.skip("ProcessingResult or Document models not implemented yet or not importable.")

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
            pytest.skip("Document model not implemented yet or not importable.")

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

        # Test invalid status (this assumes your Document model has a check constraint or validation)
        # If your SQLAlchemy model does not enforce this at the ORM level (e.g., via Enum),
        # this specific test might not raise IntegrityError here, but later at the DB integrity level.
        # However, for a robust model, such validation should ideally happen before commit.
        with pytest.raises(IntegrityError): # Using SQLAlchemy's IntegrityError
            invalid_document = Document(
                filename='test_invalid.pdf',
                file_path='/test_invalid.pdf',
                file_type='pdf',
                file_size=1000,
                upload_date=datetime.now(),
                status='non_existent_status' # This should trigger an error
            )
            db_session.add(invalid_document)
            db_session.commit() # This commit should raise the error for invalid status

    def test_document_file_hash(self, db_session):
        """Test file hash functionality if implemented"""
        if Document is None:
            pytest.skip("Document model not implemented yet or not importable.")

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

        # Test unique file_hash constraint (if applicable in your model)
        with pytest.raises(IntegrityError):
            duplicate_hash_doc = Document(
                filename='test2.pdf',
                file_path='/test2.pdf',
                file_type='pdf',
                file_size=1001,
                upload_date=datetime.now(),
                status='pending',
                file_hash='abc123def456' # Same hash as above, should cause a unique constraint violation
            )
            db_session.add(duplicate_hash_doc)
            db_session.commit()


class TestDatabaseConnection:
    """Test database connection management"""

    def test_connection_creation(self):
        """Test database connection can be created"""
        if DatabaseConnection is None:
            pytest.skip("DatabaseConnection not implemented yet or not importable.")

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
        if get_db_session is None or Base is None:
            pytest.skip("Database session management or Base not implemented yet or not importable.")

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            # Mock the engine that get_db_session would use
            mock_engine = create_engine(f'sqlite:///{db_path}', echo=False)
            Base.metadata.create_all(mock_engine) # Ensure tables are created for the mock engine

            # Patch the DatabaseConnection.engine to use our mock engine for testing purposes
            with patch('database.connection.DatabaseConnection.engine', new=mock_engine):
                session = get_db_session()
                assert session is not None
                # Verify the session is usable (e.g., by performing a simple query)
                if Document: # Only if Document model is available
                    session.query(Document).count()
                session.close()

        finally:
            os.unlink(db_path)

    def test_database_initialization(self):
        """Test database table creation using SQLAlchemy Base.metadata"""
        if Base is None:
            pytest.skip("Base (SQLAlchemy declarative base) not implemented yet or not importable.")

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            engine = create_engine(f'sqlite:///{db_path}')
            # This is the standard way to create all tables defined in Base.metadata
            Base.metadata.create_all(engine)

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Verify tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            # Assuming your Base.metadata includes Document and ProcessingResult tables
            expected_tables = []
            if Document:
                expected_tables.append(Document.__tablename__)
            if ProcessingResult:
                expected_tables.append(ProcessingResult.__tablename__)

            for table_name in expected_tables:
                assert table_name in tables

            conn.close()

        finally:
            os.unlink(db_path)


    def test_database_schema_version(self):
        """Test database schema versioning basic setup"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create schema version table (simplified for test)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Insert a version
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
        """Placeholder for migration rollback functionality test."""
        pytest.skip("Migration rollback functionality is not yet implemented or tested.")
        # This test would require a functional migration system to test rollbacks.


class TestDataIntegrity:
    """Test data integrity and constraints using raw SQLite for strict control"""

    @pytest.fixture
    def integrity_db(self):
        """Create database with integrity constraints for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Enable foreign key constraints in SQLite
        cursor.execute('PRAGMA foreign_keys = ON')

        # Define schema with constraints
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
            conn.commit() # The commit should trigger the IntegrityError

        conn.close()

    def test_foreign_key_constraint(self, integrity_db):
        """Test foreign key constraints"""
        conn = sqlite3.connect(integrity_db)
        cursor = conn.cursor()

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
        """Test check constraints (file_size, status)"""
        conn = sqlite3.connect(integrity_db)
        cursor = conn.cursor()

        # Test file_size check constraint (file_size > 0)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('test_size.pdf', '/test_size.pdf', 'pdf', 0, datetime.now(), 'pending')) # file_size = 0
            conn.commit()

        # Test status check constraint (status IN ('pending', 'processing', 'processed', 'failed'))
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('test_invalid_status.pdf', '/test_invalid_status.pdf', 'pdf', 1000, datetime.now(), 'invalid_status'))
            conn.commit()

        conn.close()

    def test_cascade_delete(self, integrity_db):
        """Test cascade delete functionality when a parent document is deleted"""
        conn = sqlite3.connect(integrity_db)
        cursor = conn.cursor()

        cursor.execute('PRAGMA foreign_keys = ON')

        # Insert document
        cursor.execute('''
            INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('test_cascade.pdf', '/test_cascade.pdf', 'pdf', 1000, datetime.now(), 'processed'))

        document_id = cursor.lastrowid

        # Insert processing result linked to the document
        cursor.execute('''
            INSERT INTO processing_results (document_id, success, created_date)
            VALUES (?, ?, ?)
        ''', (document_id, True, datetime.now()))

        conn.commit()

        # Verify initial state
        cursor.execute('SELECT COUNT(*) FROM documents WHERE id = ?', (document_id,))
        assert cursor.fetchone()[0] == 1
        cursor.execute('SELECT COUNT(*) FROM processing_results WHERE document_id = ?', (document_id,))
        assert cursor.fetchone()[0] == 1

        # Delete the parent document
        cursor.execute('DELETE FROM documents WHERE id = ?', (document_id,))
        conn.commit()

        # Verify document is deleted
        cursor.execute('SELECT * FROM documents WHERE id = ?', (document_id,))
        assert cursor.fetchone() is None

        # Verify processing result was also deleted due to CASCADE
        cursor.execute('SELECT COUNT(*) FROM processing_results WHERE document_id = ?', (document_id,))
        count = cursor.fetchone()[0]
        assert count == 0

        conn.close()


class TestDatabasePerformance:
    """Test database performance and optimization (e.g., indexing, bulk operations)"""

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

            # Verify indexes exist by querying sqlite_master
            # We filter by tbl_name to ensure indexes belong to 'documents' table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='documents'")
            indexes = [row[0] for row in cursor.fetchall()]

            expected_indexes = ['idx_filename', 'idx_file_hash', 'idx_status', 'idx_upload_date']
            for index in expected_indexes:
                assert index in indexes

            conn.close()

        finally:
            os.unlink(db_path)

    def test_bulk_insert_performance(self):
        """Test bulk insert operations using executemany"""
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

            # Prepare a list of data for bulk insertion
            num_records = 100
            test_data = [
                (f'file_{i}.pdf', f'/path/file_{i}.pdf', 'pdf', 1000 + i, datetime.now(), 'pending')
                for i in range(num_records)
            ]

            # Use executemany for bulk insert
            cursor.executemany('''
                INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', test_data)

            conn.commit()

            # Verify all records inserted
            cursor.execute('SELECT COUNT(*) FROM documents')
            count = cursor.fetchone()[0]
            assert count == num_records

            conn.close()

        finally:
            os.unlink(db_path)


class TestDatabaseOperations:
    """Test database CRUD operations using raw SQLite for basic functionality"""

    @pytest.fixture
    def test_db(self):
        """Create a temporary SQLite database for operations testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Enable foreign key constraints for cascade delete to work
        cursor.execute('PRAGMA foreign_keys = ON')

        cursor.execute('''
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                upload_date TIMESTAMP,
                status TEXT DEFAULT 'pending',
                file_hash TEXT UNIQUE
            )
        ''')

        cursor.execute('''
            CREATE TABLE processing_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                ocr_text TEXT,
                extracted_data TEXT,
                processing_time REAL,
                success BOOLEAN,
                error_message TEXT,
                created_date TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
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
        ''', ('test_insert_doc.pdf', '/uploads/test_insert_doc.pdf', 'pdf', 12345, datetime.now(), 'pending'))

        conn.commit()

        # Verify insertion
        cursor.execute('SELECT * FROM documents WHERE filename = ?', ('test_insert_doc.pdf',))
        row = cursor.fetchone()

        assert row is not None
        assert row[1] == 'test_insert_doc.pdf'  # filename
        assert row[3] == 'pdf'       # file_type
        assert row[4] == 12345       # file_size

        conn.close()

    def test_insert_processing_result(self, test_db):
        """Test inserting a processing result, linked to a document"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Insert a parent document first
        cursor.execute('''
            INSERT INTO documents (filename, file_path, file_type, file_size, upload_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('parent_doc.pdf', '/uploads/parent_doc.pdf', 'pdf', 12345, datetime.now(), 'processed'))

        document_id = cursor.lastrowid # Get the ID of the newly inserted document

        # Insert processing result linked to the parent document
        cursor.execute('''
            INSERT INTO processing_results
            (document_id, ocr_text, extracted_data, processing_time, success, created_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (document_id, 'Sample OCR text for parent', '{"key": "value"}', 2.5, True, datetime.now()))

        conn.commit()

        # Verify insertion
        cursor.execute('SELECT * FROM processing_results WHERE document_id = ?', (document_id,))
        row = cursor.fetchone()

        assert row is not None
        assert row[1] == document_id        # document_id
        assert row[2] == 'Sample OCR text for parent'  # ocr_text
        assert row[4] == 2.5        # processing_time
        assert row[5] == 1          # success (True is stored as 1 in SQLite BOOLEAN)

        conn.close()

    def test_query_documents(self, test_db):
        """Test querying documents based on criteria"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Insert test data with varying statuses and types
        test_docs = [
            ('doc1_processed.pdf', '/path1.pdf', 'pdf', 1000, 'processed', datetime.now()),
            ('doc2_pending.png', '/path2.png', 'png', 2000, 'pending', datetime.now()),
            ('doc3_failed.jpg', '/path3.jpg', 'jpg', 3000, 'failed', datetime.now()),
            ('doc4_pending.pdf', '/path4.pdf', 'pdf', 1500, 'pending', datetime.now())
        ]

        cursor.executemany('''
            INSERT INTO documents (filename, file_path, file_type, file_size, status, upload_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', test_docs)

        conn.commit()

        # Test total count
        cursor.execute('SELECT COUNT(*) FROM documents')
        count = cursor.fetchone()[0]
        assert count == 4

        # Test query by status
        cursor.execute('SELECT filename FROM documents WHERE status = ?', ('processed',))
        processed_filenames = [row[0] for row in cursor.fetchall()]
        assert len(processed_filenames) == 1
        assert 'doc1_processed.pdf' in processed_filenames

        # Test query by file_type
        cursor.execute('SELECT filename FROM documents WHERE file_type = ?', ('pdf',))
        pdf_filenames = [row[0] for row in cursor.fetchall()]
        assert len(pdf_filenames) == 2
        assert 'doc1_processed.pdf' in pdf_filenames
        assert 'doc4_pending.pdf' in pdf_filenames

        conn.close()

    def test_update_document_status(self, test_db):
        """Test updating a document's status"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Insert a document with 'pending' status
        cursor.execute('''
            INSERT INTO documents (filename, file_path, file_type, file_size, status, upload_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('doc_to_update.pdf', '/test_update.pdf', 'pdf', 1000, 'pending', datetime.now()))

        document_id = cursor.lastrowid
        conn.commit()

        # Update its status to 'processed'
        cursor.execute('UPDATE documents SET status = ? WHERE id = ?', ('processed', document_id))
        conn.commit()

        # Verify the update
        cursor.execute('SELECT status FROM documents WHERE id = ?', (document_id,))
        status = cursor.fetchone()[0]
        assert status == 'processed'

        conn.close()

    def test_delete_document(self, test_db):
        """Test deleting documents and verify cascade deletion of related processing results"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Insert a document
        cursor.execute('''
            INSERT INTO documents (filename, file_path, file_type, file_size, status, upload_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('doc_to_delete.pdf', '/test_delete.pdf', 'pdf', 1000, 'processed', datetime.now()))

        document_id = cursor.lastrowid

        # Insert a processing result linked to this document
        cursor.execute('''
            INSERT INTO processing_results (document_id, ocr_text, success, created_date)
            VALUES (?, ?, ?, ?)
        ''', (document_id, 'Text from deleted doc', True, datetime.now()))

        conn.commit()

        # Verify existence before deletion
        cursor.execute('SELECT COUNT(*) FROM documents WHERE id = ?', (document_id,))
        assert cursor.fetchone()[0] == 1
        cursor.execute('SELECT COUNT(*) FROM processing_results WHERE document_id = ?', (document_id,))
        assert cursor.fetchone()[0] == 1

        # Delete the document
        cursor.execute('DELETE FROM documents WHERE id = ?', (document_id,))
        conn.commit()

        # Verify document deletion
        cursor.execute('SELECT * FROM documents WHERE id = ?', (document_id,))
        assert cursor.fetchone() is None

        # Verify that the linked processing result was also deleted by CASCADE
        cursor.execute('SELECT COUNT(*) FROM processing_results WHERE document_id = ?', (document_id,))
        count_results = cursor.fetchone()[0]
        assert count_results == 0

        conn.close()


class TestDatabaseMigrations:
    """Test database migration functionality"""

    def test_migration_file_exists(self):
        """Test that expected migration files exist in the file system."""
        migration_files = [
            'database/migrations/001_initial.sql',
            'database/migrations/filehash.sql'
        ]

        # Get the directory of the current test file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Assume project root is one level up from 'tests' directory
        project_root = os.path.join(current_dir, '..')

        for migration_file in migration_files:
            file_path = os.path.join(project_root, migration_file)
            assert os.path.exists(file_path), f"Migration file {file_path} does not exist."

    def test_apply_migrations(self):
        """Test applying database migrations in order."""
        pytest.skip("Implementing migration application requires a specific migration tool (e.g., Alembic) and setup.")
        # This test would typically:
        # 1. Create an empty database.
        # 2. Run your migration tool's 'upgrade' command to apply all migrations.
        # 3. Verify the final database schema (e.g., check table structures, column existence, constraints).

    def test_migration_idempotence(self):
        """Test that applying migrations multiple times doesn't break the database."""
        pytest.skip("Migration idempotence test requires a specific migration tool and verification.")
        # This test would:
        # 1. Apply migrations once.
        # 2. Apply them again.
        # 3. Assert no errors occur and the schema remains consistent and correct after the second application.

    def test_database_upgrades_and_downgrades(self):
        """Test database upgrade and downgrade paths for migrations (if supported)."""
        pytest.skip("Database upgrade/downgrade test requires a robust migration system that supports versioning.")
        # This is more advanced and requires a migration system that allows moving between specific versions.


if __name__ == '__main__':
    pytest.main([__file__])
