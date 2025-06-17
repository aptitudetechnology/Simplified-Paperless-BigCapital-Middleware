# web/routes.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import json
from datetime import datetime, timedelta
import mimetypes
from typing import Dict, Any, List

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

def init_routes(app_config: Config, app_db_manager: DatabaseManager, app_doc_processor: DocumentProcessor):
    """Initialize routes with dependency injection"""
    global config, db_manager, doc_processor
    config = app_config
    db_manager = app_db_manager
    doc_processor = app_doc_processor

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    allowed_extensions = config.get('processing', 'allowed_extensions').split(',')
    return ext in [e.strip() for e in allowed_extensions]

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

# Web Routes
@web.route('/')
def index():
    """Main dashboard page"""
    try:
        # Get recent documents
        with db_manager.get_session() as session:
            recent_docs = session.execute("""
                SELECT id, original_filename, status, upload_date, total_amount, vendor_name
                FROM documents 
                ORDER BY upload_date DESC 
                LIMIT 10
            """).fetchall()
            
            # Get processing stats
            stats = session.execute("""
                SELECT 
                    COUNT(*) as total_docs,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    AVG(CASE WHEN status = 'completed' THEN total_amount END) as avg_amount
                FROM documents
                WHERE upload_date >= date('now', '-30 days')
            """).fetchone()
            
        return render_template('dashboard.html', 
                             recent_docs=recent_docs, 
                             stats=stats)
    except Exception as e:
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
        with db_manager.get_session() as session:
            query = "SELECT * FROM document_summary WHERE 1=1"
            params = []
            
            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)
            
            query += " ORDER BY upload_date DESC LIMIT ? OFFSET ?"
            params.extend([per_page, (page - 1) * per_page])
            
            documents = session.execute(query, params).fetchall()
            
            # Get total count for pagination
            count_query = "SELECT COUNT(*) FROM documents WHERE 1=1"
            count_params = []
            if status_filter:
                count_query += " AND status = ?"
                count_params.append(status_filter)
            
            total = session.execute(count_query, count_params).fetchone()[0]
            
        return render_template('documents.html', 
                             documents=documents,
                             page=page,
                             per_page=per_page,
                             total=total,
                             status_filter=status_filter)
    except Exception as e:
        flash(f'Error loading documents: {str(e)}', 'error')
        return render_template('documents.html', documents=[], page=1, per_page=per_page, total=0)

@web.route('/document/<int:doc_id>')
def document_detail(doc_id: int):
    """Document detail page"""
    try:
        with db_manager.get_session() as session:
            # Get document details
            doc = session.execute("""
                SELECT * FROM document_summary WHERE id = ?
            """, [doc_id]).fetchone()
            
            if not doc:
                flash('Document not found', 'error')
                return redirect(url_for('web.documents_list'))
            
            # Get line items
            line_items = session.execute("""
                SELECT * FROM document_line_items 
                WHERE document_id = ? 
                ORDER BY line_number
            """, [doc_id]).fetchall()
            
            # Get processing log
            processing_log = session.execute("""
                SELECT level, message, created_at, details
                FROM processing_log 
                WHERE document_id = ? 
                ORDER BY created_at DESC
                LIMIT 50
            """, [doc_id]).fetchall()
            
        return render_template('document_detail.html',
                             document=doc,
                             line_items=line_items,
                             processing_log=processing_log)
    except Exception as e:
        flash(f'Error loading document: {str(e)}', 'error')
        return redirect(url_for('web.documents_list'))

# API Routes
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
        
        # Check file size
        max_size = int(config.get('processing', 'max_file_size', '10485760'))
        if request.content_length > max_size:
            return jsonify({'error': f'File too large. Maximum size: {max_size} bytes'}), 413
        
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
        
        # Create document record
        with db_manager.get_session() as session:
            result = session.execute("""
                INSERT INTO documents 
                (filename, original_filename, file_path, file_size, mime_type, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            """, [unique_filename, filename, filepath, file_info['size'], file_info['mime_type']])
            
            doc_id = result.lastrowid
            session.commit()
            
            # Create processing job if auto-processing is enabled
            if config.getboolean('system', 'auto_process_uploads', fallback=True):
                session.execute("""
                    INSERT INTO processing_jobs (document_id, job_type, status)
                    VALUES (?, 'ocr', 'pending')
                """, [doc_id])
                session.commit()
        
        # Start processing if enabled
        auto_process = request.form.get('auto_process', 'true').lower() == 'true'
        if auto_process:
            try:
                # Process in background (in production, use Celery or similar)
                doc_processor.process_document(doc_id)
            except Exception as e:
                # Log error but don't fail the upload
                print(f"Processing error for doc {doc_id}: {e}")
        
        return jsonify({
            'success': True,
            'document_id': doc_id,
            'filename': unique_filename,
            'message': 'File uploaded successfully'
        }), 201
        
    except RequestEntityTooLarge:
        return jsonify({'error': 'File too large'}), 413
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@api.route('/documents', methods=['GET'])
def api_list_documents():
    """Get documents list via API"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status')
        
        with db_manager.get_session() as session:
            query = "SELECT * FROM document_summary WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY upload_date DESC LIMIT ? OFFSET ?"
            params.extend([per_page, (page - 1) * per_page])
            
            documents = session.execute(query, params).fetchall()
            
            # Convert to dict
            docs_list = []
            for doc in documents:
                doc_dict = dict(doc._mapping)
                # Convert datetime objects to ISO format
                for key, value in doc_dict.items():
                    if isinstance(value, datetime):
                        doc_dict[key] = value.isoformat()
                docs_list.append(doc_dict)
        
        return jsonify({
            'documents': docs_list,
            'page': page,
            'per_page': per_page,
            'total': len(docs_list)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/documents/<int:doc_id>', methods=['GET'])
def api_get_document(doc_id: int):
    """Get document details via API"""
    try:
        with db_manager.get_session() as session:
            doc = session.execute("""
                SELECT * FROM document_summary WHERE id = ?
            """, [doc_id]).fetchone()
            
            if not doc:
                return jsonify({'error': 'Document not found'}), 404
            
            # Get line items
            line_items = session.execute("""
                SELECT * FROM document_line_items WHERE document_id = ?
            """, [doc_id]).fetchall()
            
            # Convert to dict
            doc_dict = dict(doc._mapping)
            for key, value in doc_dict.items():
                if isinstance(value, datetime):
                    doc_dict[key] = value.isoformat()
            
            doc_dict['line_items'] = []
            for item in line_items:
                item_dict = dict(item._mapping)
                for key, value in item_dict.items():
                    if isinstance(value, datetime):
                        item_dict[key] = value.isoformat()
                doc_dict['line_items'].append(item_dict)
        
        return jsonify(doc_dict)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/documents/<int:doc_id>/process', methods=['POST'])
def api_process_document(doc_id: int):
    """Trigger document processing via API"""
    try:
        with db_manager.get_session() as session:
            # Check if document exists
            doc = session.execute("""
                SELECT id, status FROM documents WHERE id = ?
            """, [doc_id]).fetchone()
            
            if not doc:
                return jsonify({'error': 'Document not found'}), 404
            
            if doc.status == 'processing':
                return jsonify({'error': 'Document is already being processed'}), 400
            
            # Create processing job
            session.execute("""
                INSERT INTO processing_jobs (document_id, job_type, status, queued_at)
                VALUES (?, 'full_processing', 'pending', CURRENT_TIMESTAMP)
            """, [doc_id])
            session.commit()
        
        # Start processing
        try:
            result = doc_processor.process_document(doc_id)
            return jsonify({
                'success': True,
                'message': 'Processing completed',
                'result': result
            })
        except ProcessingError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }), 422
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/stats', methods=['GET'])
def api_get_stats():
    """Get processing statistics via API"""
    try:
        days = request.args.get('days', 30, type=int)
        
        with db_manager.get_session() as session:
            stats = session.execute("""
                SELECT 
                    COUNT(*) as total_documents,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
                    AVG(CASE WHEN total_amount > 0 THEN total_amount END) as avg_amount,
                    SUM(CASE WHEN total_amount > 0 THEN total_amount ELSE 0 END) as total_amount,
                    AVG(ocr_confidence) as avg_ocr_confidence
                FROM documents
                WHERE upload_date >= date('now', '-' || ? || ' days')
            """, [days]).fetchone()
            
            # Get daily stats
            daily_stats = session.execute("""
                SELECT 
                    DATE(upload_date) as date,
                    COUNT(*) as count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM documents
                WHERE upload_date >= date('now', '-' || ? || ' days')
                GROUP BY DATE(upload_date)
                ORDER BY date DESC
            """, [days]).fetchall()
            
        return jsonify({
            'period_days': days,
            'summary': dict(stats._mapping) if stats else {},
            'daily_stats': [dict(row._mapping) for row in daily_stats]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        with db_manager.get_session() as session:
            session.execute("SELECT 1").fetchone()
        
        # Check upload directory
        upload_folder = config.get('processing', 'upload_folder', 'uploads')
        upload_accessible = os.path.exists(upload_folder) and os.access(upload_folder, os.W_OK)
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'upload_folder': 'accessible' if upload_accessible else 'not accessible'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Error handlers
@api.errorhandler(413)
def file_too_large(e):
    return jsonify({'error': 'File too large'}), 413

@api.errorhandler(400)
def bad_request(e):
    return jsonify({'error': 'Bad request'}), 400

@api.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500
