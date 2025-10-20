"""
CORS Configuration Validator and Helper Utilities

This module provides utilities for validating and debugging CORS configuration
in the AI Meeting Assistant backend.
"""

import os
import re
from typing import List, Dict, Any
from urllib.parse import urlparse


class CORSValidator:
    """Validates and manages CORS configuration for security and functionality."""
    
    def __init__(self):
        self.flask_env = os.getenv('FLASK_ENV', 'development')
        self.cors_origins = os.getenv('CORS_ORIGINS', '')
    
    def validate_origins(self) -> Dict[str, Any]:
        """
        Validate CORS origins configuration and return validation results.
        
        Returns:
            Dict containing validation results and recommendations
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'recommendations': [],
            'parsed_origins': [],
            'environment': self.flask_env
        }
        
        # Parse origins from environment variable
        if self.cors_origins:
            origins = [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]
            results['parsed_origins'] = origins
        else:
            origins = []
        
        # Production environment validation
        if self.flask_env == 'production':
            if not origins:
                results['valid'] = False
                results['errors'].append("CORS_ORIGINS must be set in production environment")
            elif '*' in origins:
                results['valid'] = False
                results['errors'].append("Wildcard (*) not allowed in production CORS_ORIGINS")
            else:
                # Validate each origin
                for origin in origins:
                    if not self._is_valid_origin(origin):
                        results['valid'] = False
                        results['errors'].append(f"Invalid origin format: {origin}")
                    elif not origin.startswith('https://'):
                        results['warnings'].append(f"Non-HTTPS origin in production: {origin}")
        
        # Development environment validation
        elif self.flask_env == 'development':
            if not origins:
                results['warnings'].append("No CORS_ORIGINS set - localhost will be allowed automatically")
            elif '*' in origins:
                results['warnings'].append("Wildcard (*) in development - consider using specific origins")
        
        # Security recommendations
        if origins:
            results['recommendations'].extend([
                "Use HTTPS origins in production",
                "Avoid trailing slashes in origin URLs",
                "Include both www and non-www versions if needed",
                "Test CORS configuration with your frontend domains"
            ])
        
        return results
    
    def _is_valid_origin(self, origin: str) -> bool:
        """Validate if an origin URL is properly formatted."""
        try:
            parsed = urlparse(origin)
            return (
                parsed.scheme in ['http', 'https'] and
                parsed.netloc and
                not parsed.path and  # No path in origin
                not parsed.query and  # No query in origin
                not parsed.fragment  # No fragment in origin
            )
        except Exception:
            return False
    
    def get_allowed_origins(self) -> List[str]:
        """Get the list of allowed origins based on environment."""
        origins = []
        
        if self.cors_origins:
            origins = [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]
        
        # Add development origins in development mode
        if self.flask_env == 'development':
            dev_origins = [
                'http://localhost:3000',
                'http://localhost:5173',
                'http://localhost:8080',
                'http://127.0.0.1:3000',
                'http://127.0.0.1:5173',
                'http://127.0.0.1:8080'
            ]
            origins.extend(dev_origins)
            origins = list(set(origins))  # Remove duplicates
        
        return origins
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Check if a specific origin is allowed."""
        allowed_origins = self.get_allowed_origins()
        
        # Direct match
        if origin in allowed_origins:
            return True
        
        # Development localhost check
        if self.flask_env == 'development' and origin and (
            origin.startswith('http://localhost:') or
            origin.startswith('http://127.0.0.1:') or
            origin.startswith('https://localhost:') or
            origin.startswith('https://127.0.0.1:')
        ):
            return True
        
        return False
    
    def get_cors_headers(self, origin: str) -> Dict[str, str]:
        """Get appropriate CORS headers for a given origin."""
        headers = {
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS,PATCH',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Requested-With,Accept,Origin,X-API-Key,X-CSRFToken',
            'Access-Control-Allow-Credentials': 'false',
            'Access-Control-Max-Age': '86400',
            'Vary': 'Origin'
        }
        
        if self.is_origin_allowed(origin):
            headers['Access-Control-Allow-Origin'] = origin
        elif self.flask_env == 'development' and not self.cors_origins:
            headers['Access-Control-Allow-Origin'] = origin or '*'
        else:
            allowed_origins = self.get_allowed_origins()
            headers['Access-Control-Allow-Origin'] = allowed_origins[0] if allowed_origins else 'null'
        
        return headers


def validate_cors_config() -> Dict[str, Any]:
    """
    Convenience function to validate CORS configuration.
    
    Returns:
        Dict containing validation results
    """
    validator = CORSValidator()
    return validator.validate_origins()


def get_cors_debug_info() -> Dict[str, Any]:
    """
    Get comprehensive CORS debugging information.
    
    Returns:
        Dict containing CORS configuration details
    """
    validator = CORSValidator()
    
    return {
        'environment': validator.flask_env,
        'cors_origins_env': validator.cors_origins,
        'allowed_origins': validator.get_allowed_origins(),
        'validation': validator.validate_origins(),
        'security_level': 'high' if validator.flask_env == 'production' else 'low'
    }
