# web/routes/api_routes.py
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os
from datetime import datetime
import logging
from .utils import allowed_file, get_file_hash, check_duplicate_file, parse_extracted_data, get_dashboard_stats

logger = logging.getLogger(__name__)

def create_api_blueprint(config, db_manager, doc_processor):
    """Create and configure the API routes blueprint"""
    api = Blueprint('api', __name__, url_prefix='/api')
    
    @api.route('/upload', methods=['POST'])
    def upload_file():
        """Upload file endpoint with duplicate detection"""
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not allowed_file(file.filename, config):
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
            
            # Get file info using DocumentProcessor method
            file_info = doc_processor.get_file_info(temp_filepath)
            file_hash = get_file_hash(temp_filepath)
            
            # Check for duplicates unless force upload is enabled
            if not force_upload:
                duplicate_check = check_duplicate_file(original_filename, file_hash, file_info['file_size'], db_manager)
                
                if duplicate_check.get('is_duplicate', False):
                    # Remove the temporarily saved file
                    try:
                        os.remove(temp_filepath)
                    except Exception as e:
                        logger.warning(f"Failed to remove temp file {temp_filepath}: {e}")
                    
                    return jsonify({
                        'error': 'Duplicate file detected',
                        'duplicate_info': duplicate_check,
                        'suggestion': 'Use force_upload=true to upload anyway'
                    }), 409
                
                elif duplicate_check.get('is_similar', False):
                    # Log warning but continue with upload
                    logger.warning(f"Similar file detected: {duplicate_check['message']}")
            
            # Proceed with upload - file is already saved at temp_filepath
            final_filepath = temp_filepath
            
            # Insert document record with file hash
            doc_data = {
                'filename': unique_filename,
                'original_filename': original_filename,
                'file_path': final_filepath,
                'file_size': file_info['file_size'],
                'content_type': file_info.get('mime_type', 'application/octet-stream'),
                'status': 'pending',
                'file_hash': file_hash
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
            final_duplicate_check = check_duplicate_file(original_filename, file_hash, file_info['file_size'], db_manager)
            if final_duplicate_check.get('is_similar', False):
                response_data['warning'] = final_duplicate_check['message']
            
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
            stats = get_dashboard_stats(db_manager)
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
                # Get file info using DocumentProcessor method
                file_info = doc_processor.get_file_info(temp_filepath)
                file_hash = get_file_hash(temp_filepath)
                
                # Check for duplicates
                duplicate_check = check_duplicate_file(file.filename, file_hash, file_info['file_size'], db_manager)
                
                return jsonify({
                    'filename': file.filename,
                    'file_size': file_info['file_size'],
                    'file_hash': file_hash[:8] + '...',  # Show partial hash for reference
                    'duplicate_check': duplicate_check
                })
                
            finally:
                # Always clean up temp file
                try:
                    os.remove(temp_filepath)
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {temp_filepath}: {e}")
            
        except Exception as e:
            logger.error(f'Duplicate check failed: {str(e)}')
            return jsonify({'error': f'Duplicate check failed: {str(e)}'}), 500

    @api.route('/stats/refresh', methods=['POST'])
    def refresh_stats():
        """Force refresh of dashboard statistics"""
        try:
            stats = get_dashboard_stats(db_manager)
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
    
    return api
