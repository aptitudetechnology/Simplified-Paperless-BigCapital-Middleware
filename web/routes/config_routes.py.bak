from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import logging

logger = logging.getLogger(__name__)

def create_config_blueprint(config, db_manager, doc_processor):
    """Create and configure the configuration routes blueprint"""
    config_bp = Blueprint('config', __name__, url_prefix='/config')
    
    @config_bp.route('/', methods=['GET', 'POST'])
    def configuration():
        """Configuration page to view and update settings."""
        # Define log levels for the dropdown
        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

        if request.method == 'POST':
            try:
                # Paperless-NGX
                config.set('paperless_ngx', 'api_url', request.form.get('paperless_ngx_api_url'))
                if request.form.get('paperless_ngx_api_token'):
                    config.set('paperless_ngx', 'api_token', request.form.get('paperless_ngx_api_token'))
                config.set('paperless_ngx', 'invoice_tags', request.form.get('paperless_ngx_invoice_tags'))
                config.set('paperless_ngx', 'receipt_tags', request.form.get('paperless_ngx_receipt_tags'))

                # Bigcapital
                config.set('bigcapital', 'api_url', request.form.get('bigcapital_api_url'))
                if request.form.get('bigcapital_api_token'):
                    config.set('bigcapital', 'api_token', request.form.get('bigcapital_api_token'))
                
                try:
                    default_due_days = int(request.form.get('bigcapital_default_due_days'))
                    config.set('bigcapital', 'default_due_days', str(default_due_days))
                except ValueError:
                    flash('Default Due Days must be a number.', 'warning')
                    logger.warning('Invalid input for bigcapital_default_due_days')

                config.set('bigcapital', 'auto_create_customers', 'true' if 'bigcapital_auto_create_customers' in request.form else 'false')

                # Processing
                try:
                    check_interval_seconds = int(request.form.get('processing_check_interval_seconds'))
                    config.set('processing', 'check_interval_seconds', str(check_interval_seconds))
                except ValueError:
                    flash('Check Interval (seconds) must be a number.', 'warning')
                    logger.warning('Invalid input for processing_check_interval_seconds')

                config.set('processing', 'log_level', request.form.get('processing_log_level'))
                config.set('processing', 'processed_tag', request.form.get('processing_processed_tag'))
                config.set('processing', 'error_tag', request.form.get('processing_error_tag'))

                # Save changes
                config.save() 
                flash('Configuration saved successfully!', 'success')
                logger.info("Configuration updated and saved.")
                
                current_app.config_reloaded = True
                logger.info("Application components may need re-initialization due to config changes.")

            except Exception as e:
                flash(f'Error saving configuration: {str(e)}', 'danger')
                logger.exception("Failed to save configuration.")
            
            return redirect(url_for('config.configuration'))
        
        else:  # GET request
            # Retrieve current configuration values for display
            current_config_data = {
                'paperless_ngx': {
                    'api_url': config.get('paperless_ngx', 'api_url', fallback=''),
                    'api_token': '',  # Don't expose token on GET
                    'invoice_tags': config.get('paperless_ngx', 'invoice_tags', fallback=''),
                    'receipt_tags': config.get('paperless_ngx', 'receipt_tags', fallback=''),
                },
                'bigcapital': {
                    'api_url': config.get('bigcapital', 'api_url', fallback=''),
                    'api_token': '',  # Don't expose token on GET
                    'default_due_days': config.get('bigcapital', 'default_due_days', fallback=''),
                    'auto_create_customers': config.getboolean('bigcapital', 'auto_create_customers', fallback=False),
                },
                'processing': {
                    'check_interval_seconds': config.get('processing', 'check_interval_seconds', fallback=''),
                    'log_level': config.get('processing', 'log_level', fallback='INFO'),
                    'processed_tag': config.get('processing', 'processed_tag', fallback=''),
                    'error_tag': config.get('processing', 'error_tag', fallback=''),
                }
            }
            
            return render_template('config.html', 
                                   config=current_config_data, 
                                   log_levels=log_levels)
    
    return config_bp
