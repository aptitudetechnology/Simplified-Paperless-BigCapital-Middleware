# web/routes/web_routes.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
import logging
from datetime import datetime # Import datetime for handling dates
import requests # Import requests for making HTTP calls to Paperless-ngx API
import json # For handling JSON responses, though requests.json() usually handles it
# from config import Config # You might import Config here if using a class-based config

from .utils import parse_extracted_data, get_dashboard_stats # Ensure .utils is accessible

logger = logging.getLogger(__name__)

def create_web_blueprint(config, db_manager, doc_processor):
    """Create and configure the web routes blueprint"""
    web = Blueprint('web', __name__)

    # --- Jinja2 Filters ---
    @web.app_template_filter('datetime')
    def format_datetime(value, format="%Y-%m-%d %H:%M"):
        """Formats a datetime string or object into a human-readable string."""
        if not value:
            return ""
        if isinstance(value, str):
            try:
                # Attempt to parse common ISO formats (e.g., "2023-01-01T12:00:00Z")
                if 'T' in value and ('Z' in value or '+' in value):
                    dt_obj = datetime.fromisoformat(value.replace('Z', '+00:00') if 'Z' in value else value)
                else: # Attempt to parse a common date-time string without timezone
                    dt_obj = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logger.warning(f"Could not parse datetime string: {value}")
                return value # Return original value if parsing fails
        elif isinstance(value, datetime):
            dt_obj = value
        else:
            return value # Return as is if not string or datetime object

        return dt_obj.strftime(format)

    @web.app_template_filter('currency')
    def format_currency(value, symbol='$', decimal_places=2):
        """Formats a numerical value as currency."""
        try:
            return f"{symbol}{float(value):,.{decimal_places}f}"
        except (ValueError, TypeError):
            return f"{symbol}0.00"

    # --- Routes ---

    @web.route('/')
    def index():
        """Main dashboard page"""
        try:
            # Get recent documents
            recent_docs_raw = db_manager.execute_query(
                "SELECT * FROM documents ORDER BY upload_date DESC LIMIT 10"
            )

            # Convert to list of dicts and parse JSON
            recent_docs = []
            for doc_row in recent_docs_raw:
                doc_dict = dict(doc_row)
                doc_dict = parse_extracted_data(doc_dict)
                recent_docs.append(doc_dict)

            # Get comprehensive stats
            stats = get_dashboard_stats(db_manager)

            logger.info(f"Dashboard loaded with {len(recent_docs)} recent docs and stats: {stats}")

            return render_template('dashboard.html',
                                   recent_docs=recent_docs,
                                   stats=stats)
        except Exception as e:
            logger.error(f'Error loading dashboard: {str(e)}')
            flash(f'Error loading dashboard: {str(e)}', 'error')
            return render_template('dashboard.html',
                                   recent_docs=[],
                                   stats={
                                       'total_documents': 0,
                                       'completed': 0,
                                       'pending': 0,
                                       'failed': 0,
                                       'processing': 0,
                                       'avg_amount': 0.0,
                                       'total_amount': 0.0
                                       })

    @web.route('/upload')
    def upload_page():
        """File upload page"""
        return render_template('upload.html')

    @web.route('/documents')
    def documents_list():
        """Documents list page"""
        page = request.args.get('page', 1, type=int)
        per_page = 20
        status_filter = request.args.get('status', '')

        try:
            query = "SELECT * FROM documents WHERE 1=1"
            params = []

            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)

            query += " ORDER BY upload_date DESC LIMIT ? OFFSET ?"
            params.extend([per_page, (page - 1) * per_page])

            documents_raw = db_manager.execute_query(query, tuple(params))

            # Convert sqlite3.Row objects to dictionaries and parse JSON
            documents = []
            for doc_row in documents_raw:
                doc_dict = dict(doc_row)
                doc_dict = parse_extracted_data(doc_dict)
                documents.append(doc_dict)

            # Get total count for pagination
            count_query = "SELECT COUNT(*) FROM documents WHERE 1=1"
            count_params = []
            if status_filter:
                count_query += " AND status = ?"
                count_params.append(status_filter)

            total_result = db_manager.execute_query(count_query, tuple(count_params))
            total = total_result[0][0] if total_result else 0

            return render_template('documents.html',
                                   documents=documents,
                                   page=page,
                                   per_page=per_page,
                                   total=total,
                                   status_filter=status_filter)
        except Exception as e:
            logger.error(f'Error loading documents list: {str(e)}')
            flash(f'Error loading documents: {str(e)}', 'error')
            return render_template('documents.html',
                                   documents=[],
                                   page=1,
                                   per_page=per_page,
                                   total=0,
                                   status_filter=status_filter)

    @web.route('/document/<int:doc_id>')
    def document_detail(doc_id: int):
        """Document detail page"""
        try:
            doc = db_manager.get_document(doc_id)

            if not doc:
                flash('Document not found', 'error')
                return redirect(url_for('web.documents_list'))

            # Parse extracted_data JSON string to dict for display
            doc = parse_extracted_data(doc)

            line_items = doc['extracted_data'].get('line_items', [])
            processing_log = []  # Placeholder - you might want to implement this

            return render_template('document_detail.html',
                                   document=doc,
                                   line_items=line_items,
                                   processing_log=processing_log)
        except Exception as e:
            logger.error(f'Error loading document detail for ID {doc_id}: {str(e)}')
            flash(f'Error loading document: {str(e)}', 'error')
            return redirect(url_for('web.documents_list'))

    # --- NEW ROUTE FOR PAPERLESS-NGX DOCUMENTS ---
    @web.route('/paperless-ngx-documents')
    def paperless_ngx_documents():
        paperless_ngx_docs = []
        current_page = request.args.get('page', 1, type=int)
        search_query = request.args.get('q', '', type=str)
        per_page = 10 # Default items per page for Paperless-ngx

        # Retrieve configuration from the 'config' object passed to the blueprint
        PAPERLESS_NGX_BASE_URL = config.get('paperless', 'api_url', fallback='')
        PAPERLESS_NGX_API_TOKEN = config.get('paperless', 'api_token', fallback='')

        # Initialize pagination data
        pagination = {
            'page': current_page,
            'per_page': per_page,
            'total': 0,
            'pages': 0,
            'has_prev': False,
            'has_next': False,
            'prev_num': None,
            'next_num': None,
            'iter_pages': lambda: []
        }

        if not PAPERLESS_NGX_BASE_URL:
            flash("Paperless-ngx Base URL is not configured. Please set it in Configuration.", "error")
            logger.error("Paperless-ngx Base URL not configured.")
            return render_template('paperless_ngx_documents.html',
                                   paperless_ngx_docs=paperless_ngx_docs,
                                   pagination=pagination,
                                   YOUR_PAPERLESS_NGX_URL="#", # Fallback for template
                                   YOUR_PAPERLESS_NGX_BASE_URL="#")

        if not PAPERLESS_NGX_API_TOKEN:
            flash("Paperless-ngx API Token is not configured. Please set it in Configuration.", "error")
            logger.error("Paperless-ngx API Token not configured.")
            return render_template('paperless_ngx_documents.html',
                                   paperless_ngx_docs=paperless_ngx_docs,
                                   pagination=pagination,
                                   YOUR_PAPERLESS_NGX_URL=PAPERLESS_NGX_BASE_URL,
                                   YOUR_PAPERLESS_NGX_BASE_URL=PAPERLESS_NGX_BASE_URL)

        headers = {
            'Authorization': f'Token {PAPERLESS_NGX_API_TOKEN}',
        }

        params = {
            'page': current_page,
            'page_size': per_page,
            'order_by': '-created', # Sort by creation date, newest first
        }
        if search_query:
            params['query'] = search_query # Pass search query to Paperless-ngx API

        try:
            api_url = f"{PAPERLESS_NGX_BASE_URL}documents/"
            logger.info(f"Fetching Paperless-ngx documents from: {api_url} with params: {params}")

            # It's highly recommended to set verify=True and provide a CA bundle
            # or ensure your Paperless-ngx has a valid certificate in production.
            # For local development, verify=False might be used.
            response = requests.get(api_url, headers=headers, params=params, verify=False)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            # Prepare mappings for related fields (Correspondents, Document Types, Tags)
            # It's more efficient to fetch these once and cache them if performance is critical
            correspondents_map = {}
            doc_types_map = {}
            tags_map = {}

            # Fetch all correspondents
            try:
                corr_res = requests.get(f"{PAPERLESS_NGX_BASE_URL}correspondents/?page_size=max", headers=headers, verify=False)
                corr_res.raise_for_status()
                for c in corr_res.json().get('results', []):
                    correspondents_map[c['id']] = c['name']
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not fetch all correspondents: {e}")

            # Fetch all document types
            try:
                type_res = requests.get(f"{PAPERLESS_NGX_BASE_URL}/api/document_types/?page_size=max", headers=headers, verify=False)
                type_res.raise_for_status()
                for t in type_res.json().get('results', []):
                    doc_types_map[t['id']] = t['name']
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not fetch all document types: {e}")

            # Fetch all tags
            try:
                tags_res = requests.get(f"{PAPERLESS_NGX_BASE_URL}/api/tags/?page_size=max", headers=headers, verify=False)
                tags_res.raise_for_status()
                for t in tags_res.json().get('results', []):
                    tags_map[t['id']] = t['name']
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not fetch all tags: {e}")


            for doc in data.get('results', []):
                correspondent_name = correspondents_map.get(doc.get('correspondent'), 'N/A')
                document_type_name = doc_types_map.get(doc.get('document_type'), 'N/A')
                tags_names = [tags_map.get(tag_id, 'N/A') for tag_id in doc.get('tags', [])]

                paperless_ngx_docs.append({
                    'id': doc.get('id'),
                    'title': doc.get('title', 'No Title'),
                    'document_type': document_type_name,
                    'created': doc.get('created'),
                    'correspondent': correspondent_name,
                    'tags': tags_names,
                })

            total_docs = data.get('count', 0)

            # Update pagination details based on API response
            pagination['total'] = total_docs
            pagination['pages'] = (total_docs + per_page - 1) // per_page
            pagination['has_prev'] = data.get('previous') is not None
            pagination['has_next'] = data.get('next') is not None
            pagination['prev_num'] = current_page - 1 if data.get('previous') else None
            pagination['next_num'] = current_page + 1 if data.get('next') else None
            
            # Simple iter_pages for Jinja2 (consider more robust for large number of pages)
            pagination['iter_pages'] = lambda: range(1, pagination['pages'] + 1)


            logger.info(f"Successfully fetched {len(paperless_ngx_docs)} Paperless-ngx documents. Total: {total_docs}")

        except requests.exceptions.RequestException as e:
            flash(f"Error connecting to Paperless-ngx API: {e}. Check URL/Token and connectivity.", "error")
            logger.error(f"Error connecting to Paperless-ngx API: {e}")
        except KeyError as e:
            flash(f"Error parsing Paperless-ngx API response: Missing expected key {e}.", "error")
            logger.error(f"Error parsing Paperless-ngx API response: Missing key {e}")
        except Exception as e:
            flash(f"An unexpected error occurred while fetching Paperless-ngx documents: {e}", "error")
            logger.exception("An unexpected error occurred in paperless_ngx_documents route.") # Use exception for full traceback

        return render_template(
            'paperless_ngx_documents.html',
            paperless_ngx_docs=paperless_ngx_docs,
            pagination=pagination,
            YOUR_PAPERLESS_NGX_URL=PAPERLESS_NGX_BASE_URL,
            YOUR_PAPERLESS_NGX_BASE_URL=PAPERLESS_NGX_BASE_URL,
            search_query=search_query # Pass search query back to template
        )

    # --- START OF MOVED CONFIGURATION ROUTE ---
    # This route was previously in web/routes/config_routes.py
    @web.route('/configuration', methods=['GET', 'POST'])
    def configuration():
        """Configuration page to view and update settings."""
        # Define log levels for the dropdown
        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

        if request.method == 'POST':
            try:
                # Add debugging
                logger.info(f"Config object type: {type(config)}")
                logger.info(f"Config object methods: {dir(config)}")
                logger.info(f"Has set method: {hasattr(config, 'set')}")
                logger.info(f"Has save method: {hasattr(config, 'save')}")
        
                # Paperless-NGX
                config.set('paperless', 'api_url', request.form.get('paperless_api_url'))
                if request.form.get('paperless_api_token'):
                    config.set('paperless', 'api_token', request.form.get('paperless_api_token'))
                config.set('paperless', 'invoice_tags', request.form.get('paperless_invoice_tags'))
                config.set('paperless', 'receipt_tags', request.form.get('paperless_receipt_tags'))

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
            
            # This redirect now correctly points to 'web.configuration'
            return redirect(url_for('web.configuration'))  
        
        else:  # GET request
            # Retrieve current configuration values for display
            current_config_data = {
                'paperless': {
                    'api_url': config.get('paperless', 'api_url', fallback=''),
                    'api_token': '',  # Don't expose token on GET
                    'invoice_tags': config.get('paperless', 'invoice_tags', fallback=''),
                    'receipt_tags': config.get('paperless', 'receipt_tags', fallback=''),
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
    # --- END OF MOVED CONFIGURATION ROUTE ---
    
    return web
