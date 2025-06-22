# web/routes.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import json
from datetime import datetime, timedelta
import mimetypes
from typing import Dict, Any, List
import logging

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
        recent_docs = db_manager.list_documents(limit=10)

        # db_manager.get_stats() fetches general stats
        stats = db_manager.get_stats()

        # You might want to parse 'extracted_data' JSON string into a dict for display
        for doc in recent_docs:
            if 'extracted_data' in doc and isinstance(doc['extracted_data'], str):
                try:
                    doc['extracted_data'] = json.loads(doc['extracted_data'])
                except json.JSONDecodeError:
                    doc['extracted_data'] = {}
            else:
                doc['extracted_data'] = {}

        return render_template('dashboard.html',
                               recent_docs=recent_docs,
                               stats=stats)
    except Exception as e:
        logger.error(f'Error loading dashboard: {str(e)}')
        flash(f'Error loading dashboard: {str(e)}', 'error')
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
        query = "SELECT * FROM documents WHERE 1=1"
        params = []
        
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        
        query += " ORDER BY upload_date DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        documents_raw = db_manager.execute_query(query, tuple(params))
        
        # Convert sqlite3.Row objects to dictionaries and parse JSON
        documents = []
        for doc_row in documents_raw:
            doc_dict = dict(doc_row)
            if 'extracted_data' in doc_dict and isinstance(doc_dict['extracted_data'], str):
                try:
                    doc_dict['extracted_data'] = json.loads(doc_dict['extracted_data'])
                except json.JSONDecodeError:
                    doc_dict['extracted_data'] = {}
            else:
                doc_dict['extracted_data'] = {}
            documents.append(doc_dict)

        # Get total count for pagination
        count_query = "SELECT COUNT(*) FROM documents WHERE 1=1"
        count_params = []
        if status_filter:
            count_query += " AND status = ?"
            count_params.append(status_filter)
        
        total_result = db_manager.execute_query(count_query, tuple(count_params))
        total = total_result[0][0] if total_result else 0

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
            doc['extracted_data'] = {}

        line_items = doc['extracted_data'].get('line_items', [])
        processing_log = []  # Placeholder

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
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        unique_filename = f"{timestamp}{filename}"
        
        upload_folder = config.get('processing', 'upload_folder', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        
        # Get file info
        file_info = get_file_info(filepath)
        
        # Insert document record using db_manager's method
        doc_id = db_manager.store_document({
            'filename': unique_filename,
            'original_filename': filename,
            'file_path': filepath,
            'file_size': file_info['size'],
            'content_type': file_info['mime_type'],
            'status': 'pending'
        })
        
        logger.info(f"Document uploaded with ID {doc_id}: {unique_filename}")
        
        # Start processing if enabled
        auto_process = request.form.get('auto_process', 'true').lower() == 'true'
        if auto_process and doc_processor:
            try:
                logger.info(f"Starting automatic processing for document ID {doc_id}")
                result = doc_processor.process_document_by_id(doc_id)
                logger.info(f"Processing result for doc {doc_id}: {result}")
            except Exception as e:
                logger.error(f"Processing error for doc {doc_id}: {e}")
                try:
                    db_manager.update_document(doc_id, status='failed', error_message=str(e))
                except Exception as db_error:
                    logger.error(f"Failed to update document status to failed: {db_error}")
        
        return jsonify({
            'success': True,
            'document_id': doc_id,
            'filename': unique_filename,
            'message': 'File uploaded successfully'
        }), 201
        
    except RequestEntityTooLarge:
        return jsonify({'error': 'File too large'}), 413
    except Exception as e:
        logger.error(f'Upload failed: {str(e)}')
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@api.route('/documents', methods=['GET'])
def get_documents():
    """Get documents list via API"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status', '')
        
        offset = (page - 1) * per_page
        
        if status_filter:
            documents = db_manager.execute_query(
                "SELECT * FROM documents WHERE status = ? ORDER BY upload_date DESC LIMIT ? OFFSET ?",
                (status_filter, per_page, offset)
            )
            total_result = db_manager.execute_query(
                "SELECT COUNT(*) FROM documents WHERE status = ?",
                (status_filter,)
            )
        else:
            documents = db_manager.execute_query(
                "SELECT * FROM documents ORDER BY upload_date DESC LIMIT ? OFFSET ?",
                (per_page, offset)
            )
            total_result = db_manager.execute_query("SELECT COUNT(*) FROM documents")
        
        total = total_result[0][0] if total_result else 0
        
        # Convert to list of dicts
        documents_list = [dict(doc) for doc in documents]
        
        return jsonify({
            'documents': documents_list,
            'total': total,
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f'Error getting documents: {str(e)}')
        return jsonify({'error': str(e)}), 500

@api.route('/document/<int:doc_id>', methods=['GET'])
def get_document(doc_id: int):
    """Get document by ID via API"""
    try:
        doc = db_manager.get_document(doc_id)
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        
        return jsonify({'document': doc})
        
    except Exception as e:
        logger.error(f'Error getting document {doc_id}: {str(e)}')
        return jsonify({'error': str(e)}), 500

@api.route('/stats', methods=['GET'])
def get_stats():
    """Get processing statistics via API"""
    try:
        stats = db_manager.get_stats()
        return jsonify({'stats': stats})
        
    except Exception as e:
        logger.error(f'Error getting stats: {str(e)}')
        return jsonify({'error': str(e)}), 500
