"""
Simple Authentication Middleware for Firebase-authenticated routes
Uses X-User-ID header to identify users
"""

from functools import wraps
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)


def require_firebase_auth(f):
    """
    Simple decorator that requires X-User-ID header
    Used for routes that are called from Firebase-authenticated frontend
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get user ID from header
        user_id = request.headers.get('X-User-ID')
        
        if not user_id:
            logger.warning(f"Missing X-User-ID header for {request.method} {request.path}")
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'message': 'X-User-ID header is required'
            }), 401
        
        # Set current_user in request context
        request.current_user = {
            'id': user_id,
            'firebase_uid': user_id
        }
        
        logger.debug(f"Authenticated user {user_id} for {request.method} {request.path}")
        
        return f(*args, **kwargs)
    
    return decorated_function
