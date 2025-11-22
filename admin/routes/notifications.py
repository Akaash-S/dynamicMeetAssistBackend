"""
Admin Notifications Management Routes
Handles system notifications, broadcasts, and user messaging
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import uuid
import logging
import asyncio
from functools import wraps
from config.aws_rds_database import rds_db
from config.auth_config import AuthConfig
from middleware.validation import require_admin_auth, add_security_headers, validate_json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

admin_notifications_bp = Blueprint('admin_notifications', __name__)

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

@admin_notifications_bp.route('', methods=['GET'])
@add_security_headers
@require_admin_auth
@async_route
async def get_notifications():
    """
    Get paginated list of notifications with filtering
    GET /api/admin/notifications%spage=1&per_page=20&type=&priority=&is_read=
    """
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        type_filter = request.args.get('type', '').strip()
        priority_filter = request.args.get('priority', '').strip()
        is_read_filter = request.args.get('is_read', '').strip()
        
        # Build base query
        base_query = """
        SELECT n.*, u.email as target_user_email, u.name as target_user_name
        FROM admin_notifications n
        LEFT JOIN users u ON n.target_user_id = u.id
        WHERE 1=1
        """
        
        count_query = """
        SELECT COUNT(*) as total
        FROM admin_notifications n
        LEFT JOIN users u ON n.target_user_id = u.id
        WHERE 1=1
        """
        
        params = []
        
        # Add filters
        if type_filter:
            base_query += " AND n.type = %s"
            count_query += " AND n.type = %s"
            params.append(type_filter)
            
        if priority_filter:
            base_query += " AND n.priority = %s"
            count_query += " AND n.priority = %s"
            params.append(priority_filter)
            
        if is_read_filter:
            is_read_bool = is_read_filter.lower() == 'true'
            base_query += " AND n.is_read = %s"
            count_query += " AND n.is_read = %s"
            params.append(is_read_bool)
        
        # Get total count
        total_result = rds_db.execute_query(count_query, tuple(params), fetch_one=True)
        total = total_result['total'] if total_result else 0
        
        # Calculate pagination
        pages = (total + per_page - 1) // per_page
        offset = (page - 1) * per_page
        
        # Add ordering and pagination
        base_query += " ORDER BY n.created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        # Execute query
        notifications = rds_db.execute_query(base_query, tuple(params), fetch_all=True)
        
        # Get notification statistics
        stats_query = """
        SELECT 
            COUNT(*) as total_notifications,
            COUNT(CASE WHEN is_read = false THEN 1 END) as unread_notifications,
            COUNT(CASE WHEN type = 'system' THEN 1 END) as system_notifications,
            COUNT(CASE WHEN type = 'user' THEN 1 END) as user_notifications,
            COUNT(CASE WHEN type = 'payment' THEN 1 END) as payment_notifications,
            COUNT(CASE WHEN type = 'issue' THEN 1 END) as issue_notifications,
            COUNT(CASE WHEN priority = 'urgent' THEN 1 END) as urgent_notifications
        FROM admin_notifications
        """
        
        stats_result = rds_db.execute_query(stats_query, fetch_one=True)
        stats = stats_result if stats_result else {}
        
        # Format notifications
        formatted_notifications = []
        for notification in notifications:
            formatted_notifications.append({
                'id': notification['id'],
                'message': notification['message'],
                'type': notification['type'],
                'priority': notification['priority'],
                'target_user_id': notification['target_user_id'],
                'target_user_email': notification.get('target_user_email'),
                'target_user_name': notification.get('target_user_name'),
                'is_read': notification['is_read'],
                'created_by': notification['created_by'],
                'created_at': notification['created_at'].isoformat() if notification['created_at'] else None
            })
        
        return jsonify({
            'success': True,
            'message': 'Notifications retrieved successfully',
            'data': {
                'items': formatted_notifications,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': pages,
                    'has_next': page < pages,
                    'has_prev': page > 1
                },
                'statistics': {
                    'total_notifications': stats.get('total_notifications', 0),
                    'unread_notifications': stats.get('unread_notifications', 0),
                    'system_notifications': stats.get('system_notifications', 0),
                    'user_notifications': stats.get('user_notifications', 0),
                    'payment_notifications': stats.get('payment_notifications', 0),
                    'issue_notifications': stats.get('issue_notifications', 0),
                    'urgent_notifications': stats.get('urgent_notifications', 0)
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get notifications error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve notifications',
            'error': str(e)
        }), 500

@admin_notifications_bp.route('/stats', methods=['GET'])
@add_security_headers
@require_admin_auth
@async_route
async def get_notification_stats():
    """
    Get notification statistics and analytics
    GET /api/admin/notifications/stats
    """
    try:
        # Overview statistics
        overview_query = """
        SELECT 
            COUNT(*) as total_notifications,
            COUNT(CASE WHEN is_read = false THEN 1 END) as unread_notifications,
            COUNT(CASE WHEN type = 'system' THEN 1 END) as system_notifications,
            COUNT(CASE WHEN type = 'user' THEN 1 END) as user_notifications,
            COUNT(CASE WHEN type = 'payment' THEN 1 END) as payment_notifications,
            COUNT(CASE WHEN type = 'issue' THEN 1 END) as issue_notifications,
            COUNT(CASE WHEN priority = 'urgent' THEN 1 END) as urgent_notifications,
            COUNT(CASE WHEN created_at >= %s THEN 1 END) as notifications_this_week
        FROM admin_notifications
        """
        
        # Calculate start of current week
        now = datetime.utcnow()
        week_start = now - timedelta(days=7)
        
        overview_result = rds_db.execute_query(overview_query, (week_start,), fetch_one=True)
        overview = overview_result if overview_result else {}
        
        # Type breakdown
        type_query = """
        SELECT type, COUNT(*) as count
        FROM admin_notifications 
        GROUP BY type
        ORDER BY count DESC
        """
        
        type_result = rds_db.execute_query(type_query, fetch_all=True)
        type_breakdown = [
            {
                'type': row['type'],
                'count': row['count']
            }
            for row in type_result
        ]
        
        return jsonify({
            'success': True,
            'message': 'Notification statistics retrieved successfully',
            'data': {
                'overview': {
                    'total_notifications': overview.get('total_notifications', 0),
                    'unread_notifications': overview.get('unread_notifications', 0),
                    'system_notifications': overview.get('system_notifications', 0),
                    'user_notifications': overview.get('user_notifications', 0),
                    'payment_notifications': overview.get('payment_notifications', 0),
                    'issue_notifications': overview.get('issue_notifications', 0),
                    'urgent_notifications': overview.get('urgent_notifications', 0),
                    'notifications_this_week': overview.get('notifications_this_week', 0)
                },
                'type_breakdown': type_breakdown
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get notification stats error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve notification statistics',
            'error': str(e)
        }), 500

@admin_notifications_bp.route('', methods=['POST'])
@add_security_headers
@require_admin_auth
@validate_json('message')
@async_route
async def create_notification():
    """
    Create a new notification
    POST /api/admin/notifications
    """
    try:
        data = request.get_json()
        admin_email = request.admin_user['email']
        
        # Generate notification ID
        notification_id = str(uuid.uuid4())
        
        # Create notification
        create_query = """
        INSERT INTO admin_notifications (
            id, message, type, priority, target_user_id, 
            is_read, created_by, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        rds_db.execute_query(create_query, (
            notification_id,
            data['message'],
            data.get('type', 'system'),
            data.get('priority', 'normal'),
            data.get('target_user_id'),
            False,
            admin_email,
            datetime.utcnow()
        ))
        
        # Log admin action
        from routes.admin_auth import log_admin_action
        log_admin_action(
            admin_email, 'CREATE_NOTIFICATION', 'notification', notification_id,
            f"Created notification: {data['message'][:50]}...",
            request.remote_addr, request.headers.get('User-Agent')
        )
        
        # Send email notification if target user is specified
        if data.get('target_user_id'):
            try:
                from utils.notification_email_sender import send_notification_email_async
                asyncio.create_task(send_notification_email_async(notification_id, data['target_user_id']))
                logger.info(f"Email notification queued for user {data['target_user_id']}")
            except Exception as email_error:
                logger.warning(f"Failed to queue email notification: {email_error}")
        
        return jsonify({
            'success': True,
            'message': 'Notification created successfully',
            'notification_id': notification_id
        }), 201
        
    except Exception as e:
        logger.error(f"Create notification error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to create notification',
            'error': str(e)
        }), 500

@admin_notifications_bp.route('/<notification_id>', methods=['PATCH'])
@add_security_headers
@require_admin_auth
@async_route
async def update_notification(notification_id):
    """
    Update notification details
    PATCH /api/admin/notifications/{notification_id}
    """
    try:
        data = request.get_json()
        admin_email = request.admin_user['email']
        
        # Check if notification exists
        notification_query = "SELECT * FROM admin_notifications WHERE id = %s"
        notifications = rds_db.execute_query(notification_query, (notification_id,), fetch_one=True)
        if not notifications:
            return jsonify({"error": "Resource not found"}), 404
        
        if not notifications:
            return jsonify({
                'success': False,
                'message': 'Notification not found'
            }), 404
        
        # Build update query
        update_fields = []
        params = []
        
        allowed_fields = ['message', 'type', 'priority', 'is_read']
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = %s")
                params.append(data[field])
        
        if not update_fields:
            return jsonify({
                'success': False,
                'message': 'No valid fields to update'
            }), 400
        
        params.append(notification_id)
        
        update_query = f"UPDATE admin_notifications SET {', '.join(update_fields)} WHERE id = %s"
        rds_db.execute_query(update_query, params)
        
        # Log admin action
        from routes.admin_auth import log_admin_action
        log_admin_action(
            admin_email, 'UPDATE_NOTIFICATION', 'notification', notification_id,
            f"Updated notification",
            request.remote_addr, request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Notification updated successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Update notification error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to update notification',
            'error': str(e)
        }), 500

@admin_notifications_bp.route('/<notification_id>', methods=['DELETE'])
@add_security_headers
@require_admin_auth
@async_route
async def delete_notification(notification_id):
    """
    Delete a notification
    DELETE /api/admin/notifications/{notification_id}
    """
    try:
        admin_email = request.admin_user['email']
        
        # Check if notification exists
        notification_query = "SELECT * FROM admin_notifications WHERE id = %s"
        notifications = rds_db.execute_query(notification_query, (notification_id,), fetch_one=True)
        if not notifications:
            return jsonify({"error": "Resource not found"}), 404
        
        if not notifications:
            return jsonify({
                'success': False,
                'message': 'Notification not found'
            }), 404
        
        # Delete notification
        delete_query = "DELETE FROM admin_notifications WHERE id = %s"
        rds_db.execute_query(delete_query, (notification_id,), fetch_one=True)
        
        # Log admin action
        from routes.admin_auth import log_admin_action
        log_admin_action(
            admin_email, 'DELETE_NOTIFICATION', 'notification', notification_id,
            f"Deleted notification",
            request.remote_addr, request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Notification deleted successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Delete notification error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to delete notification',
            'error': str(e)
        }), 500

@admin_notifications_bp.route('/broadcast', methods=['POST'])
@add_security_headers
@require_admin_auth
@validate_json('message')
@async_route
async def broadcast_notification():
    """
    Send a broadcast notification to all users
    POST /api/admin/notifications/broadcast
    """
    try:
        data = request.get_json()
        admin_email = request.admin_user['email']
        
        # Create broadcast notification (target_user_id = NULL means broadcast)
        notification_id = str(uuid.uuid4())
        
        create_query = """
        INSERT INTO admin_notifications (
            id, message, type, priority, target_user_id, 
            is_read, created_by, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        rds_db.execute_query(create_query, (
            notification_id,
            data['message'],
            data.get('type', 'system'),
            data.get('priority', 'normal'),
            None,  # NULL for broadcast
            False,
            admin_email,
            datetime.utcnow()
        ))
        
        # Log admin action
        from routes.admin_auth import log_admin_action
        log_admin_action(
            admin_email, 'BROADCAST_NOTIFICATION', 'notification', notification_id,
            f"Broadcast notification: {data['message'][:50]}...",
            request.remote_addr, request.headers.get('User-Agent')
        )
        
        # Send broadcast email to all users with email notifications enabled
        try:
            users_query = """
            SELECT id, email, name 
            FROM users 
            WHERE email_notifications = true AND email IS NOT NULL
            """
            users = rds_db.execute_query(users_query)
            
            if users:
                from utils.notification_email_sender import send_notification_email_async
                # Send emails asynchronously to all users
                for user in users:
                    asyncio.create_task(send_notification_email_async(notification_id, user['id']))
                
                logger.info(f"Broadcast email queued for {len(users)} users")
        except Exception as email_error:
            logger.warning(f"Failed to queue broadcast emails: {email_error}")
        
        return jsonify({
            'success': True,
            'message': 'Broadcast notification sent successfully',
            'notification_id': notification_id
        }), 201
        
    except Exception as e:
        logger.error(f"Broadcast notification error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to send broadcast notification',
            'error': str(e)
        }), 500

@admin_notifications_bp.route('/mark-all-read', methods=['PATCH'])
@add_security_headers
@require_admin_auth
@async_route
async def mark_all_read():
    """
    Mark all notifications as read
    PATCH /api/admin/notifications/mark-all-read
    """
    try:
        admin_email = request.admin_user['email']
        
        # Mark all notifications as read
        update_query = "UPDATE admin_notifications SET is_read = true WHERE is_read = false"
        rds_db.execute_query(update_query)
        
        # Log admin action
        from routes.admin_auth import log_admin_action
        log_admin_action(
            admin_email, 'MARK_ALL_READ', 'notification', 'all',
            "Marked all notifications as read",
            request.remote_addr, request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'All notifications marked as read'
        }), 200
        
    except Exception as e:
        logger.error(f"Mark all read error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to mark all notifications as read',
            'error': str(e)
        }), 500

@admin_notifications_bp.route('/templates', methods=['GET'])
@add_security_headers
@require_admin_auth
@async_route
async def get_notification_templates():
    """
    Get notification templates for common messages
    GET /api/admin/notifications/templates
    """
    try:
        templates = [
            {
                'id': 'welcome',
                'name': 'Welcome Message',
                'message': 'Welcome to Dynamic Meeting Assistant! We\'re excited to have you on board.',
                'type': 'user',
                'priority': 'normal'
            },
            {
                'id': 'maintenance',
                'name': 'Maintenance Notice',
                'message': 'System maintenance is scheduled for tonight at 2 AM EST. Expected downtime: 30 minutes.',
                'type': 'system',
                'priority': 'high'
            },
            {
                'id': 'payment_success',
                'name': 'Payment Successful',
                'message': 'Your payment has been processed successfully. Thank you for your purchase!',
                'type': 'payment',
                'priority': 'normal'
            },
            {
                'id': 'issue_resolved',
                'name': 'Issue Resolved',
                'message': 'Your support ticket has been resolved. If you need further assistance, please don\'t hesitate to contact us.',
                'type': 'issue',
                'priority': 'normal'
            },
            {
                'id': 'security_alert',
                'name': 'Security Alert',
                'message': 'We detected unusual activity on your account. Please review your recent activity and contact support if needed.',
                'type': 'system',
                'priority': 'urgent'
            }
        ]
        
        return jsonify({
            'success': True,
            'message': 'Notification templates retrieved successfully',
            'data': {
                'templates': templates
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get notification templates error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve notification templates',
            'error': str(e)
        }), 500
