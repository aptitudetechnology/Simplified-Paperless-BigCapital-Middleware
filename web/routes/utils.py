import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

def allowed_file(filename: str, config) -> bool:
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    allowed_extensions_str = config.get('processing', 'allowed_extensions', fallback='pdf,jpg,jpeg,png')
    allowed_extensions = [e.strip() for e in allowed_extensions_str.split(',')]
    return ext in allowed_extensions

def get_file_hash(filepath: str) -> str:
    """Calculate SHA-256 hash of file content"""
    try:
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}")
        return ""

def check_duplicate_file(filename: str, file_hash: str, file_size: int, db_manager) -> Dict[str, Any]:
    """Check if file is a duplicate based on hash, filename, and size"""
    try:
        # First check by file hash (most reliable)
        if file_hash:
            hash_result = db_manager.execute_query(
                "SELECT id, filename, upload_date FROM documents WHERE file_hash = ?",
                (file_hash,)
            )
            if hash_result:
                doc = dict(hash_result[0])
                return {
                    'is_duplicate': True,
                    'match_type': 'content',
                    'existing_document': doc,
                    'message': f"Identical file content already exists (Document ID: {doc['id']})"
                }
        
        # Secondary check by filename and size
        name_size_result = db_manager.execute_query(
            "SELECT id, filename, upload_date FROM documents WHERE original_filename = ? AND file_size = ?",
            (filename, file_size)
        )
        if name_size_result:
            doc = dict(name_size_result[0])
            return {
                'is_duplicate': True,
                'match_type': 'name_size',
                'existing_document': doc,
                'message': f"File with same name and size already exists (Document ID: {doc['id']})"
            }
        
        # Check for similar filename (optional warning)
        similar_result = db_manager.execute_query(
            "SELECT id, filename, upload_date FROM documents WHERE original_filename = ?",
            (filename,)
        )
        if similar_result:
            doc = dict(similar_result[0])
            return {
                'is_duplicate': False,
                'is_similar': True,
                'match_type': 'name_only',
                'existing_document': doc,
                'message': f"File with same name already exists but different size (Document ID: {doc['id']})"
            }
        
        return {'is_duplicate': False, 'is_similar': False}
        
    except Exception as e:
        logger.error(f"Error checking for duplicates: {e}")
        return {'is_duplicate': False, 'error': str(e)}

def parse_extracted_data(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Parse extracted_data JSON string safely"""
    if 'extracted_data' in doc and isinstance(doc['extracted_data'], str):
        try:
            doc['extracted_data'] = json.loads(doc['extracted_data'])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse extracted_data for document: {doc.get('id', 'unknown')}")
            doc['extracted_data'] = {}
    elif 'extracted_data' not in doc or doc['extracted_data'] is None:
        doc['extracted_data'] = {}
    return doc

def get_dashboard_stats(db_manager) -> Dict[str, Any]:
    """Get comprehensive dashboard statistics"""
    try:
        # Get total documents count
        total_result = db_manager.execute_query("SELECT COUNT(*) FROM documents")
        total_documents = total_result[0][0] if total_result else 0
        
        # Get completed documents count
        completed_result = db_manager.execute_query("SELECT COUNT(*) FROM documents WHERE status = 'completed'")
        completed = completed_result[0][0] if completed_result else 0
        
        # Get pending documents count
        pending_result = db_manager.execute_query("SELECT COUNT(*) FROM documents WHERE status = 'pending'")
        pending = pending_result[0][0] if pending_result else 0
        
        # Get failed documents count
        failed_result = db_manager.execute_query("SELECT COUNT(*) FROM documents WHERE status = 'failed'")
        failed = failed_result[0][0] if failed_result else 0
        
        # Get processing documents count
        processing_result = db_manager.execute_query("SELECT COUNT(*) FROM documents WHERE status = 'processing'")
        processing = processing_result[0][0] if processing_result else 0
        
        # Calculate average amount from extracted data
        avg_amount = 0.0
        total_amount = 0.0
        amount_count = 0
        
        try:
            # Get all completed documents with extracted data
            docs_with_data = db_manager.execute_query(
                "SELECT extracted_data FROM documents WHERE status = 'completed' AND extracted_data IS NOT NULL"
            )
            
            for row in docs_with_data:
                if row[0]:  # extracted_data is not null
                    try:
                        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        if isinstance(data, dict):
                            # Try different possible amount fields
                            amount = None
                            for field in ['total_amount', 'amount', 'total', 'invoice_total']:
                                if field in data and data[field] is not None:
                                    try:
                                        # Handle string amounts by removing currency symbols
                                        amount_str = str(data[field]).replace('$', '').replace(',', '').strip()
                                        amount = float(amount_str)
                                        break
                                    except (ValueError, TypeError):
                                        continue
                            
                            if amount is not None and amount > 0:
                                total_amount += amount
                                amount_count += 1
                    except (json.JSONDecodeError, TypeError, KeyError):
                        continue
            
            if amount_count > 0:
                avg_amount = total_amount / amount_count
                
        except Exception as e:
            logger.warning(f"Error calculating average amount: {e}")
        
        stats = {
            'total_documents': total_documents,
            'completed': completed,
            'pending': pending,
            'failed': failed,
            'processing': processing,
            'avg_amount': avg_amount,
            'total_amount': total_amount
        }
        
        logger.info(f"Dashboard stats calculated: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {
            'total_documents': 0,
            'completed': 0,
            'pending': 0,
            'failed': 0,
            'processing': 0,
            'avg_amount': 0.0,
            'total_amount': 0.0
        }
