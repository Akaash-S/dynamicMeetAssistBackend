"""
Action Executor
===============
Executes actions on behalf of the chatbot (create, update, delete tasks/meetings)
"""

from typing import Dict, Optional, Any
from datetime import datetime
from config.aws_rds_database import rds_db
import uuid
import logging

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes actions on user data"""
    
    def __init__(self, user_id: str):
        """
        Initialize action executor
        
        Args:
            user_id: User ID
        """
        self.user_id = user_id
    
    def execute(
        self,
        action_type: str,
        entity_type: str,
        parameters: Dict[str, Any]
    ) -> Dict:
        """
        Execute an action
        
        Args:
            action_type: Type of action (create, update, delete)
            entity_type: Type of entity (task, meeting)
            parameters: Action parameters
            
        Returns:
            Action result
        """
        try:
            if entity_type == 'task':
                if action_type == 'create':
                    return self._create_task(parameters)
                elif action_type == 'update':
                    return self._update_task(parameters)
                elif action_type == 'delete':
                    return self._delete_task(parameters)
            elif entity_type == 'meeting':
                if action_type == 'create':
                    return self._create_meeting(parameters)
                elif action_type == 'update':
                    return self._update_meeting(parameters)
                elif action_type == 'delete':
                    return self._delete_meeting(parameters)
            
            return {
                'success': False,
                'error': f'Unsupported action: {action_type} on {entity_type}'
            }
            
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_task(self, params: Dict) -> Dict:
        """Create a new task"""
        try:
            task_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO tasks (
                id, user_id, title, description, status, priority, 
                deadline, assigned_to, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            rds_db.execute_query(query, (
                task_id,
                self.user_id,
                params.get('title', 'Untitled Task'),
                params.get('description'),
                params.get('status', 'pending'),
                params.get('priority', 'medium'),
                params.get('deadline'),
                params.get('assigned_to'),
                datetime.utcnow(),
                datetime.utcnow()
            ))
            
            logger.info(f"Created task {task_id}")
            
            return {
                'success': True,
                'action': 'create_task',
                'data': {
                    'id': task_id,
                    'title': params.get('title', 'Untitled Task'),
                    'status': params.get('status', 'pending'),
                    'priority': params.get('priority', 'medium')
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return {
                'success': False,
                'error': f'Failed to create task: {str(e)}'
            }
    
    def _update_task(self, params: Dict) -> Dict:
        """Update an existing task"""
        try:
            task_id = params.get('id')
            if not task_id:
                # Try to find task by title
                title = params.get('title')
                if title:
                    query = "SELECT id FROM tasks WHERE user_id = %s AND title LIKE %s LIMIT 1"
                    result = rds_db.execute_query(query, (self.user_id, f'%{title}%'), fetch_all=True)
                    if result:
                        task_id = result[0]['id']
            
            if not task_id:
                return {
                    'success': False,
                    'error': 'Task not found. Please specify which task to update.'
                }
            
            # Build update query dynamically
            update_fields = []
            update_values = []
            
            if 'title' in params and params['title']:
                update_fields.append('title = %s')
                update_values.append(params['title'])
            
            if 'description' in params:
                update_fields.append('description = %s')
                update_values.append(params['description'])
            
            if 'status' in params and params['status']:
                update_fields.append('status = %s')
                update_values.append(params['status'])
            
            if 'priority' in params and params['priority']:
                update_fields.append('priority = %s')
                update_values.append(params['priority'])
            
            if 'deadline' in params:
                update_fields.append('deadline = %s')
                update_values.append(params['deadline'])
            
            if 'assigned_to' in params:
                update_fields.append('assigned_to = %s')
                update_values.append(params['assigned_to'])
            
            if not update_fields:
                return {
                    'success': False,
                    'error': 'No fields to update'
                }
            
            update_fields.append('updated_at = %s')
            update_values.append(datetime.utcnow())
            
            update_values.extend([task_id, self.user_id])
            
            query = f"""
            UPDATE tasks 
            SET {', '.join(update_fields)}
            WHERE id = %s AND user_id = %s
            """
            
            rds_db.execute_query(query, tuple(update_values))
            
            logger.info(f"Updated task {task_id}")
            
            return {
                'success': True,
                'action': 'update_task',
                'data': {
                    'id': task_id,
                    'updated_fields': list(params.keys())
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return {
                'success': False,
                'error': f'Failed to update task: {str(e)}'
            }
    
    def _delete_task(self, params: Dict) -> Dict:
        """Delete a task"""
        try:
            task_id = params.get('id')
            if not task_id:
                # Try to find task by title
                title = params.get('title')
                if title:
                    query = "SELECT id FROM tasks WHERE user_id = %s AND title LIKE %s LIMIT 1"
                    result = rds_db.execute_query(query, (self.user_id, f'%{title}%'), fetch_all=True)
                    if result:
                        task_id = result[0]['id']
            
            if not task_id:
                return {
                    'success': False,
                    'error': 'Task not found. Please specify which task to delete.'
                }
            
            query = "DELETE FROM tasks WHERE id = %s AND user_id = %s"
            rds_db.execute_query(query, (task_id, self.user_id))
            
            logger.info(f"Deleted task {task_id}")
            
            return {
                'success': True,
                'action': 'delete_task',
                'data': {
                    'id': task_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return {
                'success': False,
                'error': f'Failed to delete task: {str(e)}'
            }
    
    def _create_meeting(self, params: Dict) -> Dict:
        """Create a new meeting"""
        try:
            meeting_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO meetings (
                id, user_id, title, summary, status, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            rds_db.execute_query(query, (
                meeting_id,
                self.user_id,
                params.get('title', 'Untitled Meeting'),
                params.get('summary') or params.get('description'),
                params.get('status', 'scheduled'),
                datetime.utcnow(),
                datetime.utcnow()
            ))
            
            logger.info(f"Created meeting {meeting_id}")
            
            return {
                'success': True,
                'action': 'create_meeting',
                'data': {
                    'id': meeting_id,
                    'title': params.get('title', 'Untitled Meeting'),
                    'status': params.get('status', 'scheduled')
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating meeting: {e}")
            return {
                'success': False,
                'error': f'Failed to create meeting: {str(e)}'
            }
    
    def _update_meeting(self, params: Dict) -> Dict:
        """Update an existing meeting"""
        try:
            meeting_id = params.get('id')
            if not meeting_id:
                # Try to find meeting by title
                title = params.get('title')
                if title:
                    query = "SELECT id FROM meetings WHERE user_id = %s AND title LIKE %s LIMIT 1"
                    result = rds_db.execute_query(query, (self.user_id, f'%{title}%'), fetch_all=True)
                    if result:
                        meeting_id = result[0]['id']
            
            if not meeting_id:
                return {
                    'success': False,
                    'error': 'Meeting not found. Please specify which meeting to update.'
                }
            
            # Build update query
            update_fields = []
            update_values = []
            
            if 'title' in params and params['title']:
                update_fields.append('title = %s')
                update_values.append(params['title'])
            
            if 'summary' in params:
                update_fields.append('summary = %s')
                update_values.append(params['summary'])
            
            if 'status' in params and params['status']:
                update_fields.append('status = %s')
                update_values.append(params['status'])
            
            if not update_fields:
                return {
                    'success': False,
                    'error': 'No fields to update'
                }
            
            update_fields.append('updated_at = %s')
            update_values.append(datetime.utcnow())
            
            update_values.extend([meeting_id, self.user_id])
            
            query = f"""
            UPDATE meetings 
            SET {', '.join(update_fields)}
            WHERE id = %s AND user_id = %s
            """
            
            rds_db.execute_query(query, tuple(update_values))
            
            logger.info(f"Updated meeting {meeting_id}")
            
            return {
                'success': True,
                'action': 'update_meeting',
                'data': {
                    'id': meeting_id,
                    'updated_fields': list(params.keys())
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating meeting: {e}")
            return {
                'success': False,
                'error': f'Failed to update meeting: {str(e)}'
            }
    
    def _delete_meeting(self, params: Dict) -> Dict:
        """Delete a meeting"""
        try:
            meeting_id = params.get('id')
            if not meeting_id:
                # Try to find meeting by title
                title = params.get('title')
                if title:
                    query = "SELECT id FROM meetings WHERE user_id = %s AND title LIKE %s LIMIT 1"
                    result = rds_db.execute_query(query, (self.user_id, f'%{title}%'), fetch_all=True)
                    if result:
                        meeting_id = result[0]['id']
            
            if not meeting_id:
                return {
                    'success': False,
                    'error': 'Meeting not found. Please specify which meeting to delete.'
                }
            
            query = "DELETE FROM meetings WHERE id = %s AND user_id = %s"
            rds_db.execute_query(query, (meeting_id, self.user_id))
            
            logger.info(f"Deleted meeting {meeting_id}")
            
            return {
                'success': True,
                'action': 'delete_meeting',
                'data': {
                    'id': meeting_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error deleting meeting: {e}")
            return {
                'success': False,
                'error': f'Failed to delete meeting: {str(e)}'
            }
