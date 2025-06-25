# config/paperless/settings.py

# This file defines the PaperlessConfigHandler class.
# It does NOT re-read config.ini; it expects a Config instance.

class PaperlessConfigHandler:
    def __init__(self, main_config_instance):
        # The main_config_instance is an instance of the Config class
        # defined in config/settings.py
        self.main_config = main_config_instance

    def get_api_url(self):
        return self.main_config.get('paperless', 'api_url')

    def get_api_token(self):
        return self.main_config.get('paperless', 'api_token')

    def get_invoice_tags(self):
        # Assuming tags are comma-separated strings in config.ini
        tags_string = self.main_config.get('paperless', 'invoice_tags', '')
        return [tag.strip() for tag in tags_string.split(',') if tag.strip()]

    def get_receipt_tags(self):
        # Assuming tags are comma-separated strings in config.ini
        tags_string = self.main_config.get('paperless', 'receipt_tags', '')
        return [tag.strip() for tag in tags_string.split(',') if tag.strip()]
