from flask import Blueprint, request, jsonify
from middleware.validation import validate_json, add_security_headers
from services.calendar_sync import calendar_service
from config.database import db
import logging

google_calendar_bp = Blueprint('google_calendar', __name__)

logger = logging.getLogger(__name__)

@google_calendar_bp.route('/test', methods=['GET'])
@add_security_headers()
def test_calendar_access():
    """Test Google Calendar access for the authenticated user"""
    try:
        # Get user from request (you'll need to implement auth middleware)
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Get user's Google access token
        get_token_query = "SELECT google_access_token, google_refresh_token FROM users WHERE id = %s"
        token_result = db.execute_query(get_token_query, (user_id,))
        
        if not token_result or not token_result[0]['google_access_token']:
            return jsonify({
                'success': False,
                'message': 'Google Calendar not connected',
                'error': 'No access token found. Please reconnect your Google account.'
            }), 401
        
        access_token = token_result[0]['google_access_token']
        refresh_token = token_result[0].get('google_refresh_token')
        
        # Test calendar access
        test_result = calendar_service.test_calendar_access(access_token, refresh_token)
        
        return jsonify(test_result), 200 if test_result['success'] else 400
        
    except Exception as e:
        logger.error(f"Calendar access test error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Calendar access test failed: {str(e)}'
        }), 500

@google_calendar_bp.route('/sync', methods=['POST'])
@add_security_headers()
@validate_json('meeting_id', 'tasks')
def sync_tasks_to_calendar():
    """Sync multiple tasks to Google Calendar"""
    try:
        data = request.get_json()
        meeting_id = data['meeting_id']
        tasks = data['tasks']
        
        # Get meeting and user info
        meeting_query = """
        SELECT m.title, m.user_id, u.google_access_token, u.google_refresh_token
        FROM meetings m
        JOIN users u ON m.user_id = u.id
        WHERE m.id = %s
        """
        meeting_result = db.execute_query(meeting_query, (meeting_id,))
        
        if not meeting_result:
            return jsonify({'error': 'Meeting not found'}), 404
        
        meeting_data = meeting_result[0]
        meeting_title = meeting_data['title']
        access_token = meeting_data['google_access_token']
        refresh_token = meeting_data.get('google_refresh_token')
        
        if not access_token:
            return jsonify({
                'success': False,
                'error': 'Google Calendar not connected for this user'
            }), 401
        
        # Sync tasks to calendar
        sync_result = calendar_service.sync_multiple_tasks(
            tasks=tasks,
            meeting_title=meeting_title,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        return jsonify(sync_result), 200 if sync_result['success'] else 400
        
    except Exception as e:
        logger.error(f"Calendar sync error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Calendar sync failed: {str(e)}'
        }), 500

@google_calendar_bp.route('/events/<event_id>', methods=['PUT'])
@add_security_headers()
@validate_json('task', 'meeting_title')
def update_calendar_event(event_id):
    """Update a Google Calendar event"""
    try:
        data = request.get_json()
        task = data['task']
        meeting_title = data['meeting_title']
        
        # Get user from task or meeting
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Get user's Google access token
        get_token_query = "SELECT google_access_token, google_refresh_token FROM users WHERE id = %s"
        token_result = db.execute_query(get_token_query, (user_id,))
        
        if not token_result or not token_result[0]['google_access_token']:
            return jsonify({
                'success': False,
                'error': 'Google Calendar not connected'
            }), 401
        
        access_token = token_result[0]['google_access_token']
        refresh_token = token_result[0].get('google_refresh_token')
        
        # Update calendar event
        update_result = calendar_service.update_calendar_event(
            event_id=event_id,
            task=task,
            meeting_title=meeting_title,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        return jsonify(update_result), 200 if update_result['success'] else 400
        
    except Exception as e:
        logger.error(f"Calendar event update error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Event update failed: {str(e)}'
        }), 500

@google_calendar_bp.route('/events/<event_id>', methods=['DELETE'])
@add_security_headers()
def delete_calendar_event(event_id):
    """Delete a Google Calendar event"""
    try:
        # Get user from request
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Get user's Google access token
        get_token_query = "SELECT google_access_token, google_refresh_token FROM users WHERE id = %s"
        token_result = db.execute_query(get_token_query, (user_id,))
        
        if not token_result or not token_result[0]['google_access_token']:
            return jsonify({
                'success': False,
                'error': 'Google Calendar not connected'
            }), 401
        
        access_token = token_result[0]['google_access_token']
        refresh_token = token_result[0].get('google_refresh_token')
        
        # Delete calendar event
        delete_result = calendar_service.delete_calendar_event(
            event_id=event_id,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        return jsonify(delete_result), 200 if delete_result['success'] else 400
        
    except Exception as e:
        logger.error(f"Calendar event deletion error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Event deletion failed: {str(e)}'
        }), 500

@google_calendar_bp.route('/create-event', methods=['POST'])
@validate_json('credentials', 'task', 'meeting_title')
def create_calendar_event():
    """
    Create a Google Calendar event for a task (legacy endpoint)
    """
    try:
        data = request.get_json()
        credentials = data['credentials']
        task = data['task']
        meeting_title = data['meeting_title']
        
        access_token = credentials.get('access_token')
        refresh_token = credentials.get('refresh_token')
        
        result = calendar_service.create_google_calendar_event(
            task=task,
            meeting_title=meeting_title,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'event_id': result.get('event_id'),
                'event_link': result.get('event_link')
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"Google Calendar event creation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Event creation failed: {str(e)}'
        }), 500