"""
Validation and Security Middleware
Decorators and utilities for request validation and security
"""

from flask import request, jsonify
from functools import wraps
import re
import logging

logger = logging.getLogger(__name__)

def require_admin_auth(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Import here to avoid circular imports
        from config.auth_config import AuthConfig
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'message': 'Authorization token required'
            }), 401
        
        token = auth_header.split(' ')[1]
        payload = AuthConfig.verify_jwt_token(token)
        
        if not payload:
            return jsonify({
                'success': False,
                'message': 'Invalid or expired token'
            }), 401
        
        # Check if user is admin
        if payload.get('role') != 'admin':
            return jsonify({
                'success': False,
                'message': 'Admin access required'
            }), 403
        
        # Attach user info to request for use in route
        request.admin_user = payload
        
        return f(*args, **kwargs)
    return decorated_function

def add_security_headers(f=None):
    """Decorator to add security headers - supports both @add_security_headers and @add_security_headers()"""
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            response = func(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['X-Frame-Options'] = 'DENY'
                response.headers['X-XSS-Protection'] = '1; mode=block'
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
                response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            return response
        return decorated_function
    
    # Support both @add_security_headers and @add_security_headers()
    if f is None:
        # Called with parentheses: @add_security_headers()
        return decorator
    else:
        # Called without parentheses: @add_security_headers
        return decorator(f)

def validate_json(*required_fields):
    """Decorator to validate JSON request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Content-Type must be application/json'
                }), 400
            
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'Invalid JSON data'
                }), 400
            
            missing_fields = []
            for field in required_fields:
                if field not in data or not data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                return jsonify({
                    'success': False,
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class RequestValidator:
    """Request validation utilities"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return ""
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
        
        # Trim whitespace and limit length
        return sanitized.strip()[:max_length]
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email or len(email) > 254:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_uuid(uuid_string: str) -> bool:
        """Validate UUID format"""
        if not uuid_string:
            return False
        
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        return bool(re.match(pattern, uuid_string, re.IGNORECASE))
    
    @staticmethod
    def validate_pagination(page: int, per_page: int) -> tuple[int, int]:
        """Validate and normalize pagination parameters"""
        page = max(1, int(page) if isinstance(page, (int, str)) and str(page).isdigit() else 1)
        per_page = max(1, min(100, int(per_page) if isinstance(per_page, (int, str)) and str(per_page).isdigit() else 20))
        return page, per_page
    
    @staticmethod
    def validate_file_upload(file) -> dict:
        """
        Validate uploaded file
        
        Args:
            file: Werkzeug FileStorage object
            
        Returns:
            dict: File information including size, extension, etc.
            
        Raises:
            ValueError: If file validation fails
        """
        if not file:
            raise ValueError("No file provided")
        
        if file.filename == '':
            raise ValueError("No file selected")
        
        # Get file extension
        if '.' not in file.filename:
            raise ValueError("File has no extension")
        
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        
        # Validate file extension
        allowed_extensions = {'mp3', 'wav', 'm4a', 'mp4', 'webm'}
        if file_extension not in allowed_extensions:
            raise ValueError(f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")
        
        # Get file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        # Validate file size (100MB max)
        max_size = 100 * 1024 * 1024
        if file_size > max_size:
            raise ValueError(f"File too large. Maximum size: 100MB")
        
        if file_size == 0:
            raise ValueError("File is empty")
        
        return {
            'original_filename': file.filename,
            'file_extension': file_extension,
            'file_size': file_size,
            'content_type': file.content_type
        }

# Decorator functions for backward compatibility
def validate_file_upload(f):
    """Decorator to validate file upload (deprecated - use RequestValidator.validate_file_upload)"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def validate_user_id(f):
    """Decorator to validate user ID (deprecated - use RequestValidator directly)"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function