"""
Rate Limiting Middleware for AI Meeting Assistant Backend
Provides comprehensive rate limiting for different endpoints
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request
import os

def get_user_id():
    """Get user ID from request for rate limiting"""
    # Try to get user ID from various sources
    user_id = (
        request.form.get('user_id') or
        request.args.get('user_id') or
        request.json.get('firebase_uid') if request.is_json else None or
        get_remote_address()
    )
    return user_id

# Initialize rate limiter
limiter = Limiter(
    key_func=get_user_id,
    default_limits=[
        "1000 per hour",  # Default rate limit
        "100 per minute"
    ],
    storage_uri=os.getenv('REDIS_URL', 'memory://'),  # Use Redis if available, fallback to memory
    strategy="fixed-window"
)

# Rate limiting configurations for different endpoints
RATE_LIMITS = {
    # Authentication endpoints
    'auth_verify': "10 per minute",
    'auth_update': "20 per hour",
    'auth_delete': "5 per hour",
    
    # File upload endpoints (more restrictive)
    'upload_audio': "5 per minute",
    'upload_status': "30 per minute",
    
    # Data retrieval endpoints
    'meetings_list': "60 per minute",
    'meeting_detail': "100 per minute",
    'tasks_list': "60 per minute",
    'task_update': "30 per minute",
    
    # Health check endpoints (less restrictive)
    'health_check': "120 per minute",
    'health_detailed': "30 per minute"
}

def get_rate_limit(endpoint_name: str) -> str:
    """Get rate limit for specific endpoint"""
    return RATE_LIMITS.get(endpoint_name, "100 per minute")

# Custom rate limit decorators
def rate_limit_auth():
    """Rate limit for authentication endpoints"""
    return limiter.limit(get_rate_limit('auth_verify'))

def rate_limit_upload():
    """Rate limit for upload endpoints"""
    return limiter.limit(get_rate_limit('upload_audio'))

def rate_limit_data():
    """Rate limit for data endpoints"""
    return limiter.limit(get_rate_limit('meetings_list'))

def rate_limit_health():
    """Rate limit for health endpoints"""
    return limiter.limit(get_rate_limit('health_check'))

def rate_limit_strict():
    """Strict rate limit for sensitive operations"""
    return limiter.limit("5 per minute")

def rate_limit_moderate():
    """Moderate rate limit for regular operations"""
    return limiter.limit("30 per minute")

def rate_limit_lenient():
    """Lenient rate limit for read operations"""
    return limiter.limit("100 per minute")
