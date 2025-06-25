
# config/paperless/settings.py
import os
import configparser
from pathlib import Path

class Config:
    def __init__(self, config_file='config.ini'):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self._create_default_config()

    def _create_default_config(self):
        # ... (existing sections like database, ocr, processing, etc.) ...

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
        # --- NEW SECTION FOR PAPERLESS-NGX ---
        self.config['paperless'] = {
            'api_url': 'http://paperless-ngx:8000/api/',
            'api_token': 'YOUR_GENERATED_API_TOKEN', # Placeholder for default creation
            'invoice_tags': 'Invoice,ProcessedByMiddleware',
            'receipt_tags': 'Receipt,ProcessedByMiddleware'
        }
        # --- END NEW SECTION ---

        with open(self.config_file, 'w') as f:
            self.config.write(f)

    # ... (existing get, getint, getboolean methods) ...

    # Add specific getters for Paperless-ngx settings
    def get_paperless_api_url(self):
        return self.get('paperless', 'api_url')

    def get_paperless_api_token(self):
        return self.get('paperless', 'api_token')

    def get_invoice_tags(self):
        return [tag.strip() for tag in self.get('paperless', 'invoice_tags', '').split(',') if tag.strip()]

    def get_receipt_tags(self):
        return [tag.strip() for tag in self.get('paperless', 'receipt_tags', '').split(',') if tag.strip()]
