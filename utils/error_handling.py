"""
Simple Error Handling Utilities
================================
Provides basic error handling and logging for the chatbot system
"""

import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request

logger = logging.getLogger(__name__)


def log_request_error(error: Exception, endpoint: str, user_id: Optional[str] = None) -> None:
    """
    Log request error with context
    
    Args:
        error: Exception that occurred
        endpoint: API endpoint where error occurred
        user_id: Optional user ID
    """
    try:
        error_context = {
            'timestamp': datetime.utcnow().isoformat(),
            'endpoint': endpoint,
            'user_id': user_id,
            'method': request.method if request else 'Unknown',
            'url': request.url if request else 'Unknown',
            'origin': request.headers.get('Origin') if request else 'Unknown',
            'user_agent': request.headers.get('User-Agent') if request else 'Unknown',
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
        
        logger.error(f"Request error in {endpoint}: {error_context}")
        
        # Log stack trace for debugging
        if logger.level <= logging.DEBUG:
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            
    except Exception as e:
        logger.error(f"Failed to log request error: {e}")


def log_cors_error(origin: str, method: str, endpoint: str) -> None:
    """
    Log CORS-related error
    
    Args:
        origin: Request origin
        method: HTTP method
        endpoint: API endpoint
    """
    try:
        cors_context = {
            'timestamp': datetime.utcnow().isoformat(),
            'origin': origin,
            'method': method,
            'endpoint': endpoint,
            'headers': dict(request.headers) if request else {}
        }
        
        logger.warning(f"CORS issue detected: {cors_context}")
        
    except Exception as e:
        logger.error(f"Failed to log CORS error: {e}")


def create_error_response(
    error_message: str,
    error_code: str = "GENERAL_ERROR",
    status_code: int = 500,
    include_details: bool = False,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create standardized error response
    
    Args:
        error_message: User-friendly error message
        error_code: Machine-readable error code
        status_code: HTTP status code
        include_details: Whether to include debug details
        details: Optional additional details
        
    Returns:
        Standardized error response dict
    """
    response = {
        'success': False,
        'error': error_message,
        'error_code': error_code,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if include_details and details:
        response['details'] = details
    
    return response


def create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized success response
    
    Args:
        data: Response data
        
    Returns:
        Standardized success response dict
    """
    response = {
        'success': True,
        'timestamp': datetime.utcnow().isoformat(),
        **data
    }
    
    return response


# Common error messages
ERROR_MESSAGES = {
    'VOICE_TRANSCRIPTION_FAILED': 'Failed to transcribe audio. Please try again with a clearer recording.',
    'VOICE_TTS_FAILED': 'Failed to generate audio response. Text response is still available.',
    'VOICE_FILE_TOO_LARGE': 'Audio file is too large. Please use a smaller file.',
    'VOICE_FILE_INVALID': 'Invalid audio file format. Please use a supported audio format.',
    'VOICE_SERVICE_UNAVAILABLE': 'Voice service is currently unavailable. Please try again later.',
    'CHATBOT_RESPONSE_FAILED': 'Failed to generate response. Please try again.',
    'CHATBOT_SERVICE_UNAVAILABLE': 'Chatbot service is currently unavailable. Please try again later.',
    'INVALID_REQUEST': 'Invalid request format. Please check your request and try again.',
    'AUTHENTICATION_REQUIRED': 'Authentication is required to access this endpoint.',
    'CORS_ERROR': 'Cross-origin request not allowed from this domain.'
}


def get_user_friendly_message(error_code: str) -> str:
    """
    Get user-friendly error message for error code
    
    Args:
        error_code: Error code
        
    Returns:
        User-friendly error message
    """
    return ERROR_MESSAGES.get(error_code, 'An unexpected error occurred. Please try again.')