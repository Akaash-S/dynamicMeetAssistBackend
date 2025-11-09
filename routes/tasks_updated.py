"""
Tasks Routes with Google Calendar Sync
Updated to automatically sync task changes to Google Calendar
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import traceback

from config.database import get_db
from services.calendar_sync import calendar_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tasks_bp = Blueprint('tasks', __name__)


def _resolve_db_user_id(raw_user_id: str):
    """Resolve user ID from either UUID or Firebase UID"""
    if not raw_user_id:
        return None
    try:
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        if re.match(uuid_pattern, raw_user_id, re.IGNORECASE):
            return raw_user_id
        row = get_db().execute_query("SELECT id FROM users WHERE firebase_uid = %s", (raw_user_id,))
        if row and len(row) > 0 and row[0].get('id'):
            return row[0]['id']
    except Exception:
        pass
    return None


def _sync_task_to_calendar(task_id: str, action: str = 'update'):
    """
    Helper function to sync task changes to Google Calendar
    
    Args:
        task_id: Task ID to sync
        action: 'create', 'update', or 'delete'
    """
    try:
        # Get task details
        task_query = """
        SELECT t.*, m.title as meeting_title, u.google_access_token, u.google_refresh_token
        FROM tasks t
        JOIN meetings m ON t.meeting_id = m.id
        JOIN users u ON t.user_id = u.id
        WHERE t.id = %s AND u.google_calendar_enabled = TRUE
        """
        task_result = get_db().execute_query(task_query, (task_id,))
        
        if not task_result:
            logger.info(f"Task {task_id} not found or calendar not enabled")
            return {'success': False, 'error': 'Task not found or calendar not enabled'}
        
        task = task_result[0]
        access_token = task.get('google_access_token')
        refresh_token = task.get('google_refresh_token')
        
        if not access_token:
            logger.info(f"No calendar access token for task {task_id}")
            return {'success': False, 'error': 'No calendar access token'}
        
        # Perform calendar action
        if action == 'create':
            result = calendar_service.create_google_calendar_event(
                task=task,
                meeting_title=task['meeting_title'],
                access_token=access_token,
                refresh_token=refresh_token
            )
            
            # Update task with calendar event ID
            if result['success']:
                update_query = "UPDATE tasks SET calendar_event_id = %s WHERE id = %s"
                get_db().execute_query(update_query, (result['event_id'], task_id))
                logger.info(f"✅ Task {task_id} synced to calendar: {result['event_id']}")
            
            return result
            
        elif action == 'update' and task.get('calendar_event_id'):
            result = calendar_service.update_calendar_event(
                event_id=task['calendar_event_id'],
                task=task,
                meeting_title=task['meeting_title'],
                access_token=access_token,
                refresh_token=refresh_token
            )
            logger.info(f"✅ Calendar event updated for task {task_id}")
            return result
            
        elif action == 'delete' and task.get('calendar_event_id'):
            result = calendar_service.delete_calendar_event(
                event_id=task['calendar_event_id'],
                access_token=access_token,
                refresh_token=refresh_token
            )
            logger.info(f"✅ Calendar event deleted for task {task_id}")
            return result
        
        return {'success': True, 'message': 'No calendar action needed'}
        
    except Exception as e:
        logger.error(f"❌ Error syncing task to calendar: {e}")
        return {'success': False, 'error': str(e)}


@tasks_bp.route('', methods=['GET'])
def get_tasks():
    """Get all tasks for a user"""
    try:
        raw_user_id = request.args.get('user_id')
        logger.info(f"📋 Fetching tasks for raw_user_id: {raw_user_id}")
        
        if not raw_user_id:
            logger.warning("❌ No user_id provided in request")
            return jsonify({'error': 'User ID is required'}), 400

        import re
        is_uuid = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', raw_user_id or '', re.IGNORECASE) is not None
        logger.info(f"🔎 user_id_mode: {'uuid' if is_uuid else 'firebase_uid'}")
        
        # Get filter parameters
        status = request.args.get('status')
        priority = request.args.get('priority')
        meeting_id = request.args.get('meeting_id')
        
        # Build query
        if is_uuid:
            where_sql = "t.user_id = %s"
            where_param = raw_user_id
        else:
            where_sql = "t.user_id = (SELECT id FROM users WHERE firebase_uid = %s)"
            where_param = raw_user_id

        query = f"""
        SELECT t.*, m.title as meeting_title 
        FROM tasks t
        JOIN meetings m ON t.meeting_id = m.id
        WHERE {where_sql}
        """
        params = [where_param]
        
        if status:
            query += " AND t.status = %s"
            params.append(status)
        
        if priority:
            query += " AND t.priority = %s"
            params.append(priority)
        
        if meeting_id:
            query += " AND t.meeting_id = %s"
            params.append(meeting_id)
        
        query += " ORDER BY t.deadline ASC NULLS LAST, t.created_at DESC"
        
        logger.info(f"🔍 Executing query with params: {params}")
        tasks = get_db().execute_query(query, params)
        logger.info(f"✅ Found {len(tasks) if tasks else 0} tasks")
        
        # Format tasks
        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append({
                'id': task['id'],
                'meeting_id': task['meeting_id'],
                'meeting_title': task['meeting_title'],
                'title': task['title'],
                'description': task['description'],
                'assigned_to': task['assigned_to'],
                'deadline': task['deadline'].isoformat() if task['deadline'] else None,
                'priority': task['priority'],
                'status': task['status'],
                'calendar_event_id': task['calendar_event_id'],
                'created_at': task['created_at'].isoformat() if task['created_at'] else None,
                'updated_at': task['updated_at'].isoformat() if task['updated_at'] else None
            })
        
        return jsonify({
            'tasks': formatted_tasks,
            'total': len(formatted_tasks),
            'filters': {
                'status': status,
                'priority': priority,
                'meeting_id': meeting_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error fetching tasks: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to get tasks: {str(e)}'}), 500


@tasks_bp.route('/<task_id>', methods=['PUT'])
def update_task(task_id):
    """Update task details and sync to Google Calendar"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Check if task exists
        check_query = "SELECT * FROM tasks WHERE id = %s"
        check_result = get_db().execute_query(check_query, (task_id,))
        
        if not check_result:
            return jsonify({'error': 'Task not found'}), 404
        
        current_task = check_result[0]
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        if 'title' in data:
            update_fields.append("title = %s")
            params.append(data['title'])
        
        if 'description' in data:
            update_fields.append("description = %s")
            params.append(data['description'])
        
        if 'assigned_to' in data:
            update_fields.append("assigned_to = %s")
            params.append(data['assigned_to'])
        
        if 'deadline' in data:
            if data['deadline']:
                try:
                    deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
                    update_fields.append("deadline = %s")
                    params.append(deadline)
                except ValueError:
                    return jsonify({'error': 'Invalid deadline format. Use ISO format.'}), 400
            else:
                update_fields.append("deadline = NULL")
        
        if 'priority' in data:
            valid_priorities = ['high', 'medium', 'low']
            if data['priority'] not in valid_priorities:
                return jsonify({'error': f'Invalid priority. Must be one of: {valid_priorities}'}), 400
            update_fields.append("priority = %s")
            params.append(data['priority'])
        
        if 'status' in data:
            valid_statuses = ['pending', 'in_progress', 'completed']
            if data['status'] not in valid_statuses:
                return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400
            update_fields.append("status = %s")
            params.append(data['status'])
        
        if not update_fields:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        # Add updated_at
        update_fields.append("updated_at = %s")
        params.append(datetime.utcnow())
        
        # Add task_id for WHERE clause
        params.append(task_id)
        
        # Execute update
        update_query = f"""
        UPDATE tasks 
        SET {', '.join(update_fields)}
        WHERE id = %s
        """
        
        updated_count = get_db().execute_query(update_query, params)
        
        if updated_count > 0:
            # Get updated task
            updated_task_result = get_db().execute_query(check_query, (task_id,))
            updated_task = updated_task_result[0]
            
            # Sync to Google Calendar
            calendar_result = _sync_task_to_calendar(task_id, action='update')
            
            return jsonify({
                'success': True,
                'message': 'Task updated successfully',
                'calendar_synced': calendar_result.get('success', False),
                'task': {
                    'id': updated_task['id'],
                    'title': updated_task['title'],
                    'description': updated_task['description'],
                    'assigned_to': updated_task['assigned_to'],
                    'deadline': updated_task['deadline'].isoformat() if updated_task['deadline'] else None,
                    'priority': updated_task['priority'],
                    'status': updated_task['status'],
                    'calendar_event_id': updated_task.get('calendar_event_id'),
                    'updated_at': updated_task['updated_at'].isoformat() if updated_task['updated_at'] else None
                }
            }), 200
        else:
            return jsonify({'error': 'Failed to update task'}), 500
        
    except Exception as e:
        logger.error(f"❌ Error updating task: {str(e)}")
        return jsonify({'error': f'Failed to update task: {str(e)}'}), 500


@tasks_bp.route('/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete task and remove from Google Calendar"""
    try:
        # Sync deletion to calendar first (before deleting from DB)
        calendar_result = _sync_task_to_calendar(task_id, action='delete')
        
        # Delete task from database
        delete_query = "DELETE FROM tasks WHERE id = %s"
        deleted_count = get_db().execute_query(delete_query, (task_id,))
        
        if deleted_count > 0:
            return jsonify({
                'success': True,
                'message': 'Task deleted successfully',
                'calendar_synced': calendar_result.get('success', False)
            }), 200
        else:
            return jsonify({'error': 'Task not found'}), 404
        
    except Exception as e:
        logger.error(f"❌ Error deleting task: {str(e)}")
        return jsonify({'error': f'Failed to delete task: {str(e)}'}), 500


@tasks_bp.route('/<task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    """Update task status and sync to Google Calendar"""
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        new_status = data['status']
        valid_statuses = ['pending', 'in_progress', 'completed']
        
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400
        
        # Check if task exists
        check_query = "SELECT id FROM tasks WHERE id = %s"
        check_result = get_db().execute_query(check_query, (task_id,))
        
        if not check_result:
            return jsonify({'error': 'Task not found'}), 404
        
        # Update task status
        update_query = """
        UPDATE tasks 
        SET status = %s, updated_at = %s 
        WHERE id = %s
        """
        
        updated_count = get_db().execute_query(update_query, (new_status, datetime.utcnow(), task_id))
        
        if updated_count > 0:
            # Sync to Google Calendar
            calendar_result = _sync_task_to_calendar(task_id, action='update')
            
            return jsonify({
                'success': True,
                'message': f'Task status updated to {new_status}',
                'calendar_synced': calendar_result.get('success', False)
            }), 200
        else:
            return jsonify({'error': 'Failed to update task status'}), 500
        
    except Exception as e:
        logger.error(f"❌ Error updating task status: {str(e)}")
        return jsonify({'error': f'Failed to update task status: {str(e)}'}), 500


@tasks_bp.route('/stats', methods=['GET'])
def get_task_stats():
    """Get task statistics for a user"""
    try:
        raw_user_id = request.args.get('user_id')
        
        if not raw_user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        import re
        is_uuid = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', raw_user_id or '', re.IGNORECASE) is not None
        
        if is_uuid:
            where_sql = "user_id = %s"
            where_param = raw_user_id
        else:
            where_sql = "user_id = (SELECT id FROM users WHERE firebase_uid = %s)"
            where_param = raw_user_id
        
        # Get task counts by status
        stats_query = f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN priority = 'high' THEN 1 ELSE 0 END) as high_priority,
            SUM(CASE WHEN deadline < NOW() AND status != 'completed' THEN 1 ELSE 0 END) as overdue
        FROM tasks
        WHERE {where_sql}
        """
        
        stats_result = get_db().execute_query(stats_query, (where_param,))
        
        if stats_result:
            stats = stats_result[0]
            return jsonify({
                'total': int(stats['total'] or 0),
                'pending': int(stats['pending'] or 0),
                'in_progress': int(stats['in_progress'] or 0),
                'completed': int(stats['completed'] or 0),
                'high_priority': int(stats['high_priority'] or 0),
                'overdue': int(stats['overdue'] or 0)
            }), 200
        else:
            return jsonify({
                'total': 0,
                'pending': 0,
                'in_progress': 0,
                'completed': 0,
                'high_priority': 0,
                'overdue': 0
            }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting task stats: {str(e)}")
        return jsonify({'error': f'Failed to get task stats: {str(e)}'}), 500


@tasks_bp.route('/upcoming', methods=['GET'])
def get_upcoming_tasks():
    """Get upcoming tasks (next 7 days)"""
    try:
        raw_user_id = request.args.get('user_id')
        
        if not raw_user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        import re
        is_uuid = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', raw_user_id or '', re.IGNORECASE) is not None
        
        if is_uuid:
            where_sql = "t.user_id = %s"
            where_param = raw_user_id
        else:
            where_sql = "t.user_id = (SELECT id FROM users WHERE firebase_uid = %s)"
            where_param = raw_user_id
        
        query = f"""
        SELECT t.*, m.title as meeting_title
        FROM tasks t
        JOIN meetings m ON t.meeting_id = m.id
        WHERE {where_sql}
        AND t.deadline IS NOT NULL
        AND t.deadline >= NOW()
        AND t.deadline <= NOW() + INTERVAL '7 days'
        AND t.status != 'completed'
        ORDER BY t.deadline ASC
        LIMIT 10
        """
        
        tasks = get_db().execute_query(query, (where_param,))
        
        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append({
                'id': task['id'],
                'title': task['title'],
                'deadline': task['deadline'].isoformat() if task['deadline'] else None,
                'priority': task['priority'],
                'meeting_title': task['meeting_title']
            })
        
        return jsonify({'tasks': formatted_tasks}), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting upcoming tasks: {str(e)}")
        return jsonify({'error': f'Failed to get upcoming tasks: {str(e)}'}), 500
