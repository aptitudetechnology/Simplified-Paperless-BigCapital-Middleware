# web/routes.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import json
from datetime import datetime, timedelta
import mimetypes
from typing import Dict, Any, List
import logging # Import logging

from config.settings import Config
from database.connection import DatabaseManager
from processing.document_processor import DocumentProcessor
from processing.exceptions import ProcessingError, OCRError, ExtractionError

# Create blueprints
api = Blueprint('api', __name__, url_prefix='/api')
web = Blueprint('web', __name__)

# Global variables (will be injected by app.py)
config: Config = None
db_manager: DatabaseManager = None
doc_processor: DocumentProcessor = None

# Logger for this module
logger = logging.getLogger(__name__)

def init_routes(app_config: Config, app_db_manager: DatabaseManager, app_doc_processor: DocumentProcessor):
    """Initialize routes with dependency injection"""
    global config, db_manager, doc_processor
    config = app_config
    db_manager = app_db_manager
    doc_processor = app_doc_processor
    logger.info("Routes initialized with dependencies.")

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    # Ensure config and key exist before splitting
    allowed_extensions_str = config.get('processing', 'allowed_extensions', fallback='pdf,jpg,jpeg,png')
    allowed_extensions = [e.strip() for e in allowed_extensions_str.split(',')]
    return ext in allowed_extensions

def get_file_info(filepath: str) -> Dict[str, Any]:
    """Get file information"""
    if not os.path.exists(filepath):
        return {}
    
    stat = os.stat(filepath)
    mime_type, _ = mimetypes.guess_type(filepath)
    
    return {
        'size': stat.st_size,
        'mime_type': mime_type,
        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
    }

# --- Web Routes ---
@web.route('/')
def index():
    """Main dashboard page"""
    try:
        # Use db_manager's specific methods or execute_query
        # db_manager.get_documents() fetches from 'documents' table
        recent_docs = db_manager.get_documents(limit=10)
        
        # db_manager.get_stats() fetches general stats
        stats = db_manager.get_stats()

        # You might want to parse 'extracted_data' JSON string into a dict for display
        for doc in recent_docs:
            if 'extracted_data' in doc and isinstance(doc['extracted_data'], str):
                try:
                    doc['extracted_data'] = json.loads(doc['extracted_data'])
                except json.JSONDecodeError:
                    doc['extracted_data'] = {} # Default to empty dict if parsing fails
            else:
                doc['extracted_data'] = {} # Ensure it's always a dict for template access

        # Convert stats to a dictionary if it's a sqlite3.Row object
        # db_manager.get_stats() already returns a dict, so no change needed here.
        
        return render_template('dashboard.html', 
                               recent_docs=recent_docs, 
                               stats=stats)
    except Exception as e:
        logger.error(f'Error loading dashboard: {str(e)}')
        flash(f'Error loading dashboard: {str(e)}', 'error')
        # Ensure we return a template even on error, so the app doesn't crash completely
        return render_template('dashboard.html', recent_docs=[], stats=None)

@web.route('/upload')
def upload_page():
    """File upload page"""
    return render_template('upload.html')

@web.route('/documents')
def documents_list():
    """Documents list page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status_filter = request.args.get('status', '')
    
    try:
        # Use db_manager.execute_query for custom queries
        # Note: 'document_summary' table does not exist. Use 'documents' table.
        query = "SELECT * FROM documents WHERE 1=1" # 'documents' table
        params = []
        
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        
        query += " ORDER BY upload_date DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        # Use db_manager.execute_query
        documents_raw = db_manager.execute_query(query, tuple(params))
        
        # Convert sqlite3.Row objects to dictionaries and parse JSON
        documents = []
        for doc_row in documents_raw:
            doc_dict = dict(doc_row) # Convert Row to dict
            if 'extracted_data' in doc_dict and isinstance(doc_dict['extracted_data'], str):
                try:
                    doc_dict['extracted_data'] = json.loads(doc_dict['extracted_data'])
                except json.JSONDecodeError:
                    doc_dict['extracted_data'] = {}
            else:
                doc_dict['extracted_data'] = {}
            documents.append(doc_dict)

        # Get total count for pagination
        count_query = "SELECT COUNT(*) FROM documents WHERE 1=1" # Count from 'documents'
        count_params = []
        if status_filter:
            count_query += " AND status = ?"
            count_params.append(status_filter)
        
        total_result = db_manager.execute_query(count_query, tuple(count_params))
        total = total_result[0][0] if total_result else 0 # Access the count value

        return render_template('documents.html', 
                               documents=documents,
                               page=page,
                               per_page=per_page,
                               total=total,
                               status_filter=status_filter)
    except Exception as e:
        logger.error(f'Error loading documents list: {str(e)}')
        flash(f'Error loading documents: {str(e)}', 'error')
        return render_template('documents.html', documents=[], page=1, per_page=per_page, total=0, status_filter=status_filter)

@web.route('/document/<int:doc_id>')
def document_detail(doc_id: int):
    """Document detail page"""
    try:
        # Use db_manager.get_document which is already defined and returns a dict
        doc = db_manager.get_document(doc_id)
        
        if not doc:
            flash('Document not found', 'error')
            return redirect(url_for('web.documents_list'))
        
        # Parse extracted_data JSON string to dict for display
        if 'extracted_data' in doc and isinstance(doc['extracted_data'], str):
            try:
                doc['extracted_data'] = json.loads(doc['extracted_data'])
            except json.JSONDecodeError:
                doc['extracted_data'] = {}
        else:
            doc['extracted_data'] = {} # Ensure it's always a dict

        # Line items would typically be stored within the 'extracted_data' JSON or a separate table.
        # Your `DatabaseManager` only defines 'documents' and 'extracted_data' (which is linked via document_id).
        # Assuming line_items is part of 'extracted_data' for now.
        line_items = doc['extracted_data'].get('line_items', []) # Get line_items from parsed extracted_data

        # 'processing_log' table does not exist in your current DatabaseManager init.
        # You'll need to decide how to store and retrieve processing logs.
        # For now, this will be an empty list to prevent error.
        processing_log = [] # Placeholder if you don't have a processing_log table

        return render_template('document_detail.html',
                               document=doc,
                               line_items=line_items,
                               processing_log=processing_log)
    except Exception as e:
        logger.error(f'Error loading document detail for ID {doc_id}: {str(e)}')
        flash(f'Error loading document: {str(e)}', 'error')
        return redirect(url_for('web.documents_list'))

# --- API Routes ---
@api.route('/upload', methods=['POST'])
def upload_file():
    """Upload file endpoint"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Check file size (Flask's app.config['MAX_CONTENT_LENGTH'] also handles this)
        # RequestEntityTooLarge is caught by the app.errorhandler in app.py
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        unique_filename = f"{timestamp}{filename}"
        
        upload_folder = config.get('processing', 'upload_folder', 'uploads')
        os.makedirs(upload_folder, exist_ok=True) # Ensure folder exists
        
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        
        # Get file info
        file_info = get_file_info(filepath)
        
        # Insert document record using db_manager's method
        doc_id = db_manager.insert_document(
            filename=unique_filename,
            original_filename=filename,
            file_path=filepath,
            file_size=file_info['size'],
            content_type=file_info['mime_type'] # Ensure 'mime_type' is the column name if storing here
        )
        
        # 'processing_jobs' table does not exist in your DatabaseManager init.
        # If you need job queuing, you must add this table.
        # For now, remove this block to prevent error, or add the table.
        # If auto_process_uploads is true, the processing will be triggered directly.
        # if config.getboolean('system', 'auto_process_uploads', fallback=True):
        #     with db_manager.get_connection() as conn: # Use get_connection here
        #         cursor = conn.cursor()
        #         cursor.execute("""
        #             INSERT INTO processing_jobs (document_id, job_type, status)
        #             VALUES (?, 'ocr', 'pending')
        #         """, [doc_id])
        #         conn.commit()
        
        # Start processing if enabled
        auto_process = request.form.get('auto_process', 'true').lower() == 'true'
        if auto_process and doc_processor: # Ensure doc_processor is initialized
            try:
                # Process in background (in production, use Celery or similar)
                doc_processor.process_document(doc_id)
            except Exception as e:
                # Log error but don't fail the upload
                logger.error(f"Processing error for doc {doc_id}: {e}")
        
        return jsonify({
            'success': True,
