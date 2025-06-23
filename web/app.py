# web/app.py

# Add project root to Python path
#import sys
#import os
#sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify
import os
import logging
from datetime import datetime
import secrets

from config.settings import Config
#from config/settings.py import Config
from database.connection import DatabaseManager
from processing.document_processor import DocumentProcessor

# Configuration flag to choose routing approach
USE_MODULAR_ROUTES = False  # Set to True to use new modular structure

if USE_MODULAR_ROUTES:
    # New modular structure imports
    from web.routes import create_api_blueprint, create_web_blueprint, create_config_blueprint
else:
    # Legacy monolithic structure imports
    from web.legacy_routes import api, web, init_routes

def create_app(config_path: str = None) -> Flask:
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    config = Config(config_path)
    
    # Configure Flask app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', config.get('web_interface', 'secret_key', fallback=secrets.token_hex(32)))
    app.config['MAX_CONTENT_LENGTH'] = int(config.get('processing', 'max_file_size', '10485760'))
    app.config['UPLOAD_FOLDER'] = config.get('processing', 'upload_folder', 'uploads')
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize database
    db_manager = DatabaseManager(config)
    
    # Initialize document processor
    doc_processor = DocumentProcessor(config, db_manager)
    
    # Initialize and register routes based on configuration
    #if USE_MODULAR_ROUTES:
        # New modular approach - create blueprints with factory functions
        # api_blueprint = create_api_blueprint(config, db_manager, doc_processor)
        # web_blueprint = create_web_blueprint(config, db_manager, doc_processor)
        # config_blueprint = create_config_blueprint(config, db_manager, doc_processor)
        
        # Register the created blueprints
        # app.register_blueprint(api_blueprint)
        # app.register_blueprint(web_blueprint)
        # app.register_blueprint(config_blueprint)

    if USE_MODULAR_ROUTES:
        # New modular approach - create blueprints with factory functions
        api_blueprint = create_api_blueprint(config, db_manager, doc_processor)
        web_blueprint = create_web_blueprint(config, db_manager, doc_processor)
        
        # Register the created blueprints (no separate config blueprint)
        app.register_blueprint(api_blueprint)
        app.register_blueprint(web_blueprint)
        
        app.logger.info("Using modular route structure")
    else:
        # Legacy approach - global variable injection
        init_routes(config, db_manager, doc_processor)
        
        # Register the pre-created blueprints
        app.register_blueprint(api)
        app.register_blueprint(web)
        
        app.logger.info("Using legacy monolithic route structure")
    
    # Configure logging
    setup_logging(app, config)
    
    # Add template filters
    @app.template_filter('datetime')
    def datetime_filter(value):
        """Format datetime for templates"""
        if value is None:
            return 'N/A'
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                return value
        return value.strftime('%Y-%m-%d %H:%M:%S')
    
    @app.template_filter('currency')
    def currency_filter(value):
        """Format currency for templates"""
        if value is None:
            return 'N/A'
        try:
            return f"${float(value):,.2f}"
        except:
            return str(value)
    
    @app.template_filter('filesize')
    def filesize_filter(value):
        """Format file size for templates"""
        if value is None:
            return 'N/A'
        try:
            size = int(value)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except:
            return str(value)
    
    # Add template globals
    @app.context_processor
    def inject_globals():
        """Inject global variables into templates"""
        return {
            'app_name': 'Paperless-BigCapital Middleware',
            'current_year': datetime.now().year
        }
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/5
