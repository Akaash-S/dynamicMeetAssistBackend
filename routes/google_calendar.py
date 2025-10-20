from flask import Blueprint, request, jsonify
from middleware.validation import validate_json
from services.calendar_sync import calendar_service
import logging

# Create blueprint for Google Calendar routes
google_calendar_bp = Blueprint('google_calendar', __name__)

logger = logging.getLogger(__name__)

@google_calendar_bp.route('/integrate', methods=['POST'])
@validate_json('access_token')
def integrate_google_calendar():
    """
    Integrate with Google Calendar using OAuth2 access token
    """
    try:
        data = request.get_json()
        access_token = data['access_token']
        
        # Test the integration
        result = calendar_service.integrate_google_calendar({
            'access_token': access_token
        })
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Google Calendar integration successful',
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"Google Calendar integration error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Integration failed: {str(e)}'
        }), 500

@google_calendar_bp.route('/create-event', methods=['POST'])
@validate_json('access_token', 'task', 'meeting_title')
def create_calendar_event():
    """
    Create a Google Calendar event for a task
    """
    try:
        data = request.get_json()
        access_token = data['access_token']
        task = data['task']
        meeting_title = data['meeting_title']
        
        # Create the calendar event
        result = calendar_service.create_google_calendar_event(
            task=task,
            meeting_title=meeting_title,
            access_token=access_token
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

@google_calendar_bp.route('/health', methods=['GET'])
def google_calendar_health():
    """
    Check Google Calendar service health
    """
    try:
        health_status = calendar_service.get_calendar_health()
        return jsonify({
            'success': True,
            'service': 'google_calendar',
            'status': 'healthy',
            'data': health_status
        })
    except Exception as e:
        logger.error(f"Google Calendar health check error: {str(e)}")
        return jsonify({
            'success': False,
            'service': 'google_calendar',
            'status': 'unhealthy',
            'error': str(e)
        }), 500
