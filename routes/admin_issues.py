"""
Admin Issues Management Routes for Unified Backend
CRUD operations for support ticket management
"""

from flask import Blueprint, request, jsonify
from config.database import get_db
from config.auth_config import AuthConfig
from middleware.validation import RequestValidator, require_admin_auth, add_security_headers, validate_json
from routes.admin_auth import log_admin_action
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

admin_issues_bp = Blueprint('admin_issues', __name__)

@admin_issues_bp.route('', methods=['GET'])
@add_security_headers
@require_admin_auth
def get_issues():
    """
    Get all issues with pagination and filtering
    GET /api/admin/issues
    """
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        status = request.args.get('status', '').strip()
        priority = request.args.get('priority', '').strip()
        category = request.args.get('category', '').strip()
        search = request.args.get('search', '').strip()
        
        # Build query with user information
        base_query = """
        SELECT i.*, u.email as user_email, u.name as user_name
        FROM admin_issues i
        LEFT JOIN users u ON i.user_id = u.id
        """
        
        count_query = "SELECT COUNT(*) as total FROM admin_issues i"
        conditions = []
        params = []
        
        # Apply filters
        if status and status in ['open', 'in_progress', 'resolved', 'closed']:
            conditions.append("i.status = %s")
            params.append(status)
        
        if priority and priority in ['low', 'medium', 'high', 'urgent']:
            conditions.append("i.priority = %s")
            params.append(priority)
        
        if category:
            conditions.append("i.category = %s")
            params.append(category)
        
        if search:
            conditions.append("(i.title ILIKE %s OR i.description ILIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
        
        # Add WHERE clause if conditions exist
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            base_query += where_clause
            count_query += where_clause
        
        # Get total count
        total_result = get_db().execute_query(count_query, params)
        total = total_result[0]['total'] if total_result else 0
        
        # Calculate pagination
        offset = (page - 1) * per_page
        pages = (total + per_page - 1) // per_page
        
        # Add ordering and pagination
        base_query += " ORDER BY i.created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        # Execute query
        issues = get_db().execute_query(base_query, params)
        
        # Get issue statistics
        stats_query = """
        SELECT 
            COUNT(*) as total_issues,
            COUNT(CASE WHEN status = 'open' THEN 1 END) as open_issues,
            COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_issues,
            COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_issues,
            COUNT(CASE WHEN priority = 'urgent' THEN 1 END) as urgent_issues,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as new_issues_this_week
        FROM admin_issues
        """
        
        stats_result = get_db().execute_query(stats_query)
        stats = stats_result[0] if stats_result else {}
        
        # Format issue data
        formatted_issues = []
        for issue in issues:
            formatted_issues.append({
                'id': str(issue['id']),
                'user_id': str(issue['user_id']) if issue['user_id'] else None,
                'user_email': issue['user_email'],
                'user_name': issue['user_name'],
                'title': issue['title'],
                'description': issue['description'],
                'status': issue['status'],
                'priority': issue['priority'],
                'category': issue['category'],
                'assigned_to': issue['assigned_to'],
                'resolved_by': issue['resolved_by'],
                'created_at': issue['created_at'].isoformat() if issue['created_at'] else None,
                'updated_at': issue['updated_at'].isoformat() if issue['updated_at'] else None,
                'resolved_at': issue['resolved_at'].isoformat() if issue['resolved_at'] else None
            })
        
        return jsonify({
            'success': True,
            'message': 'Issues retrieved successfully',
            'data': {
                'items': formatted_issues,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': pages,
                    'has_next': page < pages,
                    'has_prev': page > 1
                },
                'statistics': {
                    'total_issues': stats.get('total_issues', 0),
                    'open_issues': stats.get('open_issues', 0),
                    'in_progress_issues': stats.get('in_progress_issues', 0),
                    'resolved_issues': stats.get('resolved_issues', 0),
                    'urgent_issues': stats.get('urgent_issues', 0),
                    'new_issues_this_week': stats.get('new_issues_this_week', 0)
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get issues error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve issues',
            'error': str(e)
        }), 500

@admin_issues_bp.route('/report', methods=['POST'])
@add_security_headers
@validate_json('title', 'description', 'user_email')
def report_issue():
    """
    Report an issue from frontend (no auth required)
    POST /api/admin/issues/report
    """
    try:
        data = request.get_json()
        
        # Get user by email or create a guest entry
        user_query = "SELECT id FROM users WHERE email = %s"
        users = get_db().execute_query(user_query, (data['user_email'],))
        
        if users:
            user_id = users[0]['id']
        else:
            # For guest users reporting issues, we'll still create the issue
            # but mark it as from an unregistered user
            user_id = None
        
        # Generate issue ID
        issue_id = str(uuid.uuid4())
        
        # Create issue
        create_query = """
        INSERT INTO admin_issues (id, user_id, title, description, status, priority, category, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        get_db().execute_query(create_query, (
            issue_id,
            user_id,
            data['title'],
            data['description'],
            'open',
            data.get('priority', 'medium'),
            data.get('category', 'technical'),
            datetime.utcnow(),
            datetime.utcnow()
        ))
        
        return jsonify({
            'success': True,
            'message': 'Issue reported successfully',
            'issue_id': issue_id
        }), 201
        
    except Exception as e:
        logger.error(f"Report issue error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to report issue',
            'error': str(e)
        }), 500

@admin_issues_bp.route('', methods=['POST'])
@add_security_headers
@require_admin_auth
@validate_json('title', 'user_email')
def create_issue():
    """
    Create a new issue
    POST /api/admin/issues
    """
    try:
        data = request.get_json()
        admin_email = request.admin_user['email']
        
        # Get user by email
        user_query = "SELECT id FROM users WHERE email = %s"
        users = get_db().execute_query(user_query, (data['user_email'],))
        
        if not users:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        user_id = users[0]['id']
        
        # Create issue
        issue_id = str(uuid.uuid4())
        create_query = """
        INSERT INTO admin_issues (id, user_id, title, description, status, priority, category, assigned_to, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        get_db().execute_query(create_query, (
            issue_id,
            user_id,
            RequestValidator.sanitize_string(data['title'], 255),
            RequestValidator.sanitize_string(data.get('description', ''), 5000),
            data.get('status', 'open'),
            data.get('priority', 'medium'),
            RequestValidator.sanitize_string(data.get('category', ''), 100),
            admin_email,  # Assign to creating admin
            datetime.utcnow(),
            datetime.utcnow()
        ))
        
        # Log admin action
        log_admin_action(
            admin_email=admin_email,
            action='CREATE_ISSUE',
            resource_type='issue',
            resource_id=issue_id,
            details=f"Created issue '{data['title']}' for user {data['user_email']}"
        )
        
        logger.info(f"Issue created: {issue_id} by {admin_email}")
        
        return jsonify({
            'success': True,
            'message': 'Issue created successfully',
            'data': {
                'issue_id': issue_id
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Create issue error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to create issue',
            'error': str(e)
        }), 500

@admin_issues_bp.route('/<issue_id>', methods=['PATCH'])
@add_security_headers
@require_admin_auth
def update_issue(issue_id):
    """
    Update issue status and details
    PATCH /api/admin/issues/<issue_id>
    """
    try:
        data = request.get_json()
        admin_email = request.admin_user['email']
        
        # Check if issue exists
        issue_query = "SELECT * FROM admin_issues WHERE id = %s"
        issues = get_db().execute_query(issue_query, (issue_id,))
        
        if not issues:
            return jsonify({
                'success': False,
                'message': 'Issue not found'
            }), 404
        
        issue = issues[0]
        
        # Prepare update data
        updates = []
        params = []
        changes = []
        
        # Update status
        if 'status' in data and data['status'] in ['open', 'in_progress', 'resolved', 'closed']:
            new_status = data['status']
            if issue['status'] != new_status:
                updates.append("status = %s")
                params.append(new_status)
                changes.append(f"status: '{issue['status']}' → '{new_status}'")
                
                # Set resolved_at and resolved_by if resolving
                if new_status == 'resolved':
                    updates.extend(["resolved_at = %s", "resolved_by = %s"])
                    params.extend([datetime.utcnow(), admin_email])
                    changes.append(f"resolved by: {admin_email}")
        
        # Update priority
        if 'priority' in data and data['priority'] in ['low', 'medium', 'high', 'urgent']:
            new_priority = data['priority']
            if issue['priority'] != new_priority:
                updates.append("priority = %s")
                params.append(new_priority)
                changes.append(f"priority: '{issue['priority']}' → '{new_priority}'")
        
        # Update assigned_to
        if 'assigned_to' in data:
            new_assigned = RequestValidator.sanitize_string(data['assigned_to'], 255)
            if issue['assigned_to'] != new_assigned:
                updates.append("assigned_to = %s")
                params.append(new_assigned)
                changes.append(f"assigned_to: '{issue['assigned_to']}' → '{new_assigned}'")
        
        if not updates:
            return jsonify({
                'success': True,
                'message': 'No changes made to issue',
                'data': {
                    'issue_id': issue_id
                }
            }), 200
        
        # Add updated_at
        updates.append("updated_at = %s")
        params.append(datetime.utcnow())
        
        # Execute update
        update_query = f"UPDATE admin_issues SET {', '.join(updates)} WHERE id = %s"
        params.append(issue_id)
        
        get_db().execute_query(update_query, params)
        
        # Log admin action
        log_admin_action(
            admin_email=admin_email,
            action='UPDATE_ISSUE',
            resource_type='issue',
            resource_id=issue_id,
            details=f"Updated issue: {', '.join(changes)}"
        )
        
        logger.info(f"Issue updated: {issue_id} by {admin_email}")
        
        return jsonify({
            'success': True,
            'message': 'Issue updated successfully',
            'data': {
                'issue_id': issue_id,
                'changes': changes
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Update issue error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to update issue',
            'error': str(e)
        }), 500

@admin_issues_bp.route('/stats', methods=['GET'])
@add_security_headers
@require_admin_auth
def get_issue_stats():
    """
    Get issue statistics and analytics
    GET /api/admin/issues/stats
    """
    try:
        # Overview statistics
        overview_query = """
        SELECT 
            COUNT(*) as total_issues,
            COUNT(CASE WHEN status = 'open' THEN 1 END) as open_issues,
            COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_issues,
            COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_issues,
            COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_issues,
            COUNT(CASE WHEN priority = 'urgent' THEN 1 END) as urgent_issues,
            COUNT(CASE WHEN created_at >= %s THEN 1 END) as new_issues_this_week
        FROM admin_issues
        """
        
        # Calculate start of current week
        from datetime import timedelta
        now = datetime.utcnow()
        week_start = now - timedelta(days=7)
        
        overview_result = get_db().execute_query(overview_query, (week_start,))
        overview = overview_result[0] if overview_result else {}
        
        # Category breakdown
        category_query = """
        SELECT category, COUNT(*) as count
        FROM admin_issues 
        GROUP BY category
        ORDER BY count DESC
        """
        
        category_result = get_db().execute_query(category_query)
        category_breakdown = [
            {
                'category': row['category'],
                'count': row['count']
            }
            for row in category_result
        ]
        
        # Priority breakdown
        priority_query = """
        SELECT priority, COUNT(*) as count
        FROM admin_issues 
        GROUP BY priority
        ORDER BY 
            CASE priority 
                WHEN 'urgent' THEN 1 
                WHEN 'high' THEN 2 
                WHEN 'medium' THEN 3 
                WHEN 'low' THEN 4 
            END
        """
        
        priority_result = get_db().execute_query(priority_query)
        priority_breakdown = [
            {
                'priority': row['priority'],
                'count': row['count']
            }
            for row in priority_result
        ]
        
        return jsonify({
            'success': True,
            'message': 'Issue statistics retrieved successfully',
            'data': {
                'overview': {
                    'total_issues': overview.get('total_issues', 0),
                    'open_issues': overview.get('open_issues', 0),
                    'in_progress_issues': overview.get('in_progress_issues', 0),
                    'resolved_issues': overview.get('resolved_issues', 0),
                    'closed_issues': overview.get('closed_issues', 0),
                    'urgent_issues': overview.get('urgent_issues', 0),
                    'new_issues_this_week': overview.get('new_issues_this_week', 0)
                },
                'category_breakdown': category_breakdown,
                'priority_breakdown': priority_breakdown
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get issue stats error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve issue statistics',
            'error': str(e)
        }), 500