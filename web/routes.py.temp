# --- API Routes ---
@api.route('/upload', methods=['POST'])
def upload_file():
    """Upload file endpoint"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Check file size (Flask's app.config['MAX_CONTENT_LENGTH'] also handles this)
        # RequestEntityTooLarge is caught by the app.errorhandler in app.py
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        unique_filename = f"{timestamp}{filename}"
        
        upload_folder = config.get('processing', 'upload_folder', 'uploads')
        os.makedirs(upload_folder, exist_ok=True) # Ensure folder exists
        
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        
        # Get file info
        file_info = get_file_info(filepath)
        
        # Insert document record using db_manager's method
        doc_id = db_manager.insert_document(
            filename=unique_filename,
            original_filename=filename,
            file_path=filepath,
            file_size=file_info['size'],
            content_type=file_info['mime_type'] # Ensure 'mime_type' is the column name if storing here
        )
        
        logger.info(f"Document uploaded with ID {doc_id}: {unique_filename}")
        
        # Start processing if enabled
        auto_process = request.form.get('auto_process', 'true').lower() == 'true'
        if auto_process and doc_processor: # Ensure doc_processor is initialized
            try:
                # Process document using the document ID, not the file path
                logger.info(f"Starting automatic processing for document ID {doc_id}")
                result = doc_processor.process_document_by_id(doc_id)
                logger.info(f"Processing result for doc {doc_id}: {result}")
            except Exception as e:
                # Log error but don't fail the upload
                logger.error(f"Processing error for doc {doc_id}: {e}")
                # Update document status to failed
                try:
                    db_manager.update_document(doc_id, status='failed', error_message=str(e))
                except Exception as db_error:
                    logger.error(f"Failed to update document status to failed: {db_error}")
        
        return jsonify({
            'success': True,
            'document_id': doc_id,
            'filename': unique_filename,
            'message': 'File uploaded successfully'
        }), 201
        
    except RequestEntityTooLarge:
        # This will be caught by the app-level error handler in app.py
        # You can still return a more specific message if desired, but app.py's handler takes precedence
        return jsonify({'error': 'File too large'}), 413
    except Exception as e:
        logger.error(f'Upload failed: {str(e)}')
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500
