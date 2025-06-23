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
        # ... (implementation similar to original but using passed dependencies)
        pass
    
    @api.route('/documents', methods=['GET'])
    def get_documents():
        """Get documents list via API"""
        # ... implementation
        pass
    
    # ... other API routes
    
    return api
