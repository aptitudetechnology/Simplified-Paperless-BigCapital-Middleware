from flask import Blueprint, render_template, redirect, url_for, flash, request
import logging
from .utils import parse_extracted_data, get_dashboard_stats

logger = logging.getLogger(__name__)

def create_web_blueprint(config, db_manager, doc_processor):
    """Create and configure the web routes blueprint"""
    web = Blueprint('web', __name__)
    
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
            stats = get_dashboard_stats(db_manager)
            
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
                                    'avg_amount': 0.0,
                                    'total_amount': 0.0
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
    
    return web
