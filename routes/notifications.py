from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid

from config.aws_rds_database import rds_db
from middleware.validation import add_security_headers

notifications_bp = Blueprint('notifications', __name__)

def _resolve_db_user_id(raw_user_id: str):
    """Return internal UUID user id. Accepts UUID or Firebase UID string."""
    if not raw_user_id:
        return None
    try:
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        if re.match(uuid_pattern, raw_user_id, re.IGNORECASE):
            return raw_user_id
        row = rds_db.execute_query("SELECT id FROM users WHERE firebase_uid = %s", (raw_user_id,), fetch_one=True)
        if row and row.get('id'):
            return row['id']
    except Exception:
        pass
    return None

@notifications_bp.route('', methods=['GET'])
@add_security_headers()
def get_notifications():
    """Get notifications for a user"""
    try:
        raw_user_id = request.args.get('user_id')
        if not raw_user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        user_id = _resolve_db_user_id(raw_user_id)
        if not user_id:
            return jsonify({'error': 'Invalid user ID'}), 400
        
        # Get filter parameters
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = min(int(request.args.get('limit', 50)), 100)
        
        # Build query
        query = """
        SELECT * FROM notifications 
        WHERE user_id = %s
        """
        params = [user_id]
        
        if unread_only:
            query += " AND is_read = FALSE"
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        notifications = rds_db.execute_query(query, params, fetch_all=True)
        
        # Format notifications
        formatted_notifications = []
        for notif in notifications or []:
            formatted_notifications.append({
                'id': notif['id'],
                'type': notif['type'],
                'title': notif['title'],
                'message': notif['message'],
                'data': notif['data'],
                'is_read': notif['is_read'],
                'created_at': notif['created_at'].isoformat() if notif['created_at'] else None
            })
        
        # Get unread count
        count_query = "SELECT COUNT(*) as count FROM notifications WHERE user_id = %s AND is_read = FALSE"
        count_result = rds_db.execute_query(count_query, (user_id,), fetch_one=True)
        unread_count = count_result['count'] if count_result else 0
        
        return jsonify({
            'notifications': formatted_notifications,
            'unread_count': unread_count,
            'total': len(formatted_notifications)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get notifications: {str(e)}'}), 500

@notifications_bp.route('/<notification_id>/read', methods=['PUT'])
@add_security_headers()
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        update_query = """
        UPDATE notifications 
        SET is_read = TRUE, read_at = %s 
        WHERE id = %s
        """
        
        rds_db.execute_query(update_query, (datetime.utcnow(), notification_id))
        
        return jsonify({
            'success': True,
            'message': 'Notification marked as read'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to mark notification as read: {str(e)}'}), 500

@notifications_bp.route('/mark-all-read', methods=['PUT'])
@add_security_headers()
def mark_all_read():
    """Mark all notifications as read for a user"""
    try:
        raw_user_id = request.args.get('user_id')
        if not raw_user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        user_id = _resolve_db_user_id(raw_user_id)
        if not user_id:
            return jsonify({'error': 'Invalid user ID'}), 400
        
        update_query = """
        UPDATE notifications 
        SET is_read = TRUE, read_at = %s 
        WHERE user_id = %s AND is_read = FALSE
        """
        
        rds_db.execute_query(update_query, (datetime.utcnow(), user_id))
        
        return jsonify({
            'success': True,
            'message': 'All notifications marked as read'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to mark all notifications as read: {str(e)}'}), 500

@notifications_bp.route('/<notification_id>', methods=['DELETE'])
@add_security_headers()
def delete_notification(notification_id):
    """Delete a notification"""
    try:
        delete_query = "DELETE FROM notifications WHERE id = %s"
        rds_db.execute_query(delete_query, (notification_id,))
        
        return jsonify({
            'success': True,
            'message': 'Notification deleted'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to delete notification: {str(e)}'}), 500

def create_notification(user_id: str, notification_type: str, title: str, message: str, data: dict = None):
    """
    Helper function to create a notification
    
    Types:
    - meeting_completed: Meeting processing completed
    - transcription_ready: Transcription is ready
    - timeline_generated: Timeline has been generated
    - tasks_extracted: Tasks have been extracted
    - calendar_synced: Tasks synced to calendar
    - task_due_soon: Task deadline approaching
    - task_overdue: Task is overdue
    """
    try:
        notification_id = str(uuid.uuid4())
        
        insert_query = """
        INSERT INTO notifications (id, user_id, type, title, message, data, is_read, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        rds_db.execute_query(insert_query, (
            notification_id,
            user_id,
            notification_type,
            title,
            message,
            data,
            False,
            datetime.utcnow()
        ))
        
        print(f"✅ Created notification: {notification_type} for user {user_id}")
        return notification_id
        
    except Exception as e:
        print(f"❌ Failed to create notification: {e}")
        return None
