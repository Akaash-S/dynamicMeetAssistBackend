"""
CORS Debug and Configuration Endpoint

This module provides debugging endpoints for CORS configuration.
Only available in development environment for security.
"""

from flask import Blueprint, request, jsonify
import os
from utils.cors_validator import get_cors_debug_info, validate_cors_config

cors_debug_bp = Blueprint('cors_debug', __name__)


@cors_debug_bp.route('/api/cors/debug', methods=['GET'])
def cors_debug():
    """
    Debug endpoint for CORS configuration.
    Only available in development environment.
    """
    # Security: Only allow in development
    if os.getenv('FLASK_ENV') != 'development':
        return jsonify({'error': 'CORS debug endpoint only available in development'}), 403
    
    try:
        debug_info = get_cors_debug_info()
        return jsonify(debug_info), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get CORS debug info: {str(e)}'}), 500


@cors_debug_bp.route('/api/cors/validate', methods=['GET'])
def cors_validate():
    """
    Validate CORS configuration.
    Only available in development environment.
    """
    # Security: Only allow in development
    if os.getenv('FLASK_ENV') != 'development':
        return jsonify({'error': 'CORS validation endpoint only available in development'}), 403
    
    try:
        validation_results = validate_cors_config()
        return jsonify(validation_results), 200
    except Exception as e:
        return jsonify({'error': f'Failed to validate CORS config: {str(e)}'}), 500


@cors_debug_bp.route('/api/cors/test', methods=['GET', 'POST', 'OPTIONS'])
def cors_test():
    """
    Test CORS configuration with current request.
    Only available in development environment.
    """
    # Security: Only allow in development
    if os.getenv('FLASK_ENV') != 'development':
        return jsonify({'error': 'CORS test endpoint only available in development'}), 403
    
    try:
        origin = request.headers.get('Origin')
        method = request.method
        
        from utils.cors_validator import CORSValidator
        validator = CORSValidator()
        
        test_results = {
            'request_origin': origin,
            'request_method': method,
            'is_origin_allowed': validator.is_origin_allowed(origin) if origin else False,
            'allowed_origins': validator.get_allowed_origins(),
            'cors_headers': validator.get_cors_headers(origin) if origin else {},
            'environment': validator.flask_env,
            'validation_status': 'valid' if validator.validate_origins()['valid'] else 'invalid'
        }
        
        return jsonify(test_results), 200
    except Exception as e:
        return jsonify({'error': f'Failed to test CORS: {str(e)}'}), 500
