# web/routes.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
import json
import hashlib
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

def get_file_hash(filepath: str) -> str:
    """Calculate SHA-256 hash of file content"""
    try:
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}")
        return ""

def check_duplicate_file(filename: str, file_hash: str, file_size: int) -> Dict[str, Any]:
    """Check if file is a duplicate based on hash, filename, and size"""
    try:
        # First check by file hash (most reliable)
        if file_hash:
            hash_result = db_manager.execute_query(
                "SELECT id, filename, upload_date FROM documents WHERE file_hash = ?",
                (file_hash,)
            )
            if hash_result:
                doc = dict(hash_result[0])
                return {
                    'is_duplicate': True,
                    'match_type': 'content',
                    'existing_document': doc,
                    'message': f"Identical file content already exists (Document ID: {doc['id']})"
                }
        
        # Secondary check by filename and size
        name_size_result = db_manager.execute_query(
            "SELECT id, filename, upload_date FROM documents WHERE original_filename = ? AND file_size = ?",
            (filename, file_size)
        )
        if name_size_result:
            doc = dict(name_size_result[0])
            return {
                'is_duplicate': True,
                'match_type': 'name_size',
                'existing_document': doc,
                'message': f"File with same name and size already exists (Document ID: {doc['id']})"
            }
        
        # Check for similar filename (optional warning)
        similar_result = db_manager.execute_query(
            "SELECT id, filename, upload_date FROM documents WHERE original_filename = ?",
            (filename,)
        )
        if similar_result:
            doc = dict(similar_result[0])
            return {
                'is_duplicate': False,
                'is_similar': True,
                'match_type': 'name_only',
                'existing_document': doc,
                'message': f"File with same name already exists but different size (Document ID: {doc['id']})"
            }
        
        return {'is_duplicate': False, 'is_similar': False}
        
    except Exception as e:
        logger.error(f"Error checking for duplicates: {e}")
        return {'is_duplicate': False, 'error': str(e)}
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

def parse_extracted_data(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Parse extracted_data JSON string safely"""
    if 'extracted_data' in doc and isinstance(doc['extracted_data'], str):
        try:
            doc['extracted_data'] = json.loads(doc['extracted_data'])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse extracted_data for document: {doc.get('id', 'unknown')}")
            doc['extracted_data'] = {}
    elif 'extracted_data' not in doc or doc['extracted_data'] is None:
        doc['extracted_data'] = {}
    return doc

def get_dashboard_stats() -> Dict[str, Any]:
    """Get comprehensive dashboard statistics"""
    try:
        # Get total documents count
        total_result = db_manager.execute_query("SELECT COUNT(*) FROM documents")
        total_documents = total_result[0][0] if total_result else 0
        
        # Get completed documents count
        completed_result = db_manager.execute_query("SELECT COUNT(*) FROM documents WHERE status = 'completed'")
        completed = completed_result[0][0] if completed_result else 0
        
        # Get pending documents count
        pending_result = db_manager.execute_query("SELECT COUNT(*) FROM documents WHERE status = 'pending'")
        pending = pending_result[0][0] if pending_result else 0
        
        # Get failed documents count
        failed_result = db_manager.execute_query("SELECT COUNT(*) FROM documents WHERE status = 'failed'")
        failed = failed_result[0][0] if failed_result else 0
        
        # Get processing documents count
        processing_result = db_manager.execute_query("SELECT COUNT(*) FROM documents WHERE status = 'processing'")
        processing = processing_result[0][0] if processing_result else 0
        
        # Calculate average amount from extracted data
        avg_amount = 0.0
        total_amount = 0.0
        amount_count = 0
        
        try:
            # Get all completed documents with extracted data
            docs_with_data = db_manager.execute_query(
                "SELECT extracted_data FROM documents WHERE status = 'completed' AND extracted_data IS NOT NULL"
            )
            
            for row in docs_with_data:
                if row[0]:  # extracted_data is not null
                    try:
                        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        if isinstance(data, dict):
                            # Try different possible amount fields
                            amount = None
                            for field in ['total_amount', 'amount', 'total', 'invoice_total']:
                                if field in data and data[field] is not None:
                                    try:
                                        # Handle string amounts by removing currency symbols
                                        amount_str = str(data[field]).replace('$', '').replace(',', '').strip()
                                        amount = float(amount_str)
                                        break
                                    except (ValueError, TypeError):
                                        continue
                            
                            if amount and amount > 0:
                                total_amount += amount
                                amount_count += 1
                    except (json.JSONDecodeError, TypeError, KeyError):
                        continue
            
            if amount_count > 0:
                avg_amount = total_amount / amount_count
                
        except Exception as e:
            logger.warning(f"Error calculating average amount: {e}")
        
        stats = {
            'total_documents': total_documents,
            'completed': completed,
            'pending': pending,
            'failed': failed,
            'processing': processing,
            'avg_amount': avg_amount,
            'total_amount': total_amount
        }
        
        logger.info(f"Dashboard stats calculated: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {
            'total_documents': 0,
            'completed': 0,
            'pending': 0,
            'failed': 0,
            'processing': 0,
            'avg_amount': 0.0,
            'total_amount': 0.0
        }

# --- Web Routes ---
@web.route('/')
def index():
    """Main dashboard page"""
    try:
        # Get recent documents
        recent_docs_raw = db_manager.execute_query(
            "SELECT * FROM documents ORDER BY upload_date DESC LIMIT 10"
        )
        
        # Convert to list of dicts and parse JSON
        recent_docs = []
        for doc_row in recent_docs_raw:
            doc_dict = dict(doc_row)
            doc_dict = parse_extracted_data(doc_dict)
            recent_docs.append(doc_dict)

        # Get comprehensive stats
        stats = get_dashboard_stats()
        
        logger.info(f"Dashboard loaded with {len(recent_docs)} recent docs and stats: {stats}")

        return render_template('dashboard.html',
                               recent_docs=recent_docs,
                               stats=stats)
    except Exception as e:
        logger.error(f'Error loading dashboard: {str(e)}')
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html', 
                             recent_docs=[], 
                             stats={
                                 'total_documents': 0,
                                 'completed': 0,
                                 'pending': 0,
                                 'failed': 0,
                                 'processing': 0,
                                 'avg_amount': 0.0
                             })

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
            doc_dict = parse_extracted_data(doc_dict)
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
        return render_template('documents.html', 
                             documents=[], 
                             page=1, 
                             per_page=per_page, 
                             total=0, 
                             status_filter=status_filter)

@web.route('/document/<int:doc_id>')
def document_detail(doc_id: int):
    """Document detail page"""
    try:
        doc = db_manager.get_document(doc_id)
        
        if not doc:
            flash('Document not found', 'error')
            return redirect(url_for('web.documents_list'))
        
        # Parse extracted_data JSON string to dict for display
        doc = parse_extracted_data(doc)
        
        line_items = doc['extracted_data'].get('line_items', [])
        processing_log = []  # Placeholder - you might want to implement this

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
    """Upload file endpoint with duplicate detection"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Get original filename and check force upload flag
        original_filename = file.filename
        force_upload = request.form.get('force_upload', 'false').lower() == 'true'
        
        # Save file temporarily to check for duplicates
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        unique_filename = f"{timestamp}{filename}"
        
        upload_folder = config.get('processing', 'upload_folder', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        temp_filepath = os.path.join(upload_folder, unique_filename)
        file.save(temp_filepath)
        
        # Get file info and hash
        file_info = get_file_info(temp_filepath)
        file_hash = get_file_hash(temp_filepath)
        
        # Check for duplicates unless force upload is enabled
        if not force_upload:
            duplicate_check = check_duplicate_file(original_filename, file_hash, file_info['size'])
            
            if duplicate_check.get('is_duplicate', False):
                # Remove the temporarily saved file
                try:
                    os.remove(temp_filepath)
                except:
                    pass
                
                return jsonify({
                    'error': 'Duplicate file detected',
                    'duplicate_info': duplicate_check,
                    'suggestion': 'Use force_upload=true to upload anyway'
                }), 409  # Conflict status code
            
            elif duplicate_check.get('is_similar', False):
                # Log warning but continue with upload
                logger.warning(f"Similar file detected: {duplicate_check['message']}")
        
        # Proceed with upload - file is already saved at temp_filepath
        final_filepath = temp_filepath  # Use the temp path as final path
        
        # Insert document record with file hash
        doc_data = {
            'filename': unique_filename,
            'original_filename': original_filename,
            'file_path': final_filepath,
            'file_size': file_info['size'],
            'content_type': file_info['mime_type'],
            'status': 'pending',
            'file_hash': file_hash  # Store the hash for future duplicate detection
        }
        
        doc_id = db_manager.store_document(doc_data)
        
        logger.info(f"Document uploaded with ID {doc_id}: {unique_filename} (hash: {file_hash[:8]}...)")
        
        # Start processing if enabled
        auto_process = request.form.get('auto_process', 'true').lower() == 'true'
        if auto_process and doc_processor:
            try:
                logger.info(f"Starting automatic processing for document ID {doc_id}")
                # Update status to processing
                db_manager.update_document(doc_id, status='processing')
                
                result = doc_processor.process_document_by_id(doc_id)
                logger.info(f"Processing result for doc {doc_id}: {result}")
                
                # Update status based on result
                if result and result.get('success', False):
                    db_manager.update_document(doc_id, status='completed')
                else:
                    error_msg = result.get('error', 'Processing failed') if result else 'Unknown processing error'
                    db_manager.update_document(doc_id, status='failed', error_message=error_msg)
                    
            except Exception as e:
                logger.error(f"Processing error for doc {doc_id}: {e}")
                try:
                    db_manager.update_document(doc_id, status='failed', error_message=str(e))
                except Exception as db_error:
                    logger.error(f"Failed to update document status to failed: {db_error}")
        
        response_data = {
            'success': True,
            'document_id': doc_id,
            'filename': unique_filename,
            'message': 'File uploaded successfully'
        }
        
        # Include duplicate warning if similar file was found
        duplicate_check = check_duplicate_file(original_filename, file_hash, file_info['size'])
        if duplicate_check.get('is_similar', False):
            response_data['warning'] = duplicate_check['message']
        
        return jsonify(response_data), 201
        
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
        
        # Convert to list of dicts and parse JSON
        documents_list = []
        for doc in documents:
            doc_dict = dict(doc)
            doc_dict = parse_extracted_data(doc_dict)
            documents_list.append(doc_dict)
        
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
        
        # Parse extracted data
        doc = parse_extracted_data(doc)
        
        return jsonify({'document': doc})
        
    except Exception as e:
        logger.error(f'Error getting document {doc_id}: {str(e)}')
        return jsonify({'error': str(e)}), 500

@api.route('/document/<int:doc_id>/reprocess', methods=['POST'])
def reprocess_document(doc_id: int):
    """Reprocess a document via API"""
    try:
        doc = db_manager.get_document(doc_id)
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        
        if not doc_processor:
            return jsonify({'error': 'Document processor not available'}), 500
        
        # Update status to processing
        db_manager.update_document(doc_id, status='processing')
        
        try:
            result = doc_processor.process_document_by_id(doc_id)
            
            if result and result.get('success', False):
                db_manager.update_document(doc_id, status='completed')
                return jsonify({
                    'success': True,
                    'message': 'Document reprocessed successfully',
                    'result': result
                })
            else:
                error_msg = result.get('error', 'Processing failed') if result else 'Unknown processing error'
                db_manager.update_document(doc_id, status='failed', error_message=error_msg)
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 500
                
        except Exception as e:
            logger.error(f"Reprocessing error for doc {doc_id}: {e}")
            db_manager.update_document(doc_id, status='failed', error_message=str(e))
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        
    except Exception as e:
        logger.error(f'Error reprocessing document {doc_id}: {str(e)}')
        return jsonify({'error': str(e)}), 500

@api.route('/stats', methods=['GET'])
def get_stats():
    """Get processing statistics via API"""
    try:
        stats = get_dashboard_stats()
        return jsonify({'stats': stats})
        
    except Exception as e:
        logger.error(f'Error getting stats: {str(e)}')
        return jsonify({'error': str(e)}), 500

@api.route('/check-duplicate', methods=['POST'])
def check_duplicate():
    """Check if a file would be a duplicate before uploading"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save file temporarily to calculate hash
        filename = secure_filename(file.filename)
        temp_filename = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        
        upload_folder = config.get('processing', 'upload_folder', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        temp_filepath = os.path.join(upload_folder, temp_filename)
        file.save(temp_filepath)
        
        try:
            # Get file info and hash
            file_info = get_file_info(temp_filepath)
            file_hash = get_file_hash(temp_filepath)
            
            # Check for duplicates
            duplicate_check = check_duplicate_file(file.filename, file_hash, file_info['size'])
            
            return jsonify({
                'filename': file.filename,
                'file_size': file_info['size'],
                'file_hash': file_hash[:8] + '...',  # Show partial hash for reference
                'duplicate_check': duplicate_check
            })
            
        finally:
            # Always clean up temp file
            try:
                os.remove(temp_filepath)
            except:
                pass
        
    except Exception as e:
        logger.error(f'Duplicate check failed: {str(e)}')
        return jsonify({'error': f'Duplicate check failed: {str(e)}'}), 500
    """Force refresh of dashboard statistics"""
    try:
        stats = get_dashboard_stats()
        logger.info(f"Stats refreshed: {stats}")
        return jsonify({
            'success': True,
            'stats': stats,
            'message': 'Statistics refreshed successfully'
        })
    except Exception as e:
        logger.error(f'Error refreshing stats: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
