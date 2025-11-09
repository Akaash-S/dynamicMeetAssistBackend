"""
Authentication Middleware for Role-Based Access Control
Provides decorators for protecting routes based on user roles
"""

from functools import wraps
from flask import request, jsonify
from config.auth_config import AuthConfig
from config.database import get_db
import logging

logger = logging.getLogger(__name__)

def require_auth(allowed_roles=None):
    """
    Decorator to require authentication for routes
    
    Args:
        allowed_roles (list): List of allowed roles ['user', 'admin']. 
                             If None, any authenticated user is allowed.
    
    Usage:
        @require_auth()  # Any authenticated user
        @require_auth(['user'])  # Only regular users
        @require_auth(['admin'])  # Only admins
        @require_auth(['user', 'admin'])  # Both users and admins
    """
    if allowed_roles is None:
        allowed_roles = ['user', 'admin']
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            
            if not auth_header:
                return jsonify({
                    'success': False,
                    'error': 'Authorization required',
                    'message': 'Please provide an authorization token'
                }), 401
            
            # Extract token
            if not auth_header.startswith('Bearer '):
                return jsonify({
                    'success': False,
                    'error': 'Invalid authorization format',
                    'message': 'Authorization header must be in format: Bearer <token>'
                }), 401
            
            token = auth_header.split(' ')[1]
            
            # Verify token
            payload = AuthConfig.verify_jwt_token(token)
            if not payload:
                return jsonify({
                    'success': False,
                    'error': 'Invalid or expired token',
                    'message': 'Please log in again'
                }), 401
            
            # Get user from database to verify role
            try:
                user_query = "SELECT * FROM users WHERE id = %s"
                users = get_db().execute_query(user_query, (payload['user_id'],))
                
                if not users:
                    return jsonify({
                        'success': False,
                        'error': 'User not found',
                        'message': 'User account no longer exists'
                    }), 404
                
                user = users[0]
                
                # Check if user role is allowed
                if user['role'] not in allowed_roles:
                    return jsonify({
                        'success': False,
                        'error': 'Access denied',
                        'message': f'This endpoint requires {" or ".join(allowed_roles)} role'
                    }), 403
                
                # Add user info to request context
                request.current_user = {
                    'id': str(user['id']),
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role'],
                    'firebase_uid': user.get('firebase_uid'),
                    'google_oauth_id': user.get('google_oauth_id')
                }
                
                logger.info(f"Authenticated {user['role']}: {user['email']} for {request.method} {request.path}")
                
            except Exception as e:
                logger.error(f"Auth middleware error: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Authentication failed',
                    'message': 'Unable to verify user credentials'
                }), 500
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_user_auth():
    """
    Decorator to require regular user authentication (not admin)
    Shorthand for @require_auth(['user'])
    """
    return require_auth(['user'])


def require_admin_auth():
    """
    Decorator to require admin authentication
    Shorthand for @require_auth(['admin'])
    """
    return require_auth(['admin'])


def require_any_auth():
    """
    Decorator to require any authenticated user (user or admin)
    Shorthand for @require_auth(['user', 'admin'])
    """
    return require_auth(['user', 'admin'])


def optional_auth():
    """
    Decorator for optional authentication
    Adds user info to request if authenticated, but doesn't require it
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                
                # Verify token
                payload = AuthConfig.verify_jwt_token(token)
                if payload:
                    try:
                        # Get user from database
                        user_query = "SELECT * FROM users WHERE id = %s"
                        users = get_db().execute_query(user_query, (payload['user_id'],))
                        
                        if users:
                            user = users[0]
                            request.current_user = {
                                'id': str(user['id']),
                                'email': user['email'],
                                'name': user['name'],
                                'role': user['role'],
                                'firebase_uid': user.get('firebase_uid'),
                                'google_oauth_id': user.get('google_oauth_id')
                            }
                    except Exception as e:
                        logger.warning(f"Optional auth failed: {e}")
            
            # Continue even if auth failed
            if not hasattr(request, 'current_user'):
                request.current_user = None
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def get_current_user():
    """
    Get the current authenticated user from request context
    
    Returns:
        dict: User info if authenticated, None otherwise
    """
    return getattr(request, 'current_user', None)


def is_admin():
    """
    Check if current user is an admin
    
    Returns:
        bool: True if current user is admin, False otherwise
    """
    user = get_current_user()
    return user and user.get('role') == 'admin'


def is_user():
    """
    Check if current user is a regular user
    
    Returns:
        bool: True if current user is a regular user, False otherwise
    """
    user = get_current_user()
    return user and user.get('role') == 'user'
