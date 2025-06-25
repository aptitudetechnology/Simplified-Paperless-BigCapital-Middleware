
# config/paperless/settings.py


# You would likely need to pass the main Config instance to this
# or have this module read from config.ini directly in a more limited scope.

# For simplicity, let's assume it gets passed a configparser object or a Config instance
# OR it just defines constants if the settings are hardcoded.

class PaperlessConfigHandler:
    def __init__(self, main_config_instance):
        self.main_config = main_config_instance

    def get_api_url(self):
        return self.main_config.get('paperless', 'api_url')

    def get_api_token(self):
        return self.main_config.get('paperless', 'api_token')

    def get_invoice_tags(self):
        return [tag.strip() for tag in self.main_config.get('paperless', 'invoice_tags', '').split(',') if tag.strip()]

    def get_receipt_tags(self):
        return [tag.strip() for tag in self.main_config.get('paperless', 'receipt_tags', '').split(',') if tag.strip()]

# If you prefer to define them as simple variables that the main Config class then loads
# This would be less flexible if you want to read them from config.ini here.
  PAPERLESS_DEFAULT_API_URL = 'http://paperless-ngx:8000/api/'
  PAPERLESS_DEFAULT_API_TOKEN = 'YOUR_GENERATED_API_TOKEN'
