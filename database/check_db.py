import sqlite3
import os

# Define the path to your database file
# This path assumes the script is run from the project root and the DB is in data/middleware.db
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'middleware.db')

def get_document_count(db_path):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        # Ensure row_factory is set for dictionary-like access if needed elsewhere,
        # though for COUNT it's not strictly necessary.
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents;")
        count = cursor.fetchone()[0]
        print(f"Number of documents in the database: {count}")
    except FileNotFoundError:
        print(f"Error: Database file not found at {db_path}. Please ensure the Flask app has been run at least once to initialize the database.")
    except sqlite3.OperationalError as e:
        print(f"Database operational error: {e}. This might mean the database file is locked or corrupt.")
    except sqlite3.Error as e:
        print(f"A SQLite error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    get_document_count(DB_PATH)
