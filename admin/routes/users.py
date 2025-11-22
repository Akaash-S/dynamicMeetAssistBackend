"""
Admin User Management Routes for Unified Backend
CRUD operations for user management by admins
"""

from flask import Blueprint, request, jsonify
from config.aws_rds_database import rds_db
from config.auth_config import AuthConfig
from middleware.validation import RequestValidator, require_admin_auth, add_security_headers, validate_json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from admin.utils import log_admin_action
from datetime import datetime
import logging
import uuid
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

admin_users_bp = Blueprint('admin_users', __name__)

def async_route(f):
    """Decorator to run async functions in Flask routes"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper



@admin_users_bp.route('', methods=['GET'])
@add_security_headers
@require_admin_auth
@async_route
async def get_users():
    """
    Get all users with pagination and filtering
    GET /api/admin/users
    """
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        search = request.args.get('search', '').strip()
        role = request.args.get('role', '').strip()
        auth_provider = request.args.get('auth_provider', '').strip()
        
        # Build base query
        base_query = "SELECT * FROM users"
        count_query = "SELECT COUNT(*) as total FROM users"
        conditions = []
        params = []
        
        # Apply filters
        if search:
            conditions.append("(name ILIKE %s OR email ILIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
        
        if role and role in ['admin', 'user']:
            conditions.append("role = %s")
            params.append(role)
        
        if auth_provider and auth_provider in ['firebase', 'google_oauth', 'admin_email']:
            conditions.append("auth_provider = %s")
            params.append(auth_provider)
        
        # Add WHERE clause if conditions exist
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            base_query += where_clause
            count_query += where_clause
        
        # Get total count
        total_result = rds_db.execute_query(count_query, tuple(params), fetch_one=True)
        total = total_result['total'] if total_result else 0
        
        # Calculate pagination
        offset = (page - 1) * per_page
        pages = (total + per_page - 1) // per_page
        
        # Add ordering and pagination
        base_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        # Execute query
        users = rds_db.execute_query(base_query, tuple(params), fetch_all=True)
        
        # Get user statistics
        stats_query = """
        SELECT 
            COUNT(*) as total_users,
            COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_users,
            COUNT(CASE WHEN is_active = true THEN 1 END) as active_users,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as new_users_this_week
        FROM users
        """
        stats_result = rds_db.execute_query(stats_query, fetch_one=True)
        stats = stats_result if stats_result else {}
        
        # Format user data
        formatted_users = []
        for user in users:
            formatted_users.append({
                'id': str(user['id']),
                'email': user['email'],
                'name': user['name'],
                'role': user['role'],
                'auth_provider': user['auth_provider'],
                'is_active': user['is_active'],
                'last_login_at': user['last_login_at'].isoformat() if user['last_login_at'] else None,
                'created_at': user['created_at'].isoformat() if user['created_at'] else None,
                'updated_at': user['updated_at'].isoformat() if user['updated_at'] else None
            })
        
        return jsonify({
            'success': True,
            'message': 'Users retrieved successfully',
            'data': {
                'items': formatted_users,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': pages,
                    'has_next': page < pages,
                    'has_prev': page > 1
                },
                'statistics': {
                    'total_users': stats.get('total_users', 0),
                    'admin_users': stats.get('admin_users', 0),
                    'active_users': stats.get('active_users', 0),
                    'new_users_this_week': stats.get('new_users_this_week', 0)
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get users error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve users',
            'error': str(e)
        }), 500

@admin_users_bp.route('/<user_id>', methods=['GET'])
@add_security_headers
@require_admin_auth
@async_route
async def get_user_details(user_id):
    """
    Get detailed user information
    GET /api/admin/users/<user_id>
    """
    try:
        # Get user details
        user_query = "SELECT * FROM users WHERE id = %s"
        users = rds_db.execute_query(user_query, (user_id,), fetch_one=True)
        if not users:
            return jsonify({"error": "Resource not found"}), 404
        
        if not users:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        user = users[0]
        
        # Get user statistics
        stats_queries = {
            'meetings': "SELECT COUNT(*) as count FROM meetings WHERE user_id = %s",
            'tasks': "SELECT COUNT(*) as count FROM tasks WHERE meeting_id IN (SELECT id FROM meetings WHERE user_id = %s)",
            'issues': "SELECT COUNT(*) as count FROM admin_issues WHERE user_id = %s",
            'payments': "SELECT COUNT(*) as count FROM admin_payments WHERE user_id = %s"
        }
        
        user_stats = {}
        for stat_name, query in stats_queries.items():
            result = rds_db.execute_query(query, (user_id,), fetch_one=True)
            user_stats[f'total_{stat_name}'] = result['count'] if result else 0
        
        # Format user data
        user_data = {
            'id': str(user['id']),
            'email': user['email'],
            'name': user['name'],
            'role': user['role'],
            'auth_provider': user['auth_provider'],
            'is_active': user['is_active'],
            'email_notifications': user['email_notifications'],
            'in_app_notifications': user['in_app_notifications'],
            'google_calendar_enabled': user['google_calendar_enabled'],
            'last_login_at': user['last_login_at'].isoformat() if user['last_login_at'] else None,
            'created_at': user['created_at'].isoformat() if user['created_at'] else None,
            'updated_at': user['updated_at'].isoformat() if user['updated_at'] else None,
            'statistics': user_stats
        }
        
        return jsonify({
            'success': True,
            'message': 'User details retrieved successfully',
            'data': {
                'user': user_data
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get user details error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve user details',
            'error': str(e)
        }), 500

@admin_users_bp.route('/<user_id>', methods=['PUT'])
@add_security_headers
@require_admin_auth
@validate_json('name')
@async_route
async def update_user(user_id):
    """
    Update user information
    PUT /api/admin/users/<user_id>
    """
    try:
        data = request.get_json()
        admin_email = request.admin_user['email']
        
        # Check if user exists
        user_query = "SELECT * FROM users WHERE id = %s"
        users = rds_db.execute_query(user_query, (user_id,), fetch_one=True)
        if not users:
            return jsonify({"error": "Resource not found"}), 404
        
        if not users:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        user = users[0]
        
        # Prepare update data
        updates = []
        params = []
        changes = []
        
        # Update name
        if 'name' in data and data['name'].strip():
            new_name = RequestValidator.sanitize_string(data['name'], 255)
            if user['name'] != new_name:
                updates.append("name = %s")
                params.append(new_name)
                changes.append(f"name: '{user['name']}' → '{new_name}'")
        
        # Update role (admin only)
        if 'role' in data and data['role'] in ['admin', 'user']:
            new_role = data['role']
            if user['role'] != new_role:
                # Prevent self-demotion
                if user['email'] == admin_email and new_role != 'admin':
                    return jsonify({
                        'success': False,
                        'message': 'Cannot change your own admin role'
                    }), 400
                
                updates.append("role = %s")
                params.append(new_role)
                changes.append(f"role: '{user['role']}' → '{new_role}'")
        
        # Update active status
        if 'is_active' in data:
            new_is_active = bool(data['is_active'])
            if user['is_active'] != new_is_active:
                updates.append("is_active = %s")
                params.append(new_is_active)
                changes.append(f"is_active: {user['is_active']} → {new_is_active}")
        
        # Update notification preferences
        for field in ['email_notifications', 'in_app_notifications', 'google_calendar_enabled']:
            if field in data:
                new_value = bool(data[field])
                if user[field] != new_value:
                    updates.append(f"{field} = %s")
                    params.append(new_value)
                    changes.append(f"{field}: {user[field]} → {new_value}")
        
        if not updates:
            return jsonify({
                'success': True,
                'message': 'No changes made to user',
                'data': {
                    'user': {
                        'id': str(user['id']),
                        'email': user['email'],
                        'name': user['name'],
                        'role': user['role']
                    }
                }
            }), 200
        
        # Add updated_at
        updates.append("updated_at = %s")
        params.append(datetime.utcnow())
        
        # Execute update
        update_query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
        params.append(user_id)
        
        rds_db.execute_query(update_query, params)
        
        # Log admin action
        log_admin_action(
            admin_email=admin_email,
            action='UPDATE_USER',
            resource_type='user',
            resource_id=str(user_id),
            details=f"Updated user {user['email']}: {', '.join(changes)}"
        )
        
        # Get updated user
        updated_users = rds_db.execute_query(user_query, (user_id,), fetch_one=True)
        if not updated_users:
            return jsonify({"error": "Resource not found"}), 404
        updated_user = updated_users[0]
        
        logger.info(f"User updated: {user_id} by {admin_email}")
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'data': {
                'user': {
                    'id': str(updated_user['id']),
                    'email': updated_user['email'],
                    'name': updated_user['name'],
                    'role': updated_user['role'],
                    'is_active': updated_user['is_active']
                },
                'changes': changes
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to update user',
            'error': str(e)
        }), 500

@admin_users_bp.route('/<user_id>', methods=['DELETE'])
@add_security_headers
@require_admin_auth
@async_route
async def delete_user(user_id):
    """
    Delete a user (soft delete by deactivating)
    DELETE /api/admin/users/<user_id>
    """
    try:
        admin_email = request.admin_user['email']
        
        # Check if user exists
        user_query = "SELECT * FROM users WHERE id = %s"
        users = rds_db.execute_query(user_query, (user_id,), fetch_one=True)
        if not users:
            return jsonify({"error": "Resource not found"}), 404
        
        if not users:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        user = users[0]
        
        # Prevent self-deletion
        if user['email'] == admin_email:
            return jsonify({
                'success': False,
                'message': 'Cannot delete your own account'
            }), 400
        
        # Soft delete by deactivating the user
        deactivate_query = "UPDATE users SET is_active = false, updated_at = %s WHERE id = %s"
        rds_db.execute_query(deactivate_query, (datetime.utcnow(), user_id))
        
        # Log admin action
        log_admin_action(
            admin_email=admin_email,
            action='DELETE_USER',
            resource_type='user',
            resource_id=str(user_id),
            details=f"Deactivated user {user['email']}"
        )
        
        logger.info(f"User deactivated: {user_id} by {admin_email}")
        
        return jsonify({
            'success': True,
            'message': 'User deactivated successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to delete user',
            'error': str(e)
        }), 500

@admin_users_bp.route('/stats', methods=['GET'])
@add_security_headers
@require_admin_auth
@async_route
async def get_user_stats():
    """
    Get comprehensive user statistics
    GET /api/admin/users/stats
    """
    try:
        # Overview statistics
        overview_query = """
        SELECT 
            COUNT(*) as total_users,
            COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_users,
            COUNT(CASE WHEN is_active = true THEN 1 END) as active_users,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as new_users_this_week,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as new_users_this_month,
            COUNT(CASE WHEN last_login_at >= NOW() - INTERVAL '7 days' THEN 1 END) as active_users_this_week
        FROM users
        """
        
        overview_result = rds_db.execute_query(overview_query, fetch_one=True)
        overview = overview_result if overview_result else {}
        
        # Auth provider breakdown
        auth_provider_query = """
        SELECT auth_provider, COUNT(*) as count
        FROM users
        GROUP BY auth_provider
        """
        
        auth_provider_result = rds_db.execute_query(auth_provider_query, fetch_all=True)
        auth_provider_breakdown = {row['auth_provider']: row['count'] for row in (auth_provider_result or [])}
        
        # Registration trends (last 30 days)
        trends_query = """
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as registrations
        FROM users
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date
        """
        
        trends_result = rds_db.execute_query(trends_query, fetch_all=True)
        registration_trends = [
            {
                'date': row['date'].isoformat(),
                'registrations': row['registrations']
            }
            for row in trends_result
        ]
        
        return jsonify({
            'success': True,
            'message': 'User statistics retrieved successfully',
            'data': {
                'overview': {
                    'total_users': overview.get('total_users', 0),
                    'admin_users': overview.get('admin_users', 0),
                    'active_users': overview.get('active_users', 0),
                    'new_users_this_week': overview.get('new_users_this_week', 0),
                    'new_users_this_month': overview.get('new_users_this_month', 0),
                    'active_users_this_week': overview.get('active_users_this_week', 0)
                },
                'auth_provider_breakdown': auth_provider_breakdown,
                'registration_trends': registration_trends
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get user stats error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve user statistics',
            'error': str(e)
        }), 500
