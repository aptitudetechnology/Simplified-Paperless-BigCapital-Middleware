# tests/test_database.py
"""
Test suite for database operations, including document storage,
retrieval, and processing results.
"""

import pytest
import sqlite3
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

# Attempt to import database functions and models
try:
    from database.database import init_db, add_document, get_document_by_id, update_document_status, \
                                  get_all_documents, add_processing_result, get_processing_results_for_document
    from database.models import Base, Document, ProcessingResult, SessionLocal, engine
except ImportError:
    # This block allows tests to run even if the database modules are not fully implemented yet
    init_db = add_document = get_document_by_id = update_document_status = None
    get_all_documents = add_processing_result = get_processing_results_for_document = None
    Base = None
    SessionLocal = None
    engine = None
    Document = MagicMock() # Mock the Document and ProcessingResult classes
    ProcessingResult = MagicMock()


@pytest.fixture(scope="module")
def setup_database():
    """
    Module-scoped fixture to set up and tear down a temporary SQLite database
    for testing.
    """
    if init_db is None or SessionLocal is None or engine is None:
        pytest.skip("Database modules not fully implemented yet")

    # Use a temporary in-memory database for speed and isolation
    test_db_url = "sqlite:///./test_temp.db"
    # Ensure the test DB file is clean before starting
    if os.path.exists("./test_temp.db"):
        os.remove("./test_temp.db")

    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Yield control to tests
    yield "sqlite:///./test_temp.db"

    # Teardown: close session and drop tables, then delete the file
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_temp.db"):
        os.remove("./test_temp.db")


@pytest.fixture(scope="function")
def test_db():
    """
    Function-scoped fixture to create a temporary database file for each test,
    ensuring isolation. This is used when direct sqlite3.connect is needed.
    """
    # Create a temporary file path for the SQLite database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name
    
    # Initialize the database within this temporary file for this specific test
    # This ensures a clean slate for each test using this fixture
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Define schema directly for this isolated test fixture
    # This ensures the schema is present for sqlite3.connect usage
    cursor.execute('''
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER,
            status TEXT,
            upload_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE processing_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            ocr_text TEXT,
            extracted_data TEXT, -- Store JSON string or similar
            success BOOLEAN,
            created_date TEXT,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

    yield db_path

    # Clean up the temporary database file after the test
    os.unlink(db_path)


class TestDatabaseInitAndTeardown:
    """Test database initialization and teardown processes."""

    def test_init_db(self, setup_database):
        """Test if the database initialization creates tables."""
        if init_db is None or SessionLocal is None:
            pytest.skip("Database modules not fully implemented yet")
        
        # init_db is called by setup_database
        # Try to connect and list tables to verify
        test_engine = create_engine(setup_database)
        inspector = inspect(test_engine)
        assert 'documents' in inspector.get_table_names()
        assert 'processing_results' in inspector.get_table_names()

    def test_session_creation(self, setup_database):
        """Test if a database session can be created."""
        if SessionLocal is None:
            pytest.skip("Database modules not fully implemented yet")
        session = SessionLocal()
        assert session is not None
        session.close()


class TestDocumentOperations:
    """Test CRUD operations for documents."""

    def test_add_document(self, setup_database):
        """Test adding a new document to the database."""
        if add_document is None or SessionLocal is None or Document is None:
            pytest.skip("Database modules not fully implemented yet")

        session = SessionLocal()
        try:
            document_data = {
                'filename': 'test_doc.pdf',
                'file_path': '/uploads/test_doc.pdf',
                'file_type': 'pdf',
                'file_size': 1024,
                'status': 'uploaded'
            }
            document = add_document(session, **document_data)
            assert document is not None
            assert document.filename == 'test_doc.pdf'
            assert document.status == 'uploaded'
            assert document.upload_date is not None

            # Verify by fetching
            fetched_doc = session.query(Document).filter_by(filename='test_doc.pdf').first()
            assert fetched_doc.id == document.id
        finally:
            session.close()

    def test_get_document_by_id(self, setup_database):
        """Test retrieving a document by its ID."""
        if add_document is None or get_document_by_id is None or SessionLocal is None:
            pytest.skip("Database modules not fully implemented yet")

        session = SessionLocal()
        try:
            document_data = {
                'filename': 'retrieve_doc.png',
                'file_path': '/uploads/retrieve_doc.png',
                'file_type': 'png',
                'file_size': 2048,
                'status': 'processing'
            }
            added_document = add_document(session, **document_data)
            
            fetched_document = get_document_by_id(session, added_document.id)
            assert fetched_document is not None
            assert fetched_document.filename == 'retrieve_doc.png'
            assert fetched_document.id == added_document.id

            assert get_document_by_id(session, 99999) is None # Non-existent ID
        finally:
            session.close()

    def test_update_document_status(self, setup_database):
        """Test updating a document's status."""
        if add_document is None or update_document_status is None or SessionLocal is None:
            pytest.skip("Database modules not fully implemented yet")

        session = SessionLocal()
        try:
            document_data = {
                'filename': 'update_doc.jpg',
                'file_path': '/uploads/update_doc.jpg',
                'file_type': 'jpg',
                'file_size': 500,
                'status': 'uploaded'
            }
            added_document = add_document(session, **document_data)
            
            updated_doc = update_document_status(session, added_document.id, 'processed')
            assert updated_doc is not None
            assert updated_doc.status == 'processed'

            # Verify in DB
            fetched_doc = session.query(Document).get(added_document.id)
            assert fetched_doc.status == 'processed'

            # Test update of non-existent document
            assert update_document_status(session, 99999, 'failed') is None
        finally:
            session.close()

    def test_get_all_documents(self, setup_database):
        """Test retrieving all documents from the database."""
        if add_document is None or get_all_documents is None or SessionLocal is None:
            pytest.skip("Database modules not fully implemented yet")

        session = SessionLocal()
        try:
            # Ensure DB is empty before test or handle existing data if necessary
            session.query(Document).delete()
            session.commit()

            docs_before = get_all_documents(session)
            assert len(docs_before) == 0

            add_document(session, filename='doc1.pdf', file_path='/path/1.pdf', file_type='pdf', file_size=100, status='uploaded')
            add_document(session, filename='doc2.png', file_path='/path/2.png', file_type='png', file_size=200, status='processed')
            
            all_docs = get_all_documents(session)
            assert len(all_docs) == 2
            assert any(d.filename == 'doc1.pdf' for d in all_docs)
            assert any(d.filename == 'doc2.png' for d in all_docs)
        finally:
            session.close()


class TestProcessingResultOperations:
    """Test CRUD operations for processing results."""

    def test_add_processing_result(self, setup_database):
        """Test adding a new processing result."""
        if add_document is None or add_processing_result is None or SessionLocal is None:
            pytest.skip("Database modules not fully implemented yet")

        session = SessionLocal()
        try:
            # First, add a document to link the result to
            doc = add_document(session, filename='result_doc.pdf', file_path='/uploads/res.pdf', file_type='pdf', file_size=500, status='processed')
            
            result_data = {
                'document_id': doc.id,
                'ocr_text': 'This is OCR text.',
                'extracted_data': {'invoice_number': 'INV-TEST-001', 'total_amount': 123.45},
                'success': True
            }
            result = add_processing_result(session, **result_data)
            
            assert result is not None
            assert result.document_id == doc.id
            assert result.ocr_text == 'This is OCR text.'
            assert result.success is True
            assert result.created_date is not None

            # Verify by fetching
            fetched_result = session.query(ProcessingResult).filter_by(document_id=doc.id).first()
            assert fetched_result.id == result.id
        finally:
            session.close()

    def test_get_processing_results_for_document(self, setup_database):
        """Test retrieving all processing results for a specific document."""
        if add_document is None or add_processing_result is None or get_processing_results_for_document is None or SessionLocal is None:
            pytest.skip("Database modules not fully implemented yet")

        session = SessionLocal()
        try:
            doc1 = add_document(session, filename='doc_results1.pdf', file_path='/path/doc1.pdf', file_type='pdf', file_size=100, status='processed')
            doc2 = add_document(session, filename='doc_results2.png', file_path='/path/doc2.png', file_type='png', file_size=200, status='uploaded')

            add_processing_result(session, document_id=doc1.id, ocr_text='Text for doc1_1', success=True)
            add_processing_result(session, document_id=doc1.id, ocr_text='Text for doc1_2', success=False)
            add_processing_result(session, document_id=doc2.id, ocr_text='Text for doc2_1', success=True)

            results_doc1 = get_processing_results_for_document(session, doc1.id)
            assert len(results_doc1) == 2
            assert any('Text for doc1_1' in r.ocr_text for r in results_doc1)
            assert any('Text for doc1_2' in r.ocr_text for r in results_doc1)

            results_doc2 = get_processing_results_for_document(session, doc2.id)
            assert len(results_doc2) == 1
            assert any('Text for doc2_1' in r.ocr_text for r in results_doc2)

            assert len(get_processing_results_for_document(session, 99999)) == 0 # Non-existent document
        finally:
            session.close()


class TestDatabaseOperations:
    """
    Test low-level database operations that might not directly use SQLAlchemy
    helpers, especially for features like CASCADE.
    """
    import tempfile # Make sure tempfile is imported
    import os # Make sure os is imported
    import sqlite3 # Make sure sqlite3 is imported
    from datetime import datetime # Make sure datetime is imported

    def test_delete_document(self, test_db):
        """Test deleting documents and verify cascade deletion of related processing results"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # --- THIS IS THE CRUCIAL LINE TO ADD ---
        cursor.execute('PRAGMA foreign_keys = ON;')
        # --- END OF CRUCIAL LINE ---
        
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
        assert count_results == 0 # This assertion should now pass

        conn.close() # Close the connection after the test
