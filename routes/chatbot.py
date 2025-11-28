"""
Chatbot API Routes
==================
REST API endpoints for chatbot interactions
"""

from flask import Blueprint, request, jsonify, Response, stream_with_context
from middleware.auth import require_auth
from middleware.simple_auth import require_firebase_auth
from chatbot.service import ChatbotService
from chatbot.voice import get_voice_service
from utils.error_handling import (
    log_request_error, log_cors_error, create_error_response, 
    create_success_response, get_user_friendly_message
)
import logging

logger = logging.getLogger(__name__)

chatbot_bp = Blueprint('chatbot', __name__)


@chatbot_bp.route('/message', methods=['POST'])
@require_firebase_auth
def send_message():
    """
    Send message to chatbot
    
    Request body:
        - message: str (required)
        - session_id: str (optional)
        - stream: bool (optional, default: false)
    
    Returns:
        - response: str
        - session_id: str
        - sources: list
    """
    try:
        current_user = request.current_user
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        message = data['message']
        session_id = data.get('session_id')
        stream = data.get('stream', False)
        
        # Initialize chatbot service
        chatbot_service = ChatbotService(current_user['id'])
        
        # Process message
        if stream:
            # Streaming response using Server-Sent Events
            result = chatbot_service.process_message(message, session_id, stream=True)
            
            def generate():
                # Send session_id and sources first
                yield f"data: {jsonify({'session_id': result['session_id'], 'sources': result['sources']}).get_data(as_text=True)}\n\n"
                
                # Stream response chunks
                for chunk in result['stream']:
                    yield f"data: {jsonify({'chunk': chunk}).get_data(as_text=True)}\n\n"
                
                # Send completion signal
                yield f"data: {jsonify({'done': True}).get_data(as_text=True)}\n\n"
            
            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            # Regular response
            result = chatbot_service.process_message(message, session_id, stream=False)
            
            return jsonify({
                'success': True,
                'response': result['response'],
                'session_id': result['session_id'],
                'sources': result['sources']
            }), 200
        
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to process message',
            'message': str(e)
        }), 500


@chatbot_bp.route('/voice', methods=['POST', 'OPTIONS'])
@require_firebase_auth
def send_voice_message():
    """
    Send voice message to chatbot
    
    Request (multipart/form-data):
        - audio: file (required)
        - session_id: str (optional)
        - include_audio_response: bool (optional, default: false)
    
    Returns:
        - transcription: str
        - response: str
        - session_id: str
        - sources: list
        - audio_response: str (base64, optional)
    """
    # Handle preflight requests
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,Accept,Origin')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
    
    try:
        current_user = request.current_user
        # Validate request content type
        if not request.content_type or not request.content_type.startswith('multipart/form-data'):
            log_cors_error(
                request.headers.get('Origin', 'Unknown'),
                request.method,
                '/api/chatbot/voice'
            )
            return jsonify(create_error_response(
                get_user_friendly_message('INVALID_REQUEST'),
                'INVALID_REQUEST',
                400
            )), 400
        
        # Check if audio file is present
        if 'audio' not in request.files:
            return jsonify(create_error_response(
                'Audio file is required. Please include an "audio" field in your form data.',
                'VOICE_FILE_INVALID',
                400
            )), 400
        
        audio_file = request.files['audio']
        
        if not audio_file or audio_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No audio file selected. Please choose a valid audio file.'
            }), 400
        
        # Validate file size before reading
        audio_file.seek(0, 2)  # Seek to end
        file_size = audio_file.tell()
        audio_file.seek(0)  # Reset to beginning
        
        max_size = 25 * 1024 * 1024  # 25MB
        if file_size > max_size:
            return jsonify(create_error_response(
                get_user_friendly_message('VOICE_FILE_TOO_LARGE'),
                'VOICE_FILE_TOO_LARGE',
                400
            )), 400
        
        if file_size == 0:
            return jsonify({
                'success': False,
                'error': 'Audio file is empty. Please select a valid audio file.'
            }), 400
        
        # Get optional parameters
        session_id = request.form.get('session_id')
        include_audio_response = request.form.get('include_audio_response', 'false').lower() == 'true'
        
        # Read audio file
        audio_bytes = audio_file.read()
        filename = audio_file.filename or 'audio.wav'
        
        # Initialize services
        try:
            voice_service = get_voice_service()
            chatbot_service = ChatbotService(current_user['id'])
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            return jsonify({
                'success': False,
                'error': 'Voice service is currently unavailable. Please try again later.'
            }), 503
        
        # Check service status
        service_status = voice_service.get_service_status()
        if not service_status['transcription_enabled']:
            return jsonify(create_error_response(
                get_user_friendly_message('VOICE_SERVICE_UNAVAILABLE'),
                'VOICE_SERVICE_UNAVAILABLE',
                503
            )), 503
        
        # Process voice message
        result = voice_service.process_voice_message(
            audio_file=audio_bytes,
            filename=filename,
            chatbot_service=chatbot_service,
            user_id=current_user['id'],
            session_id=session_id,
            include_audio_response=include_audio_response
        )
        
        return jsonify(create_success_response(result)), 200
        
    except ValueError as e:
        log_request_error(e, '/api/chatbot/voice', current_user.get('id'))
        return jsonify(create_error_response(
            str(e),
            'VOICE_TRANSCRIPTION_FAILED',
            400
        )), 400
    except Exception as e:
        log_request_error(e, '/api/chatbot/voice', current_user.get('id'))
        return jsonify(create_error_response(
            get_user_friendly_message('VOICE_SERVICE_UNAVAILABLE'),
            'VOICE_SERVICE_UNAVAILABLE',
            500,
            include_details=logger.level <= logging.DEBUG,
            details={'error': str(e)} if logger.level <= logging.DEBUG else None
        )), 500


@chatbot_bp.route('/history', methods=['GET'])
@require_firebase_auth
def get_history():
    """
    Get conversation history
    
    Query params:
        - session_id: str (required)
        - limit: int (optional, default: 50)
    
    Returns:
        - messages: list
        - session_id: str
    """
    try:
        current_user = request.current_user
        session_id = request.args.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400
        
        limit = int(request.args.get('limit', 50))
        
        # Initialize chatbot service
        chatbot_service = ChatbotService(current_user['id'])
        
        # Get history
        result = chatbot_service.get_conversation_history(session_id, limit)
        
        return jsonify({
            'success': True,
            **result
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_history: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get conversation history',
            'message': str(e)
        }), 500


@chatbot_bp.route('/history', methods=['DELETE'])
@require_firebase_auth
def clear_history():
    """
    Clear conversation history
    
    Request body:
        - session_id: str (optional)
    
    Returns:
        - success: bool
    """
    try:
        current_user = request.current_user
        data = request.get_json() or {}
        session_id = data.get('session_id')
        
        # Initialize chatbot service
        chatbot_service = ChatbotService(current_user['id'])
        
        # Clear history
        result = chatbot_service.clear_conversation(session_id)
        
        return jsonify({
            'success': True,
            'message': 'Conversation history cleared'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in clear_history: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear conversation history',
            'message': str(e)
        }), 500


@chatbot_bp.route('/sessions', methods=['GET'])
@require_firebase_auth
def get_sessions():
    """
    Get user's conversation sessions
    
    Query params:
        - limit: int (optional, default: 10)
    
    Returns:
        - sessions: list (empty list if no sessions or table doesn't exist)
    """
    try:
        # Get current user from request context (set by auth middleware)
        current_user = request.current_user
        limit = int(request.args.get('limit', 10))
        
        logger.info(f"Getting sessions for user {current_user['id']}, limit={limit}")
        
        # Initialize chatbot service
        chatbot_service = ChatbotService(current_user['id'])
        
        # Get sessions (returns empty list if none exist)
        result = chatbot_service.get_sessions(limit)
        
        return jsonify({
            'success': True,
            **result
        }), 200
        
    except Exception as e:
        # Even on error, return empty sessions list with 200 status
        # This prevents frontend errors for new users
        logger.error(f"Error in get_sessions (returning empty list): {e}", exc_info=True)
        return jsonify({
            'success': True,
            'sessions': []
        }), 200


@chatbot_bp.route('/voice/status', methods=['GET'])
@require_firebase_auth
def get_voice_status():
    """
    Get voice service status and capabilities
    
    Returns:
        - transcription_enabled: bool
        - tts_enabled: bool
        - max_audio_size_mb: int
        - initialization_errors: list
    """
    try:
        current_user = request.current_user
        voice_service = get_voice_service()
        status = voice_service.get_service_status()
        
        return jsonify({
            'success': True,
            **status
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_voice_status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get voice service status',
            'message': str(e)
        }), 500


@chatbot_bp.route('/index', methods=['POST'])
@require_firebase_auth
def index_user_data():
    """
    Index user data into vector store
    
    Returns:
        - success: bool
        - message: str
    """
    try:
        current_user = request.current_user
        # Initialize chatbot service
        chatbot_service = ChatbotService(current_user['id'])
        
        # Index data
        result = chatbot_service.index_user_data()
        
        return jsonify({
            'success': True,
            **result
        }), 200
        
    except Exception as e:
        logger.error(f"Error in index_user_data: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to index user data',
            'message': str(e)
        }), 500


@chatbot_bp.route('/suggestions', methods=['GET'])
@require_firebase_auth
def get_suggestions():
    """
    Get smart suggestions based on user's current context
    
    Returns:
        - success: bool
        - suggestions: list
    """
    try:
        current_user = request.current_user
        logger.info(f"Getting suggestions for user {current_user['id']}")
        
        # Initialize chatbot service
        chatbot_service = ChatbotService(current_user['id'])
        
        # Get suggestions
        result = chatbot_service.get_smart_suggestions()
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_suggestions: {e}", exc_info=True)
        return jsonify({
            'success': True,
            'suggestions': []
        }), 200  # Return 200 with empty suggestions on error
