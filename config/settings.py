# config/settings.py

import os
import configparser
from pathlib import Path
# Import the PaperlessConfigHandler from the new module
# Ensure config/paperless/__init__.py exists (can be an empty file)
# for config.paperless to be treated as a package.
from config.paperless.settings import PaperlessConfigHandler # Correct import path assuming it's a class in that file

class Config:
    def __init__(self, config_file='config/config.ini'):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.load_config()
        # Initialize the PaperlessConfigHandler instance, passing this Config instance
        # so it can access the loaded configparser object
        self.paperless_config_handler = PaperlessConfigHandler(self)

    def load_config(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self._create_default_config()

    def _create_default_config(self):
        """
        Creates a default config.ini file with predefined settings.
        This method is called if config.ini does not exist on startup.
        """
        self.config['database'] = {
            'type': 'sqlite',
            'path': 'data/middleware.db'
        }
        
        # --- EXTENDED MODE SECTION ---
        self.config['extended'] = {
            'enabled': 'false'
        }
        
        self.config['ocr'] = {
            'language': 'eng',
            'confidence_threshold': '60',
            'dpi': '300'
        }
        self.config['processing'] = {
            'upload_folder': 'uploads',
            'max_file_size': '10485760',
            'allowed_extensions': 'pdf,png,jpg,jpeg,tiff',
            # Set the default check interval to 10 seconds
            'check_interval_seconds': '10',
            'log_level': 'INFO',
            'processed_tag': 'ProcessedByMiddleware',
            'error_tag': 'ErrorProcessing'
        }
        self.config['web_interface'] = {
            'host': '0.0.0.0',
            'port': '5000',
            'debug': 'false',
            'secret_key': 'dev-secret-key-change-in-production'
        }
        self.config['logging'] = {
            'level': 'INFO',
            'file': 'logs/middleware.log'
        }
        self.config['currency'] = {
            'default': 'USD',
            'supported': 'USD,EUR,GBP,AUD,CAD'
        }
        # --- PAPERLESS-NGX SECTION ---
        self.config['paperless'] = {
            'api_url': 'http://paperless-ngx:8000/api/',
            'api_token': 'YOUR_GENERATED_API_TOKEN', # Placeholder for default creation
            'invoice_tags': 'Invoice,ProcessedByMiddleware',
            'receipt_tags': 'Receipt,ProcessedByMiddleware'
        }
        # --- BIGCAPITAL SECTION ---
        self.config['bigcapital'] = {
            'api_url': 'http://bigcapital:3000/api/',
            'api_token': 'YOUR_BIGCAPITAL_API_TOKEN',
            # Set the default due days to 7
            'default_due_days': '7',
            'auto_create_customers': 'false'
        }
        # Ensure the directory for config_file exists before writing
        config_dir = os.path.dirname(self.config_file)
        os.makedirs(config_dir, exist_ok=True)
        
        with open(self.config_file, 'w') as f:
            self.config.write(f)

    def get(self, section, key, fallback=None):
        """Get a configuration value."""
        return self.config.get(section, key, fallback=fallback)

    def getint(self, section, key, fallback=None):
        """Get an integer configuration value."""
        return self.config.getint(section, key, fallback=fallback)

    def getboolean(self, section, key, fallback=None):
        """Get a boolean configuration value."""
        return self.config.getboolean(section, key, fallback=fallback)

    def set(self, section, key, value):
        """Set a configuration value."""
        # Ensure section exists
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        # Set the value
        self.config.set(section, key, str(value))

    def save(self):
        """Save configuration changes to file."""
        # Ensure the directory exists
        config_dir = os.path.dirname(self.config_file)
        os.makedirs(config_dir, exist_ok=True)
        
        # Write the configuration to file
        with open(self.config_file, 'w') as f:
            self.config.write(f)

    # Add specific getters for Paperless-ngx settings, delegating to the handler
    def get_paperless_api_url(self):
        """Get the Paperless-ngx API URL."""
        return self.paperless_config_handler.get_api_url()

    def get_paperless_api_token(self):
        """Get the Paperless-ngx API token."""
        return self.paperless_config_handler.get_api_token()

    def get_invoice_tags(self):
        """Get the invoice tags for Paperless-ngx."""
        return self.paperless_config_handler.get_invoice_tags()

    def get_receipt_tags(self):
        """Get the receipt tags for Paperless-ngx."""
        return self.paperless_config_handler.get_receipt_tags()
