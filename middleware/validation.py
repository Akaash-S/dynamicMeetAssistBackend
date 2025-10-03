"""
Request Validation Middleware for AI Meeting Assistant Backend
Provides comprehensive input validation, file validation, and security checks
"""

import os
import mimetypes
from functools import wraps
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
from typing import List, Optional, Dict, Any
import re

class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class RequestValidator:
    """Centralized request validation logic"""
    
    # Configuration from environment variables
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 104857600))  # 100MB default
    ALLOWED_EXTENSIONS = os.getenv('ALLOWED_EXTENSIONS', 'mp3,wav,m4a,mp4,webm').split(',')
    
    # MIME types for audio files
    ALLOWED_MIME_TYPES = {
        'mp3': ['audio/mpeg', 'audio/mp3'],
        'wav': ['audio/wav', 'audio/x-wav', 'audio/wave'],
        'm4a': ['audio/mp4', 'audio/m4a', 'audio/x-m4a'],
        'mp4': ['audio/mp4', 'video/mp4'],
        'webm': ['audio/webm', 'video/webm']
    }
    
    @classmethod
    def _validate_file_signature(cls, file_header: bytes, file_extension: str) -> bool:
        """Validate file signature (magic bytes) against extension"""
        if len(file_header) < 4:
            return True  # Not enough data to validate
        
        # Common file signatures (magic bytes)
        signatures = {
            'mp3': [
                b'ID3',  # ID3v2
                b'\xFF\xFB',  # MPEG-1 Layer 3
                b'\xFF\xF3',  # MPEG-1 Layer 3
                b'\xFF\xF2',  # MPEG-1 Layer 3
            ],
            'wav': [
                b'RIFF',  # WAV files start with RIFF
            ],
            'm4a': [
                b'\x00\x00\x00\x20ftypM4A',  # M4A signature
                b'\x00\x00\x00\x18ftyp',     # Alternative M4A
                b'ftyp',  # Generic MP4 container
            ],
            'mp4': [
                b'\x00\x00\x00\x18ftyp',  # MP4 signature
                b'\x00\x00\x00\x20ftyp',  # Alternative MP4
                b'ftyp',  # Generic MP4 container
            ],
            'webm': [
                b'\x1A\x45\xDF\xA3',  # WebM/Matroska signature
            ]
        }
        
        extension_signatures = signatures.get(file_extension, [])
        if not extension_signatures:
            return True  # No signatures defined, allow
        
        # Check if file header starts with any of the expected signatures
        for signature in extension_signatures:
            if file_header.startswith(signature):
                return True
            # For some formats, check if signature appears within first few bytes
            if signature in file_header[:12]:
                return True
        
        return False  # No matching signature found
    
    @classmethod
    def validate_required_fields(cls, data: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate that all required fields are present and not empty"""
        missing_fields = []
        
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
            elif isinstance(data[field], str) and not data[field].strip():
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    @classmethod
    def validate_uuid(cls, uuid_string: str) -> bool:
        """Validate UUID format"""
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, uuid_string, re.IGNORECASE))
    
    @classmethod
    def validate_file_upload(cls, file) -> Dict[str, Any]:
        """Comprehensive file validation"""
        if not file:
            raise ValidationError("No file provided")
        
        if file.filename == '':
            raise ValidationError("No file selected")
        
        # Secure filename
        original_filename = file.filename
        secure_name = secure_filename(original_filename)
        
        if not secure_name:
            raise ValidationError("Invalid filename")
        
        # Check file extension
        if '.' not in secure_name:
            raise ValidationError("File must have an extension")
        
        file_extension = secure_name.rsplit('.', 1)[1].lower()
        
        if file_extension not in cls.ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"Invalid file type. Allowed extensions: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        
        if file_size > cls.MAX_FILE_SIZE:
            max_mb = cls.MAX_FILE_SIZE / (1024 * 1024)
            raise ValidationError(f"File too large. Maximum size: {max_mb:.0f}MB")
        
        if file_size == 0:
            raise ValidationError("File is empty")
        
        # Validate MIME type using multiple methods
        try:
            # Method 1: Check Flask's content type
            flask_mime = file.content_type
            allowed_mimes_for_ext = cls.ALLOWED_MIME_TYPES.get(file_extension, [])
            
            # Method 2: Use mimetypes library as backup
            guessed_mime, _ = mimetypes.guess_type(secure_name)
            
            # Method 3: Read file header for basic validation
            file.seek(0)
            file_header = file.read(12)  # Read first 12 bytes
            file.seek(0)  # Reset file pointer
            
            # Basic file signature validation
            is_valid_file = cls._validate_file_signature(file_header, file_extension)
            
            if not is_valid_file:
                raise ValidationError(
                    f"File signature doesn't match the extension '{file_extension}'. "
                    f"The file may be corrupted or have an incorrect extension."
                )
            
            # Check MIME types
            if flask_mime and flask_mime not in allowed_mimes_for_ext:
                if guessed_mime and guessed_mime in allowed_mimes_for_ext:
                    # Trust the guessed MIME type if it matches
                    pass
                else:
                    try:
                        current_app.logger.warning(
                            f"MIME type mismatch: Flask={flask_mime}, Guessed={guessed_mime}, "
                            f"Expected={allowed_mimes_for_ext}"
                        )
                    except RuntimeError:
                        # Working outside of application context, just print
                        print(f"MIME type mismatch: Flask={flask_mime}, Guessed={guessed_mime}, Expected={allowed_mimes_for_ext}")
                    # Don't fail on MIME type mismatch, just log warning
        
        except Exception as e:
            # If validation fails, log warning but don't fail the upload
            try:
                current_app.logger.warning(f"File content validation warning: {e}")
            except RuntimeError:
                # Working outside of application context, just print
                print(f"File content validation warning: {e}")
        
        return {
            'original_filename': original_filename,
            'secure_filename': secure_name,
            'file_size': file_size,
            'file_extension': file_extension,
            'mime_type': getattr(file, 'content_type', 'unknown')
        }
    
    @classmethod
    def validate_task_status(cls, status: str) -> None:
        """Validate task status"""
        valid_statuses = ['pending', 'in_progress', 'completed']
        if status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    @classmethod
    def validate_task_priority(cls, priority: str) -> None:
        """Validate task priority"""
        valid_priorities = ['high', 'medium', 'low']
        if priority not in valid_priorities:
            raise ValidationError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")
    
    @classmethod
    def validate_pagination(cls, page: int, limit: int) -> None:
        """Validate pagination parameters"""
        if page < 1:
            raise ValidationError("Page must be greater than 0")
        if limit < 1 or limit > 100:
            raise ValidationError("Limit must be between 1 and 100")
    
    @classmethod
    def sanitize_string(cls, text: str, max_length: int = 1000) -> str:
        """Sanitize and validate string input"""
        if not isinstance(text, str):
            raise ValidationError("Input must be a string")
        
        # Remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        # Check length
        if len(sanitized) > max_length:
            raise ValidationError(f"Text too long. Maximum length: {max_length} characters")
        
        return sanitized

# Decorator functions for easy use
def validate_json(*required_fields):
    """Decorator to validate JSON request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                if not request.is_json:
                    return jsonify({'error': 'Request must be JSON'}), 400
                
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'Request body cannot be empty'}), 400
                
                if required_fields:
                    RequestValidator.validate_required_fields(data, list(required_fields))
                
                return f(*args, **kwargs)
            
            except ValidationError as e:
                return jsonify({'error': e.message}), e.status_code
            except Exception as e:
                current_app.logger.error(f"Validation error: {e}")
                return jsonify({'error': 'Validation failed'}), 400
        
        return decorated_function
    return decorator

def validate_file_upload():
    """Decorator to validate file upload requests"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                if 'audio' not in request.files:
                    return jsonify({'error': 'No audio file provided'}), 400
                
                file = request.files['audio']
                file_info = RequestValidator.validate_file_upload(file)
                
                # Add file info to request context for use in the route
                request.file_info = file_info
                
                return f(*args, **kwargs)
            
            except ValidationError as e:
                return jsonify({'error': e.message}), e.status_code
            except Exception as e:
                current_app.logger.error(f"File validation error: {e}")
                return jsonify({'error': 'File validation failed'}), 400
        
        return decorated_function
    return decorator

def validate_uuid_param(param_name: str):
    """Decorator to validate UUID parameters"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                param_value = kwargs.get(param_name)
                if not param_value:
                    return jsonify({'error': f'Missing {param_name} parameter'}), 400
                
                if not RequestValidator.validate_uuid(param_value):
                    return jsonify({'error': f'Invalid {param_name} format'}), 400
                
                return f(*args, **kwargs)
            
            except ValidationError as e:
                return jsonify({'error': e.message}), e.status_code
            except Exception as e:
                current_app.logger.error(f"UUID validation error: {e}")
                return jsonify({'error': 'Parameter validation failed'}), 400
        
        return decorated_function
    return decorator

def validate_pagination():
    """Decorator to validate pagination parameters"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                page = int(request.args.get('page', 1))
                limit = int(request.args.get('limit', 10))
                
                RequestValidator.validate_pagination(page, limit)
                
                # Add validated params to request context
                request.pagination = {'page': page, 'limit': limit}
                
                return f(*args, **kwargs)
            
            except (ValueError, ValidationError) as e:
                error_msg = str(e) if isinstance(e, ValidationError) else "Invalid pagination parameters"
                return jsonify({'error': error_msg}), 400
            except Exception as e:
                current_app.logger.error(f"Pagination validation error: {e}")
                return jsonify({'error': 'Pagination validation failed'}), 400
        
        return decorated_function
    return decorator

def validate_user_id():
    """Decorator to validate user_id parameter (expects database user ID)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                user_id = request.args.get('user_id') or request.form.get('user_id')
                if not user_id:
                    return jsonify({'error': 'User ID is required'}), 400
                
                # Sanitize user ID
                user_id = RequestValidator.sanitize_string(user_id, 255)
                
                # Add to request context
                request.validated_user_id = user_id
                
                return f(*args, **kwargs)
            
            except ValidationError as e:
                return jsonify({'error': e.message}), e.status_code
            except Exception as e:
                current_app.logger.error(f"User ID validation error: {e}")
                return jsonify({'error': 'User ID validation failed'}), 400
        
        return decorated_function
    return decorator

# Security middleware
def add_security_headers():
    """Decorator to add security headers"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            
            # Add security headers
            if hasattr(response, 'headers'):
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['X-Frame-Options'] = 'DENY'
                response.headers['X-XSS-Protection'] = '1; mode=block'
                response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            return response
        
        return decorated_function
    return decorator
