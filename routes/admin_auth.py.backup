"""
ADMIN APP Authentication Routes
================================
This module handles authentication for the ADMIN DASHBOARD APP ONLY.
Admin users (role='admin') authenticate here using EMAIL + PASSWORD.

AUTHENTICATION METHOD:
- ✅ Email + Password - ONLY METHOD for admins
- ❌ Google Sign-In - NOT SUPPORTED (use Email + Password instead)
- ❌ Firebase Auth - NOT SUPPORTED (client app only)

IMPORTANT:
- These routes are for ADMIN APP users only (role='admin')
- All authentication is done through Email + Password
- Passwords are hashed with bcrypt for security
- JWT tokens are used for session management
- Client users MUST use /api/auth/* endpoints (Google Sign-In)
- Admin actions are logged in admin_logs table

Endpoints:
- POST /api/admin/auth/login - Admin login (Email + Password)
- POST /api/admin/auth/verify-token - Verify JWT token
- POST /api/admin/auth/logout - Admin logout
- GET /api/admin/auth/profile - Get admin profile

For client authentication (Google Sign-In), see: backend/routes/auth.py
"""

from flask import Blueprint, request, jsonify, make_response
from config.aws_rds_database import rds_db
from config.auth_config import AuthConfig, session_manager
from middleware.validation import validate_json, add_security_headers, RequestValidator, require_admin_auth
from datetime import datetime
import logging
import secrets
import uuid

logger = logging.getLogger(__name__)

admin_auth_bp = Blueprint('admin_auth', __name__)

@admin_auth_bp.route('/login', methods=['POST'])
@add_security_headers()
@validate_json('email', 'password')
def admin_login():
    """
    Admin login with email and password
    POST /api/admin/auth/login
    """
    try:
        data = request.get_json()
        
        email = RequestValidator.sanitize_string(data.get('email', '')).lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400

        # Validate email format
        if not RequestValidator.validate_email(email):
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400

        # Check if it's the default admin from environment
        if AuthConfig.is_default_admin(email, password):
            # Find or create default admin user
            user_query = "SELECT * FROM users WHERE email = %s"
            users = rds_db.execute_query(user_query, (email,), fetch_one=True)
            if not users:
                return jsonify({"error": "Resource not found"}), 404
            
            if not users:
                # Create default admin user
                user_id = str(uuid.uuid4())
                create_user_query = """
                INSERT INTO users (id, email, name, role, auth_provider, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                rds_db.execute_query(create_user_query, (
                    user_id, email, AuthConfig.DEFAULT_ADMIN_NAME, 'admin', 
                    'admin_email', True, datetime.utcnow(), datetime.utcnow()
                ))
                
                # Fetch the created user
                users = rds_db.execute_query(user_query, (email,), fetch_one=True)
                if not users:
                    return jsonify({"error": "Resource not found"}), 404
                logger.info(f"Created default admin user: {email}")
            
            user = users[0]
        else:
            # Check database for user with password hash
            user_query = "SELECT * FROM users WHERE email = %s AND password_hash IS NOT NULL"
            users = rds_db.execute_query(user_query, (email,), fetch_one=True)
            if not users:
                return jsonify({"error": "Resource not found"}), 404
            
            if not users:
                return jsonify({
                    'success': False,
                    'message': 'Invalid email or password'
                }), 401
            
            user = users[0]
            
            if not AuthConfig.verify_password(password, user['password_hash']):
                return jsonify({
                    'success': False,
                    'message': 'Invalid email or password'
                }), 401

        # Check if user is admin
        if user['role'] != 'admin':
            return jsonify({
                'success': False,
                'message': 'Admin access required'
            }), 403

        # Update last login
        update_login_query = "UPDATE users SET last_login_at = %s WHERE id = %s"
        rds_db.execute_query(update_login_query, (datetime.utcnow(), user['id']))

        # Generate JWT token
        token = AuthConfig.generate_jwt_token({
            'id': user['id'],
            'email': user['email'],
            'role': user['role'],
            'name': user['name'],
            'auth_provider': user['auth_provider']
        })

        # Create session
        session_id = session_manager.create_session({
            'id': user['id'],
            'email': user['email'],
            'role': user['role'],
            'name': user['name'],
            'auth_provider': user['auth_provider']
        })

        # Log admin action
        log_admin_action(
            admin_email=user['email'],
            action='LOGIN',
            resource_type='auth',
            details=f"Admin login successful from {request.remote_addr}"
        )

        logger.info(f"Admin login successful: {user['email']}")

        # Create response with security headers
        response_data = {
            'success': True,
            'message': 'Login successful',
            'data': {
                'token': token,
                'session_id': session_id,
                'user': {
                    'id': str(user['id']),
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role']
                }
            }
        }
        
        response = make_response(jsonify(response_data), 200)
        
        # Add security headers
        for header, value in AuthConfig.get_security_headers().items():
            response.headers[header] = value
            
        return response

    except Exception as e:
        logger.error(f"Admin login error: {e}")
        return jsonify({
            'success': False,
            'message': 'Login failed',
            'error': str(e)
        }), 500

@admin_auth_bp.route('/verify-token', methods=['POST'])
@add_security_headers()
@validate_json('token')
def verify_admin_token():
    """
    Verify JWT token and return user info
    POST /api/admin/auth/verify-token
    """
    try:
        data = request.get_json()
        token = data['token']
        
        payload = AuthConfig.verify_jwt_token(token)
        if not payload:
            return jsonify({
                'success': False,
                'message': 'Invalid or expired token'
            }), 401

        # Get user from database
        user_query = "SELECT * FROM users WHERE id = %s"
        users = rds_db.execute_query(user_query, (payload['user_id'],), fetch_one=True)
        if not users:
            return jsonify({"error": "Resource not found"}), 404
        
        if not users:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        user = users[0]

        # Check if user is still admin
        if user['role'] != 'admin':
            return jsonify({
                'success': False,
                'message': 'Admin access revoked'
            }), 403

        return jsonify({
            'success': True,
            'message': 'Token verified successfully',
            'data': {
                'user': {
                    'id': str(user['id']),
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role'],
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None,
                    'updated_at': user['updated_at'].isoformat() if user['updated_at'] else None
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return jsonify({
            'success': False,
            'message': 'Token verification failed',
            'error': str(e)
        }), 500

@admin_auth_bp.route('/logout', methods=['POST'])
@add_security_headers()
def admin_logout():
    """
    Admin logout - invalidate session
    POST /api/admin/auth/logout
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            payload = AuthConfig.verify_jwt_token(token)
            
            if payload:
                # Log admin action
                log_admin_action(
                    admin_email=payload.get('email', 'unknown'),
                    action='LOGOUT',
                    resource_type='auth',
                    details=f"Admin logout from {request.remote_addr}"
                )
        
        # Delete session if provided
        if session_id:
            session_manager.delete_session(session_id)
        
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        }), 200
        
    except Exception as e:
        logger.error(f"Admin logout error: {e}")
        return jsonify({
            'success': True,  # Return success even on error
            'message': 'Logout completed'
        }), 200

@admin_auth_bp.route('/profile', methods=['GET'])
@add_security_headers()
def get_admin_profile():
    """
    Get current admin profile
    GET /api/admin/auth/profile
    """
    try:
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

        # Get user from database
        user_query = "SELECT * FROM users WHERE id = %s AND role = 'admin'"
        users = rds_db.execute_query(user_query, (payload['user_id'],), fetch_one=True)
        if not users:
            return jsonify({"error": "Resource not found"}), 404
        
        if not users:
            return jsonify({
                'success': False,
                'message': 'Admin user not found'
            }), 404

        user = users[0]
        
        return jsonify({
            'success': True,
            'message': 'Profile retrieved successfully',
            'data': {
                'user': {
                    'id': str(user['id']),
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role'],
                    'auth_provider': user['auth_provider'],
                    'last_login_at': user['last_login_at'].isoformat() if user['last_login_at'] else None,
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None,
                    'updated_at': user['updated_at'].isoformat() if user['updated_at'] else None
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Get admin profile error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to get profile',
            'error': str(e)
        }), 500

def log_admin_action(admin_email: str, action: str, resource_type: str = None, 
                    resource_id: str = None, details: str = None):
    """
    Log admin action to database
    
    Args:
        admin_email (str): Email of admin performing action
        action (str): Action performed
        resource_type (str): Type of resource affected
        resource_id (str): ID of affected resource
        details (str): Additional details about the action
    """
    try:
        # Get request info
        ip_address = request.remote_addr if request else None
        user_agent = request.headers.get('User-Agent') if request else None
        
        # Insert log entry
        log_query = """
        INSERT INTO admin_logs (admin_email, action, resource_type, resource_id, details, ip_address, user_agent, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        rds_db.execute_query(log_query, (
            admin_email, action, resource_type, resource_id, details,
            ip_address, user_agent, datetime.utcnow()
        ))
        
        logger.info(f"Admin action logged: {admin_email} - {action}")
        
    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")
        # Don't raise exception to avoid breaking the main operation
