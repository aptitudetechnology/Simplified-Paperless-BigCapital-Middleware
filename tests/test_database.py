import sqlite3
from datetime import datetime
import os
import tempfile
import pytest # Import pytest for the fixture decorator

class TestDatabaseOperations:
    # Removed setup_method and teardown_method as the new test_delete_document
    # now explicitly handles its own database connection via the test_db fixture
    # and recreates tables within itself. This avoids conflicts and ensures isolation
    # when using the test_db fixture.

    # Removed _create_test_schema_with_proper_cascade as its functionality
    # is now directly handled within the test_delete_document method and test_db fixture.

    def test_delete_document(self, test_db):
        """Test deleting documents and verify cascade deletion of related processing results"""
        # Connect to the database provided by the test_db fixture
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # CRUCIAL: Enable foreign key constraints for this connection
        # This is essential for ON DELETE CASCADE to work
        cursor.execute('PRAGMA foreign_keys = ON;')
        
        # Verify foreign keys are enabled (for debugging)
        cursor.execute('PRAGMA foreign_keys;')
        fk_enabled = cursor.fetchone()[0]
        print(f"Foreign keys enabled: {fk_enabled}")
        
        # The test_db fixture already creates the tables.
        # However, if running this test in isolation without pytest,
        # or if you want to explicitly ensure a fresh schema here,
        # you might drop and recreate. For a pytest setup with the fixture,
        # the fixture itself ensures a clean slate.
        # The lines below are commented out as the fixture already handles table creation.
        # If your environment requires it, uncomment and adjust:
        # cursor.execute('DROP TABLE IF EXISTS processing_results')
        # cursor.execute('DROP TABLE IF EXISTS documents')
        #
        # # Create documents table
        # cursor.execute('''
        #     CREATE TABLE documents (
        #         id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         filename TEXT NOT NULL,
        #         file_path TEXT NOT NULL,
        #         file_type TEXT,
        #         file_size INTEGER,
        #         status TEXT,
        #         upload_date TEXT
        #     )
        # ''')
        #
        # # Create processing_results table with ON DELETE CASCADE
        # cursor.execute('''
        #     CREATE TABLE processing_results (
        #         id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         document_id INTEGER NOT NULL,
        #         ocr_text TEXT,
        #         extracted_data TEXT,
        #         success BOOLEAN,
        #         created_date TEXT,
        #         FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        #     )
        # ''')
        # conn.commit() # Commit schema changes

        try:
            # Insert a document
            cursor.execute('''
                INSERT INTO documents (filename, file_path, file_type, file_size, status, upload_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('doc_to_delete.pdf', '/test_delete.pdf', 'pdf', 1000, 'processed', datetime.now().isoformat()))

            document_id = cursor.lastrowid
            print(f"Inserted document with ID: {document_id}")

            # Insert a processing result linked to this document
            cursor.execute('''
                INSERT INTO processing_results (document_id, ocr_text, success, created_date)
                VALUES (?, ?, ?, ?)
            ''', (document_id, 'Text from deleted doc', True, datetime.now().isoformat()))

            processing_result_id = cursor.lastrowid
            print(f"Inserted processing result with ID: {processing_result_id}")

            conn.commit()

            # Verify existence before deletion
            cursor.execute('SELECT COUNT(*) FROM documents WHERE id = ?', (document_id,))
            doc_count_before = cursor.fetchone()[0]
            print(f"Documents before deletion: {doc_count_before}")
            assert doc_count_before == 1

            cursor.execute('SELECT COUNT(*) FROM processing_results WHERE document_id = ?', (document_id,))
            result_count_before = cursor.fetchone()[0]
            print(f"Processing results before deletion: {result_count_before}")
            assert result_count_before == 1

            # Delete the document (this should trigger the cascade)
            print(f"Attempting to delete document with ID: {document_id}")
            cursor.execute('DELETE FROM documents WHERE id = ?', (document_id,))
            rows_deleted = cursor.rowcount
            print(f"Rows deleted from documents table: {rows_deleted}")
            conn.commit()

            # Verify document deletion
            cursor.execute('SELECT COUNT(*) FROM documents WHERE id = ?', (document_id,))
            doc_count_after = cursor.fetchone()[0]
            print(f"Documents after deletion: {doc_count_after}")
            assert doc_count_after == 0

            # Verify that the linked processing result was also deleted by CASCADE
            cursor.execute('SELECT COUNT(*) FROM processing_results WHERE document_id = ?', (document_id,))
            result_count_after = cursor.fetchone()[0]
            print(f"Processing results after deletion: {result_count_after}")

            assert result_count_after == 0, \
                f"Expected 0 processing results after document deletion, but found {result_count_after}"
            print("Cascade deletion successful!")

        except Exception as e:
            print(f"Test failed with error: {e}")
            # Debug: Check what's actually in the tables
            cursor.execute('SELECT * FROM documents')
            docs = cursor.fetchall()
            print(f"All documents: {docs}")
            
            cursor.execute('SELECT * FROM processing_results')
            results = cursor.fetchall()
            print(f"All processing results: {results}")
            raise # Re-raise the exception to indicate test failure
        finally:
            conn.close()


# Also, update the test_db fixture to ensure it creates tables with CASCADE:
@pytest.fixture(scope="function")
def test_db():
    """
    Function-scoped fixture to create a temporary database file for each test,
    ensuring isolation. This is used when direct sqlite3.connect is needed
    for lower-level SQLite testing (e.g., CASCADE).
    """
    # Create a temporary file path for the SQLite database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name
    
    # Initialize the database within this temporary file for this specific test
    # This ensures a clean slate for each test using this fixture
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys for this connection
    cursor.execute('PRAGMA foreign_keys = ON;')

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
    conn.close() # Close connection after setup

    yield db_path

    # Clean up the temporary database file after the test
    os.unlink(db_path)


# Example of how you might run it manually for quick testing without pytest:
if __name__ == "__main__":
    # Simulate the test_db fixture for manual execution
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path_for_manual_run = tmp_file.name

    # Setup the database via the test_db fixture logic
    conn_manual = sqlite3.connect(db_path_for_manual_run)
    cursor_manual = conn_manual.cursor()
    cursor_manual.execute('PRAGMA foreign_keys = ON;')
    cursor_manual.execute('''
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
    cursor_manual.execute('''
        CREATE TABLE processing_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            ocr_text TEXT,
            extracted_data TEXT,
            success BOOLEAN,
            created_date TEXT,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        )
    ''')
    conn_manual.commit()
    conn_manual.close()

    test_runner = TestDatabaseOperations()
    print("\n--- Running test_delete_document (manual simulation) ---")
    try:
        # Pass the path of the temporary database to the test method
        test_runner.test_delete_document(db_path_for_manual_run)
    except AssertionError as ae:
        print(f"Test failed: {ae}")
    finally:
        # Clean up the temporary database file after the manual run
        if os.path.exists(db_path_for_manual_run):
            os.unlink(db_path_for_manual_run)

