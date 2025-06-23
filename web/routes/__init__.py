from flask import Blueprint
from config.settings import Config
from database.connection import DatabaseManager
from processing.document_processor import DocumentProcessor
import logging

# Import route modules
from .web_routes import create_web_blueprint
from .api_routes import create_api_blueprint
from .config_routes import create_config_blueprint

logger = logging.getLogger(__name__)

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
    logger.info("Routes initialized with dependencies.")

def get_blueprints():
    """Return all blueprints for registration with Flask app"""
    if not config or not db_manager or not doc_processor:
        raise RuntimeError("Routes must be initialized before getting blueprints")
    
    return [
        create_web_blueprint(config, db_manager, doc_processor),
        create_api_blueprint(config, db_manager, doc_processor),
        create_config_blueprint(config, db_manager, doc_processor)
    ]
