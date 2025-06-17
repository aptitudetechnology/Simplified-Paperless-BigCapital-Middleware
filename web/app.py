# web/app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import os
import uuid
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from config.settings import Config
from database.connection import DatabaseManager
from core.processor import DocumentProcessor
from database.models import Document, ProcessingStats
from utils.logger import setup_logging, get_logger
from utils.exceptions import ProcessingError, OCRProcessingError
from datetime import datetime
import mimetypes

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    config = Config()
    setup_logging(config)
    logger = get_logger(__name__)
    
    # Flask configuration
    app.config['SECRET_KEY'] = config.get('web_interface', 'secret_key')
    app.config['MAX_CONTENT_LENGTH'] = config.getint('processing', 'max_file_size')
    app.config['UPLOAD_FOLDER'] = config.get('processing', 'upload_folder')
    
    # Initialize database and processor
    db_manager = DatabaseManager(config)
    processor = DocumentProcessor(config, db_manager)
    
    # Allowed file extensions
    allowed_extensions = set(config.get('processing', 'allowed_extensions').split(','))
    
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in allowed_extensions
    
    @app.route('/')
    def index():
        """Main upload interface"""
        return render_template('index.html', 
                             allowed_extensions=', '.join(allowed_extensions),
                             max_size_mb=app.config['MAX_CONTENT_LENGTH'] // (1024*1024))
    
    @app.route('/upload', methods=['POST'])
    def upload_file():
        """Handle file upload and processing"""
        try:
            if 'file' not in request.files:
                flash('No file selected', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)
            
            if not allowed_file(file.filename):
                flash(f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}', 'error')
                return redirect(request.url)
            
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Ensure upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Save file
            file.save(file_path)
            logger.info(f"File uploaded: {original_filename} -> {file_path}")
            
            # Process document
            try:
                document = processor.process_document(file_path, original_filename)
                flash(f'Document "{original_filename}" processed successfully!', 'success')
                return redirect(url_for('view_document', doc_id=document.id))
            
            except (ProcessingError, OCRProcessingError) as e:
                flash(f'Processing failed: {str(e)}', 'error')
                return redirect(url_for('index'))
            
        except RequestEntityTooLarge:
            flash('File too large. Maximum size is 10MB.', 'error')
            return redirect(url_for('index'))
        
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            flash('An unexpected error occurred during upload.', 'error')
            return redirect(url_for('index'))
    
    @app.route('/documents')
    def list_documents():
        """List all processed documents"""
        session = db_manager.get_session()
        try:
            documents = session.query(Document).order_by(Document.upload_date.desc()).limit(50).all()
            return render_template('documents.html', documents=documents)
        finally:
            session.close()
    
    @app.route('/document/<int:doc_id>')
    def view_document(doc_id):
        """View specific document details"""
        session = db_manager.get_session()
        try:
            document = session.query(Document).filter(Document.id == doc_id).first()
            if not document:
                flash('Document not found', 'error')
                return redirect(url_for('list_documents'))
            
            return render_template('document_detail.html', document=document)
        finally:
            session.close()
    
    @app.route('/api/stats')
    def api_stats():
        """API endpoint for processing statistics"""
        session = db_manager.get_session()
        try:
            # Get today's stats
            today = datetime.now().date()
            today_stats = session.query(ProcessingStats).filter(
                ProcessingStats.date >= datetime.combine(today, datetime.min.time())
            ).first()
            
            # Get total document count
            total_documents = session.query(Document).count()
            completed_documents = session.query(Document).filter(Document.status == 'completed').count()
            failed_documents = session.query(Document).filter(Document.status == 'failed').count()
            
            return jsonify({
                'total_documents': total_documents,
                'completed_documents': completed_documents,
                'failed_documents': failed_documents,
                'success_rate': (completed_documents / total_documents * 100) if total_documents > 0 else 0,
                'today_processed': today_stats.documents_processed if today_stats else 0,
                'today_successful': today_stats.successful_extractions if today_stats else 0,
                'today_failed': today_stats.failed_extractions if today_stats else 0,
                'avg_processing_time': today_stats.avg_processing_time if today_stats else 0
            })
        finally:
            session.close()
    
    @app.route('/api/document/<int:doc_id>')
    def api_document(doc_id):
        """API endpoint for document data"""
        session = db_manager.get_session()
        try:
            document = session.query(Document).filter(Document.id == doc_id).first()
            if not document:
                return jsonify({'error': 'Document not found'}), 404
            
            return jsonify({
                'id': document.id,
                'filename': document.original_filename,
                'status': document.status,
                'upload_date': document.upload_date.isoformat() if document.upload_date else None,
                'processed_date': document.processed_date.isoformat() if document.processed_date else None,
                'vendor_name': document.vendor_name,
                'invoice_number': document.invoice_number,
                'invoice_date': document.invoice_date.isoformat() if document.invoice_date else None,
                'total_amount': document.total_amount,
                'currency': document.currency,
                'ocr_confidence': document.ocr_confidence,
                'extraction_method': document.extraction_method,
                'processing_error': document.processing_error
            })
        finally:
            session.close()
    
    @app.errorhandler(413)
    def too_large(e):
        flash('File is too large. Maximum size is 10MB.', 'error')
        return redirect(url_for('index'))
    
    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal server error: {str(e)}")
        flash('An internal server error occurred.', 'error')
        return redirect(url_for('index'))
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    # Load configuration for host and port
    config = Config()
    host = config.get('web_interface', 'host', '0.0.0.0')
    port = config.getint('web_interface', 'port', 5000)
    debug = config.getboolean('web_interface', 'debug', False)
    
    app.run(host=host, port=port, debug=debug)

# web/templates/base.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Paperless-BigCapital Middleware{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="{{ url_for('static', filename='css/style.css') }}" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                <i class="fas fa-file-invoice me-2"></i>
                Paperless-BigCapital
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('index') }}">
                            <i class="fas fa-upload me-1"></i>Upload
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('list_documents') }}">
                            <i class="fas fa-list me-1"></i>Documents
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <main class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>

    <footer class="bg-light mt-5 py-4">
        <div class="container text-center">
            <p class="mb-0">&copy; 2024 Paperless-BigCapital Middleware - Phase 1</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>

# web/templates/index.html
{% extends "base.html" %}

{% block title %}Upload Document - Paperless-BigCapital{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">
                    <i class="fas fa-cloud-upload-alt me-2"></i>
                    Upload Invoice or Receipt
                </h4>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('upload_file') }}" enctype="multipart/form-data" id="uploadForm">
                    <div class="mb-3">
                        <label for="file" class="form-label">Select Document</label>
                        <input type="file" class="form-control" id="file" name="file" accept=".pdf,.png,.jpg,.jpeg,.tiff" required>
                        <div class="form-text">
                            Supported formats: {{ allowed_extensions }}<br>
                            Maximum file size: {{ max_size_mb }}MB
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <div class="progress" id="uploadProgress" style="display: none;">
                            <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-primary" id="uploadBtn">
                        <i class="fas fa-upload me-2"></i>
                        Upload and Process
                    </button>
                    
                    <button type="button" class="btn btn-secondary" id="processingBtn" style="display: none;" disabled>
                        <i class="fas fa-spinner fa-spin me-2"></i>
                        Processing...
                    </button>
                </form>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body text-center">
                        <i class="fas fa-eye fa-2x text-primary mb-3"></i>
                        <h5>OCR Processing</h5>
                        <p class="text-muted">Automatically extract text from your documents using Tesseract OCR</p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body text-center">
                        <i class="fas fa-search fa-2x text-success mb-3"></i>
                        <h5>Data Extraction</h5>
                        <p class="text-muted">Intelligently parse vendor names, amounts, dates, and invoice numbers</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row mt-5">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-chart-bar me-2"></i>
                    Processing Statistics
                </h5>
            </div>
            <div class="card-body">
                <div class="row" id="statsContainer">
                    <div class="col-md-3">
                        <div class="stat-item">
                            <div class="stat-number" id="totalDocs">-</div>
                            <div class="stat-label">Total Documents</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-item">
                            <div class="stat-number text-success" id="successRate">-</div>
                            <div class="stat-label">Success Rate</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-item">
                            <div class="stat-number text-info" id="todayProcessed">-</div>
                            <div class="stat-label">Today Processed</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-item">
                            <div class="stat-number text-warning" id="avgTime">-</div>
                            <div class="stat-label">Avg Time (s)</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    
    // Handle form submission
    document.getElementById('uploadForm').addEventListener('submit', function() {
        document.getElementById('uploadBtn').style.display = 'none';
        document.getElementById('processingBtn').style.display = 'inline-block';
        document.getElementById('uploadProgress').style.display = 'block';
        
        // Simulate progress (real implementation would use AJAX)
        let progress = 0;
        const progressBar = document.querySelector('.progress-bar');
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            progressBar.style.width = progress + '%';
        }, 500);
        
        // Clear interval when form actually submits
        setTimeout(() => clearInterval(interval), 10000);
    });
});

function loadStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            document.getElementById('totalDocs').textContent = data.total_documents;
            document.getElementById('successRate').textContent = data.success_rate.toFixed(1) + '%';
            document.getElementById('todayProcessed').textContent = data.today_processed;
            document.getElementById('avgTime').textContent = data.avg_processing_time.toFixed(2);
        })
        .catch(error => console.error('Error loading stats:', error));
}
</script>
{% endblock %}

# web/templates/documents.html
{% extends "base.html" %}

{% block title %}Documents - Paperless-BigCapital{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2>
        <i class="fas fa-file-alt me-2"></i>
        Processed Documents
    </h2>
    <a href="{{ url_for('index') }}" class="btn btn-primary">
        <i class="fas fa-plus me-2"></i>
        Upload New Document
    </a>
</div>

{% if documents %}
<div class="card">
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Document</th>
                        <th>Status</th>
                        <th>Vendor</th>
                        <th>Amount</th>
                        <th>Date</th>
                        <th>Uploaded</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for doc in documents %}
                    <tr>
                        <td>
                            <div class="d-flex align-items-center">
                                <i class="fas fa-file-pdf text-danger me-2"></i>
                                <div>
                                    <div class="fw-bold">{{ doc.original_filename }}</div>
                                    <small class="text-muted">{{ doc.file_size | filesizeformat }}</small>
                                </div>
                            </div>
                        </td>
                        <td>
                            {% if doc.status == 'completed' %}
                                <span class="badge bg-success">Completed</span>
                            {% elif doc.status == 'failed' %}
                                <span class="badge bg-danger">Failed</span>
                            {% elif doc.status == 'processing' %}
                                <span class="badge bg-warning">Processing</span>
                            {% else %}
                                <span class="badge bg-secondary">{{ doc.status.title() }}</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if doc.vendor_name %}
                                {{ doc.vendor_name }}
                            {% else %}
                                <span class="text-muted">-</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if doc.total_amount %}
                                {{ doc.currency or 'USD' }} {{ "%.2f"|format(doc.total_amount) }}
                            {% else %}
                                <span class="text-muted">-</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if doc.invoice_date %}
                                {{ doc.invoice_date.strftime('%Y-%m-%d') }}
                            {% else %}
                                <span class="text-muted">-</span>
                            {% endif %}
                        </td>
                        <td>
                            <small class="text-muted">
                                {{ doc.upload_date.strftime('%Y-%m-%d %H:%M') if doc.upload_date else '-' }}
                            </small>
                        </td>
                        <td>
                            <a href="{{ url_for('view_document', doc_id=doc.id) }}" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-eye"></i>
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% else %}
<div class="text-center py-5">
    <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
    <h4>No Documents Yet</h4>
    <p class="text-muted">Upload your first invoice or receipt to get started.</p>
    <a href="{{ url_for('index') }}" class="btn btn-primary">
        <i class="fas fa-upload me-2"></i>
        Upload Document
    </a>
</div>
{% endif %}
{% endblock %}

# web/templates/document_detail.html
{% extends "base.html" %}

{% block title %}{{ document.original_filename }} - Paperless-BigCapital{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-file-alt me-2"></i>
                    {{ document.original_filename }}
                </h5>
            </div>
            <div class="card-body">
                <div class="row mb-3">
                    <div class="col-sm-3"><strong>Status:</strong></div>
                    <div class="col-sm-9">
                        {% if document.status == 'completed' %}
                            <span class="badge bg-success">Completed</span>
                        {% elif document.status == 'failed' %}
                            <span class="badge bg-danger">Failed</span>
                        {% elif document.status == 'processing' %}
                            <span class="badge bg-warning">Processing</span>
                        {% else %}
                            <span class="badge bg-secondary">{{ document.status.title() }}</span>
                        {% endif %}
                    </div>
                </div>
                
                <div class="row mb-3">
                    <div class="col-sm-3"><strong>Upload Date:</strong></div>
                    <div class="col-sm-9">{{ document.upload_date.strftime('%Y-%m-%d %H:%M:%S') if document.upload_date else '-' }}</div>
                </div>
                
                <div class="row mb-3">
                    <div class="col-sm-3"><strong>Processed Date:</strong></div>
                    <div class="col-sm-9">{{ document.processed_date.strftime('%Y-%m-%d %H:%M:%S') if document.processed_date else '-' }}</div>
                </div>
                
                <div class="row mb-3">
                    <div class="col-sm-3"><strong>File Size:</strong></div>
                    <div class="col-sm-9">{{ document.file_size | filesizeformat }}</div>
                </div>
                
                {% if document.processing_error %}
                <div class="alert alert-danger">
                    <strong>Processing Error:</strong><br>
                    {{ document.processing_error }}
                </div>
                {% endif %}
            </div>
        </div>
        
        {% if document.ocr_text %}
        <div class="card mt-4">
            <div class="card-header">
                <h6 class="mb-0">
                    <i class="fas fa-align-left me-2"></i>
                    Extracted Text
                    {% if document.ocr_confidence %}
                        <span class="badge bg-info ms-2">{{ "%.1f"|format(document.ocr_confidence) }}% confidence</span>
                    {% endif %}
                </h6>
            </div>
            <div class="card-body">
                <pre class="ocr-text">{{ document.ocr_text }}</pre>
            </div>
        </div>
        {% endif %}
    </div>
    
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h6 class="mb-0">
                    <i class="fas fa-info-circle me-2"></i>
                    Extracted Data
                </h6>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <strong>Vendor:</strong><br>
                    {{ document.vendor_name or '-' }}
                </div>
                
                <div class="mb-3">
                    <strong>Invoice Number:</strong><br>
                    {{ document.invoice_number or '-' }}
                </div>
                
                <div class="mb-3">
                    <strong>Invoice Date:</strong><br>
                    {{ document.invoice_date.strftime('%Y-%m-%d') if document.invoice_date else '-' }}
                </div>
                
                <div class="mb-3">
                    <strong>Total Amount:</strong><br>
                    {% if document.total_amount %}
                        {{ document.currency or 'USD' }} {{ "%.2f"|format(document.total_amount) }}
                    {% else %}
                        -
                    {% endif %}
                </div>
                
                <div class="mb-3">
                    <strong>Extraction Method:</strong><br>
                    <small class="text-muted">{{ document.extraction_method or '-' }}</small>
                </div>
            </div>
        </div>
        
        <div class="card mt-3">
            <div class="card-header">
                <h6 class="mb-0">
                    <i class="fas fa-cogs me-2"></i>
                    Actions
                </h6>
            </div>
            <div class="card-body">
                <div class="d-grid gap-2">
                    <button class="btn btn-outline-primary" onclick="exportData()">
                        <i class="fas fa-download me-2"></i>
                        Export Data
                    </button>
                    <button class="btn btn-outline-secondary" onclick="reprocess()">
                        <i class="fas fa-redo me-2"></i>
                        Reprocess
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="mt-4">
    <a href="{{ url_for('list_documents') }}" class="btn btn-secondary">
        <i class="fas fa-arrow-left me-2"></i>
        Back to Documents
    </a>
</div>
{% endblock %}

{% block scripts %}
<script>
function exportData() {
    const docId = {{ document.id }};
    fetch(`/api/document/${docId}`)
        .then(response => response.json())
        .then(data => {
            const dataStr = JSON.stringify(data, null, 2);
            const dataBlob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `document_${docId}_data.json`;
            link.click();
            URL.revokeObjectURL(url);
        })
        .catch(error => {
            console.error('Error exporting data:', error);
            alert('Failed to export data');
        });
}

function reprocess() {
    alert('Reprocessing functionality will be implemented in Phase 2');
}
</script>
{% endblock %}

# web/static/css/style.css
/* Custom styles for Paperless-BigCapital Middleware */

body {
    background-color: #f8f9fa;
}

.navbar-brand {
    font-weight: bold;
}

.card {
    border: none;
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

.card-header {
    background-color: #fff;
    border-bottom: 1px solid #dee2e6;
    font-weight: 600;
}

.stat-item {
    text-align: center;
    padding: 1rem;
}

.stat-number {
    font-size: 2rem;
    font-weight: bold;
    color: #495057;
}

.stat-label {
    color: #6c757d;
    font-size: 0.875rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.ocr-text {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 0.375rem;
    padding: 1rem;
    font-size: 0.875rem;
    line-height: 1.5;
    max-height: 400px;
    overflow-y: auto;
    white-space: pre-wrap;
}

.table th {
    border-top: none;
    font-weight: 600;
    color: #495057;
}

.btn {
    border-radius: 0.375rem;
}

.progress {
    height: 8px;
}

.alert {
    border: none;
    border-radius: 0.5rem;
}

footer {
    margin-top: auto;
}

/* File upload styling */
.form-control:focus {
    border-color: #0d6efd;
    box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25);
}

/* Responsive improvements */
@media (max-width: 768px) {
    .stat-item {
        margin-bottom: 1rem;
    }
    
    .stat-number {
        font-size: 1.5rem;
    }
}

/* web/static/js/app.js */
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
    
    // File size validation
    const fileInput = document.getElementById('file');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const maxSize = 10 * 1024 * 1024; // 10MB
                if (file.size > maxSize) {
                    alert('File is too large. Maximum size is 10MB.');
                    e.target.value = '';
                }
            }
        });
    }
    
    // Refresh stats every 30 seconds
    if (typeof loadStats === 'function') {
        setInterval(loadStats, 30000);
    }
});

// Utility function to format file sizes
function formatFileSize(bytes) {
    if (bytes == 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
