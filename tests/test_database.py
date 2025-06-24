def test_delete_document(self, test_db):
    """Test deleting documents and verify cascade deletion of related processing results"""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    # Enable foreign key constraints
    cursor.execute('PRAGMA foreign_keys = ON;')
    
    # Verify foreign keys are enabled
    cursor.execute('PRAGMA foreign_keys;')
    fk_enabled = cursor.fetchone()[0]
    print(f"Foreign keys enabled: {fk_enabled}")  # Debug output
    
    try:
        # Insert a document
        cursor.execute('''
            INSERT INTO documents (filename, file_path, file_type, file_size, status, upload_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('doc_to_delete.pdf', '/test_delete.pdf', 'pdf', 1000, 'processed', datetime.now().isoformat()))

        document_id = cursor.lastrowid
        print(f"Inserted document with ID: {document_id}")  # Debug output

        # Insert a processing result linked to this document
        cursor.execute('''
            INSERT INTO processing_results (document_id, ocr_text, success, created_date)
            VALUES (?, ?, ?, ?)
        ''', (document_id, 'Text from deleted doc', True, datetime.now().isoformat()))

        processing_result_id = cursor.lastrowid
        print(f"Inserted processing result with ID: {processing_result_id}")  # Debug output

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

        # Delete the document
        cursor.execute('DELETE FROM documents WHERE id = ?', (document_id,))
        rows_deleted = cursor.rowcount
        print(f"Rows deleted from documents: {rows_deleted}")
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
        
        # This is the assertion that was likely failing at line 800
        assert result_count_after == 0, f"Expected 0 processing results after document deletion, but found {result_count_after}"

    except Exception as e:
        print(f"Test failed with error: {e}")
        # Debug: Check what's actually in the tables
        cursor.execute('SELECT * FROM documents')
        docs = cursor.fetchall()
        print(f"All documents: {docs}")
        
        cursor.execute('SELECT * FROM processing_results')
        results = cursor.fetchall()
        print(f"All processing results: {results}")
        raise
    finally:
        conn.close()


# Alternative implementation if CASCADE isn't working properly
def test_delete_document_manual_cascade(self, test_db):
    """Test deleting documents with manual cascade deletion"""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    # Enable foreign key constraints
    cursor.execute('PRAGMA foreign_keys = ON;')
    
    try:
        # Insert a document
        cursor.execute('''
            INSERT INTO documents (filename, file_path, file_type, file_size, status, upload_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('doc_to_delete.pdf', '/test_delete.pdf', 'pdf', 1000, 'processed', datetime.now().isoformat()))

        document_id = cursor.lastrowid

        # Insert a processing result linked to this document
        cursor.execute('''
            INSERT INTO processing_results (document_id, ocr_text, success, created_date)
            VALUES (?, ?, ?, ?)
        ''', (document_id, 'Text from deleted doc', True, datetime.now().isoformat()))

        conn.commit()

        # Manual cascade deletion approach
        # First delete processing results
        cursor.execute('DELETE FROM processing_results WHERE document_id = ?', (document_id,))
        # Then delete the document
        cursor.execute('DELETE FROM documents WHERE id = ?', (document_id,))
        conn.commit()

        # Verify both are deleted
        cursor.execute('SELECT COUNT(*) FROM documents WHERE id = ?', (document_id,))
        assert cursor.fetchone()[0] == 0

        cursor.execute('SELECT COUNT(*) FROM processing_results WHERE document_id = ?', (document_id,))
        assert cursor.fetchone()[0] == 0

    finally:
        conn.close()


# Fix for the schema to ensure CASCADE works properly
def create_test_schema_with_proper_cascade(cursor):
    """Create test schema with proper CASCADE deletion"""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
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
        CREATE TABLE IF NOT EXISTS processing_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            ocr_text TEXT,
            extracted_data TEXT,
            success BOOLEAN,
            created_date TEXT,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        )
    ''')
