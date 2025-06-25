# config/settings.py
import os
import configparser
from pathlib import Path

# Import the PaperlessConfigHandler from the new module
# Ensure config/paperless/__init__.py exists (can be an empty file)
# for config.paperless to be treated as a package.
from config.paperless.settings import PaperlessConfigHandler # Correct import path assuming it's a class in that file


class Config:
    def __init__(self, config_file='/config/config.ini'):
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
        self.config['database'] = {
            'type': 'sqlite',
            'path': 'data/middleware.db'
        }
        self.config['ocr'] = {
            'language': 'eng',
            'confidence_threshold': '60',
            'dpi': '300'
        }
        self.config['processing'] = {
            'upload_folder': 'uploads',
            'max_file_size': '10485760',
            'allowed_extensions': 'pdf,png,jpg,jpeg,tiff'
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
        # --- NEW SECTION FOR PAPERLESS-NGX (Add this back!) ---
         self.config['paperless'] = {
            'api_url': 'http://paperless-ngx:8000/api/',
            'api_token': 'YOUR_GENERATED_API_TOKEN', # Placeholder for default creation
            'invoice_tags': 'Invoice,ProcessedByMiddleware',
            'receipt_tags': 'Receipt,ProcessedByMiddleware'
        }

        # Ensure the directory for config_file exists before writing
        config_dir = os.path.dirname(self.config_file)
        os.makedirs(config_dir, exist_ok=True) # <--- Make sure this line is here

        with open(self.config_file, 'w') as f:
            self.config.write(f)
        # --- END NEW SECTION ---

        with open(self.config_file, 'w') as f:
            self.config.write(f)

    def get(self, section, key, fallback=None):
        return self.config.get(section, key, fallback=fallback)

    def getint(self, section, key, fallback=None):
        return self.config.getint(section, key, fallback=fallback)

    def getboolean(self, section, key, fallback=None):
        return self.config.getboolean(section, key, fallback=fallback)

    # Add specific getters for Paperless-ngx settings, delegating to the handler
    def get_paperless_api_url(self):
        return self.paperless_config_handler.get_api_url()

    def get_paperless_api_token(self):
        return self.paperless_config_handler.get_api_token()

    def get_invoice_tags(self):
        return self.paperless_config_handler.get_invoice_tags()

    def get_receipt_tags(self):
        return self.paperless_config_handler.get_receipt_tags()
