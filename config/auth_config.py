"""
Authentication Configuration for Unified Backend
JWT token management and security utilities for both client and admin apps
"""

import jwt
import hashlib
import secrets
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Removed decorators to prevent circular imports - moved to middleware/validation.py

class AuthConfig:
    """Authentication configuration and utilities"""
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
    
    # Password Configuration
    PASSWORD_HASH_ITERATIONS = 100000
    PASSWORD_MIN_LENGTH = 6
    
    # Session Configuration
    SESSION_TIMEOUT_HOURS = int(os.getenv('SESSION_TIMEOUT_HOURS', '24'))
    
    # Admin Configuration
    DEFAULT_ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@dynamicmeetingassistant.com').lower()
    DEFAULT_ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
    DEFAULT_ADMIN_NAME = os.getenv('ADMIN_NAME', 'System Administrator')
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password with salt using PBKDF2
        
        Args:
            password (str): Plain text password
            
        Returns:
            str: Hashed password in format "salt:hash"
        """
        salt = secrets.token_hex(32)  # 64 character salt
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            AuthConfig.PASSWORD_HASH_ITERATIONS
        )
        return f"{salt}:{password_hash.hex()}"
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify password against hash
        
        Args:
            password (str): Plain text password
            hashed_password (str): Hashed password from database
            
        Returns:
            bool: True if password matches
        """
        try:
            salt, stored_hash = hashed_password.split(':', 1)
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                AuthConfig.PASSWORD_HASH_ITERATIONS
            )
            return secrets.compare_digest(password_hash.hex(), stored_hash)
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def generate_jwt_token(user_data: Dict[str, Any]) -> str:
        """
        Generate JWT token for user
        
        Args:
            user_data (dict): User information to encode in token
            
        Returns:
            str: JWT token
        """
        payload = {
            'user_id': str(user_data['id']),
            'email': user_data['email'],
            'role': user_data.get('role', 'user'),
            'name': user_data.get('name', ''),
            'auth_provider': user_data.get('auth_provider', 'firebase'),
            'exp': datetime.utcnow() + timedelta(hours=AuthConfig.JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow(),
            'iss': 'dynamic-meeting-assistant',  # Issuer
            'aud': 'dynamic-meeting-assistant'   # Audience
        }
        
        return jwt.encode(payload, AuthConfig.JWT_SECRET_KEY, algorithm=AuthConfig.JWT_ALGORITHM)
    
    @staticmethod
    def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token and return payload
        
        Args:
            token (str): JWT token to verify
            
        Returns:
            dict or None: Token payload if valid, None if invalid
        """
        try:
            payload = jwt.decode(
                token, 
                AuthConfig.JWT_SECRET_KEY, 
                algorithms=[AuthConfig.JWT_ALGORITHM],
                audience='dynamic-meeting-assistant',
                issuer='dynamic-meeting-assistant'
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT token verification error: {e}")
            return None
    
    @staticmethod
    def generate_session_id() -> str:
        """Generate secure session ID"""
        return secrets.token_hex(32)
    
    @staticmethod
    def is_default_admin(email: str, password: str) -> bool:
        """
        Check if credentials match default admin
        
        Args:
            email (str): Email to check
            password (str): Password to check
            
        Returns:
            bool: True if matches default admin credentials
        """
        return (
            email.lower() == AuthConfig.DEFAULT_ADMIN_EMAIL and 
            password == AuthConfig.DEFAULT_ADMIN_PASSWORD
        )
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        Validate password strength
        
        Args:
            password (str): Password to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if len(password) < AuthConfig.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {AuthConfig.PASSWORD_MIN_LENGTH} characters long"
        
        # For admin accounts, require stronger passwords
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not (has_upper and has_lower and has_digit and has_special):
            return False, "Password must contain uppercase, lowercase, digit, and special character"
        
        return True, ""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get security headers for responses"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }

# Session storage (use Redis in production)
class SessionManager:
    """In-memory session manager (use Redis in production)"""
    
    def __init__(self):
        self._sessions = {}
    
    def create_session(self, user_data: Dict[str, Any]) -> str:
        """Create new session"""
        session_id = AuthConfig.generate_session_id()
        self._sessions[session_id] = {
            'user_id': str(user_data['id']),
            'email': user_data['email'],
            'role': user_data.get('role', 'user'),
            'name': user_data.get('name', ''),
            'auth_provider': user_data.get('auth_provider', 'firebase'),
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(hours=AuthConfig.SESSION_TIMEOUT_HOURS),
            'last_activity': datetime.utcnow()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        # Check if session has expired
        if datetime.utcnow() > session['expires_at']:
            self.delete_session(session_id)
            return None
        
        # Update last activity
        session['last_activity'] = datetime.utcnow()
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        return self._sessions.pop(session_id, None) is not None
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self._sessions.items()
            if now > session['expires_at']
        ]
        for session_id in expired_sessions:
            del self._sessions[session_id]
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

# Global session manager instance
session_manager = SessionManager()