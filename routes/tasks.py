from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import traceback

from config.aws_rds_database import rds_db
def _resolve_db_user_id(raw_user_id: str):
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
from services.calendar_sync import calendar_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tasks_bp = Blueprint('tasks', __name__)

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
        status = request.args.get('status')  # pending, in_progress, completed
        priority = request.args.get('priority')  # high, medium, low
        meeting_id = request.args.get('meeting_id')
        
        # Build query - use database user_id directly
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
        tasks = rds_db.execute_query(query, params, fetch_all=True)
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
        logger.error(f"❌ Error fetching tasks for user {raw_user_id}: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return jsonify({
            'error': f'Failed to get tasks: {str(e)}',
            'user_id': raw_user_id,
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@tasks_bp.route('/upcoming', methods=['GET'])
def get_upcoming_tasks():
    """Get upcoming tasks with deadlines"""
    try:
        raw_user_id = request.args.get('user_id')
        if not raw_user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        days_ahead = int(request.args.get('days', 30))
        
        # Use the same user_id resolution logic as other endpoints
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
        AND t.deadline <= NOW() + INTERVAL '{days_ahead} days'
        AND t.status != 'completed'
        ORDER BY t.deadline ASC
        """
        
        tasks = rds_db.execute_query(query, (where_param,), fetch_all=True)
        
        # Format tasks
        formatted_tasks = []
        for task in tasks or []:
            # Calculate days until deadline
            if task['deadline']:
                days_until = (task['deadline'].date() - datetime.now().date()).days
            else:
                days_until = None
            
            formatted_tasks.append({
                'id': task['id'],
                'meeting_id': task['meeting_id'],
                'meeting_title': task['meeting_title'],
                'title': task['title'],
                'description': task['description'],
                'assigned_to': task['assigned_to'],
                'deadline': task['deadline'].isoformat() if task['deadline'] else None,
                'days_until_deadline': days_until,
                'priority': task['priority'],
                'status': task['status'],
                'is_overdue': days_until < 0 if days_until is not None else False
            })
        
        return jsonify({
            'upcoming_tasks': formatted_tasks,
            'total': len(formatted_tasks),
            'days_ahead': days_ahead
        }), 200
        
    except Exception as e:
        # Log full traceback for server diagnostics
        logger.error(f"Error in get_upcoming_tasks: {e}")
        logger.error(traceback.format_exc())
        
        msg = str(e).lower()
        # If tasks table (or referenced columns) do not exist yet, fail gracefully
        if 'relation \"tasks\" does not exist' in msg or 'relation \'tasks\'' in msg:
            logger.warning("Tasks table does not exist yet. Returning empty upcoming_tasks response.")
            return jsonify({
                'upcoming_tasks': [],
                'total': 0,
                'days_ahead': int(request.args.get('days', 30))
            }), 200
        
        return jsonify({'error': f'Failed to get upcoming tasks: {str(e)}'}), 500

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
            where_sql = "t.user_id = %s"
            where_param = raw_user_id
        else:
            where_sql = "t.user_id = (SELECT id FROM users WHERE firebase_uid = %s)"
            where_param = raw_user_id

        stats = {}
        
        # Total tasks
        total_query = f"""
        SELECT COALESCE(COUNT(*), 0) as count
        FROM tasks t
        WHERE {where_sql}
        """
        total_result = rds_db.execute_query(total_query, (where_param,), fetch_one=True)
        stats['total_tasks'] = int(total_result['count']) if total_result else 0
        
        # Tasks by status
        status_query = f"""
        SELECT t.status, COALESCE(COUNT(*), 0) as count
        FROM tasks t
        WHERE {where_sql}
        GROUP BY t.status
        """
        status_result = rds_db.execute_query(status_query, (where_param,), fetch_all=True)
        stats['by_status'] = {row['status']: int(row['count']) for row in status_result} if status_result else {}
        
        # Tasks by priority
        priority_query = f"""
        SELECT t.priority, COALESCE(COUNT(*), 0) as count
        FROM tasks t
        WHERE {where_sql}
        GROUP BY t.priority
        """
        priority_result = rds_db.execute_query(priority_query, (where_param,), fetch_all=True)
        stats['by_priority'] = {row['priority']: int(row['count']) for row in priority_result} if priority_result else {}
        
        # Overdue tasks
        overdue_query = f"""
        SELECT COALESCE(COUNT(*), 0) as count
        FROM tasks t
        WHERE {where_sql}
        AND t.deadline IS NOT NULL
        AND t.deadline < NOW() 
        AND t.status != 'completed'
        """
        overdue_result = rds_db.execute_query(overdue_query, (where_param,), fetch_one=True)
        stats['overdue_tasks'] = int(overdue_result['count']) if overdue_result else 0
        
        # Due this week
        week_query = f"""
        SELECT COALESCE(COUNT(*), 0) as count
        FROM tasks t
        WHERE {where_sql}
        AND t.deadline IS NOT NULL
        AND t.deadline BETWEEN NOW() AND NOW() + INTERVAL '7 days'
        AND t.status != 'completed'
        """
        week_result = rds_db.execute_query(week_query, (where_param,), fetch_one=True)
        stats['due_this_week'] = int(week_result['count']) if week_result else 0
        
        # Completion rate
        total = stats['total_tasks']
        completed = stats['by_status'].get('completed', 0)
        stats['completion_rate'] = round((completed / total) * 100, 2) if total > 0 else 0
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get task stats: {str(e)}'}), 500

@tasks_bp.route('/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get specific task details"""
    try:
        query = """
        SELECT t.*, m.title as meeting_title 
        FROM tasks t
        JOIN meetings m ON t.meeting_id = m.id
        WHERE t.id = %s
        """
        
        result = rds_db.execute_query(query, (task_id,), fetch_one=True)
        if not result:
            return jsonify({"error": "Resource not found"}), 404
        
        if not result:
            return jsonify({'error': 'Task not found'}), 404
        
        task = result[0]
        
        return jsonify({
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
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get task: {str(e)}'}), 500

@tasks_bp.route('/<task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    """Update task status"""
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
        check_result = rds_db.execute_query(check_query, (task_id,), fetch_one=True)
        if not check_result:
            return jsonify({"error": "Resource not found"}), 404
        
        if not check_result:
            return jsonify({'error': 'Task not found'}), 404
        
        # Update task status
        update_query = """
        UPDATE tasks 
        SET status = %s, updated_at = %s 
        WHERE id = %s
        """
        
        updated_count = rds_db.execute_query(update_query, (new_status, datetime.utcnow(), task_id))
        
        if updated_count > 0:
            # Update calendar event if exists
            calendar_result = calendar_service.update_task_status(task_id, new_status)
            
            return jsonify({
                'success': True,
                'message': f'Task status updated to {new_status}',
                'calendar_updated': calendar_result.get('success', False)
            }), 200
        else:
            return jsonify({'error': 'Failed to update task status'}), 500
        
    except Exception as e:
        return jsonify({'error': f'Failed to update task status: {str(e)}'}), 500

@tasks_bp.route('/<task_id>', methods=['PUT'])
def update_task(task_id):
    """Update task details"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Check if task exists
        check_query = "SELECT * FROM tasks WHERE id = %s"
        check_result = rds_db.execute_query(check_query, (task_id,), fetch_one=True)
        if not check_result:
            return jsonify({"error": "Resource not found"}), 404
        
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
        
        updated_count = rds_db.execute_query(update_query, params)
        
        if updated_count > 0:
            # Get updated task
            updated_task_result = rds_db.execute_query(check_query, (task_id,), fetch_one=True)
            if not updated_task_result:
                return jsonify({"error": "Resource not found"}), 404
            updated_task = updated_task_result[0]
            
            return jsonify({
                'success': True,
                'message': 'Task updated successfully',
                'task': {
                    'id': updated_task['id'],
                    'title': updated_task['title'],
                    'description': updated_task['description'],
                    'assigned_to': updated_task['assigned_to'],
                    'deadline': updated_task['deadline'].isoformat() if updated_task['deadline'] else None,
                    'priority': updated_task['priority'],
                    'status': updated_task['status'],
                    'updated_at': updated_task['updated_at'].isoformat() if updated_task['updated_at'] else None
                }
            }), 200
        else:
            return jsonify({'error': 'Failed to update task'}), 500
        
    except Exception as e:
        return jsonify({'error': f'Failed to update task: {str(e)}'}), 500

@tasks_bp.route('/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    try:
        # Check if task exists
        check_query = "SELECT id FROM tasks WHERE id = %s"
        check_result = rds_db.execute_query(check_query, (task_id,), fetch_one=True)
        if not check_result:
            return jsonify({"error": "Resource not found"}), 404
        
        if not check_result:
            return jsonify({'error': 'Task not found'}), 404
        
        # Delete task
        delete_query = "DELETE FROM tasks WHERE id = %s"
        deleted_count = rds_db.execute_query(delete_query, (task_id,), fetch_one=True)
        if not deleted_count:
            return jsonify({"error": "Resource not found"}), 404
        
        if deleted_count > 0:
            # Delete calendar event if exists
            calendar_result = calendar_service.delete_task_event(task_id)
            
            return jsonify({
                'success': True,
                'message': 'Task deleted successfully',
                'calendar_deleted': calendar_result.get('success', False)
            }), 200
        else:
            return jsonify({'error': 'Failed to delete task'}), 500
        
    except Exception as e:
        return jsonify({'error': f'Failed to delete task: {str(e)}'}), 500
