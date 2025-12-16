"""
Helper utilities for file handling, validation, and security.
"""
import os
import re
from werkzeug.utils import secure_filename
from flask import current_app


def allowed_file(filename):
    """
    Check if file has allowed extension for certificates (PDF only).
    
    Args:
        filename: Name of the file to check
    
    Returns:
        bool: True if allowed, False otherwise
    """
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf'})
    return ext in allowed


def allowed_template_file(filename):
    """
    Check if file has allowed extension for certificate templates (PDF only).
    
    Args:
        filename: Name of the file to check
    
    Returns:
        bool: True if allowed, False otherwise
    """
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    return ext == 'pdf'


def allowed_bulk_file(filename):
    """
    Check if file has allowed extension for bulk upload (CSV, Excel).
    
    Args:
        filename: Name of the file to check
    
    Returns:
        bool: True if allowed, False otherwise
    """
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    allowed = current_app.config.get('ALLOWED_BULK_EXTENSIONS', {'csv', 'xlsx', 'xls'})
    return ext in allowed


def secure_filename_custom(filename):
    """
    Secure filename while preserving some readability.
    Prevents directory traversal and removes dangerous characters.
    
    Args:
        filename: Original filename
    
    Returns:
        str: Secured filename
    """
    # Use werkzeug's secure_filename as base
    secured = secure_filename(filename)
    
    # Ensure filename is not empty after securing
    if not secured:
        import uuid
        secured = f"file_{uuid.uuid4().hex[:8]}"
    
    return secured


def validate_email(email):
    """
    Validate email format using regex.
    
    Args:
        email: Email string to validate
    
    Returns:
        bool: True if valid email format, False otherwise
    """
    if not email:
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def sanitize_email(email):
    """
    Sanitize and normalize email input.
    
    Args:
        email: Email string to sanitize
    
    Returns:
        str: Sanitized, lowercase email
    """
    if not email:
        return ''
    
    # Strip whitespace and convert to lowercase
    return email.strip().lower()


def get_file_extension(filename):
    """
    Get file extension from filename.
    
    Args:
        filename: Filename string
    
    Returns:
        str: File extension (lowercase) or empty string
    """
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()


def generate_unique_filename(original_filename, prefix=''):
    """
    Generate a unique filename to prevent overwrites.
    
    Args:
        original_filename: Original filename
        prefix: Optional prefix for the filename
    
    Returns:
        str: Unique filename
    """
    import uuid
    from datetime import datetime
    
    # Get extension
    ext = get_file_extension(original_filename)
    
    # Generate unique name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    
    if prefix:
        return f"{prefix}_{timestamp}_{unique_id}.{ext}"
    return f"{timestamp}_{unique_id}.{ext}"
