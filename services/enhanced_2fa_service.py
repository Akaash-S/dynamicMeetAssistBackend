"""
Enhanced 2FA Service
====================
Handles Two-Factor Authentication with smart session tracking:
- Requires 2FA on manual logout/login
- Skips 2FA for active sessions
- Requires 2FA for sensitive operations (data deletion)
"""

import pyotp
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging
from config.aws_rds_database import rds_db

logger = logging.getLogger(__name__)


class Enhanced2FAService:
    """Enhanced 2FA service with session tracking"""
    
    # Session types
    SESSION_ACTIVE = 'active'  # User is logged in, no 2FA needed
    SESSION_LOGGED_OUT = 'logged_out'  # User manually logged out, needs 2FA
    SESSION_EXPIRED = 'expired'  # Session expired, needs 2FA
    
    # Operation types that require 2FA
    SENSITIVE_OPERATIONS = [
        'delete_meeting',
        'delete_task',
        'delete_account',
        'change_password',
        'disable_2fa',
        'export_data'
    ]
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> List[str]:
        """Generate backup codes for 2FA"""
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()  # 8-character hex code
            codes.append(code)
        return codes
    
    @staticmethod
    def hash_backup_code(code: str) -> str:
        """Hash a backup code for storage"""
        return hashlib.sha256(code.encode()).hexdigest()
    
    @staticmethod
    def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
        """
        Verify TOTP code
        
        Args:
            secret: User's TOTP secret
            code: 6-digit code from authenticator app
            window: Time window for code validity (default 1 = ±30 seconds)
            
        Returns:
            True if code is valid
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=window)
        except Exception as e:
            logger.error(f"Error verifying TOTP code: {e}")
            return False
    
    @staticmethod
    def verify_backup_code(user_id: str, code: str) -> bool:
        """
        Verify and consume a backup code
        
        Args:
            user_id: User ID
            code: Backup code to verify
            
        Returns:
            True if code is valid and not used
        """
        try:
            # Get user's backup codes
            query = "SELECT backup_codes FROM users WHERE id = %s"
            result = rds_db.execute_query(query, (user_id,), fetch_one=True)
            
            if not result or not result.get('backup_codes'):
                return False
            
            import json
            backup_codes = json.loads(result['backup_codes'])
            code_hash = Enhanced2FAService.hash_backup_code(code)
            
            # Check if code exists and is not used
            for bc in backup_codes:
                if bc['hash'] == code_hash and not bc.get('used', False):
                    # Mark code as used
                    bc['used'] = True
                    bc['used_at'] = datetime.utcnow().isoformat()
                    
                    # Update database
                    update_query = "UPDATE users SET backup_codes = %s WHERE id = %s"
                    rds_db.execute_query(update_query, (json.dumps(backup_codes), user_id))
                    
                    logger.info(f"Backup code used for user: {user_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying backup code: {e}")
            return False
    
    @staticmethod
    def enable_2fa(user_id: str, secret: str, method: str = 'totp') -> Tuple[bool, Optional[List[str]]]:
        """
        Enable 2FA for a user
        
        Args:
            user_id: User ID
            secret: TOTP secret
            method: 2FA method (totp, sms, email)
            
        Returns:
            Tuple of (success, backup_codes)
        """
        try:
            # Generate backup codes
            backup_codes = Enhanced2FAService.generate_backup_codes()
            
            # Store hashed backup codes
            import json
            backup_codes_data = [
                {
                    'hash': Enhanced2FAService.hash_backup_code(code),
                    'used': False
                }
                for code in backup_codes
            ]
            
            # Update user record
            query = """
            UPDATE users 
            SET two_factor_enabled = true,
                two_factor_method = %s,
                two_factor_secret = %s,
                backup_codes = %s,
                updated_at = %s
            WHERE id = %s
            """
            
            rds_db.execute_query(query, (
                method,
                secret,
                json.dumps(backup_codes_data),
                datetime.utcnow(),
                user_id
            ))
            
            logger.info(f"2FA enabled for user: {user_id}")
            return True, backup_codes
            
        except Exception as e:
            logger.error(f"Error enabling 2FA: {e}")
            return False, None
    
    @staticmethod
    def disable_2fa(user_id: str) -> bool:
        """Disable 2FA for a user"""
        try:
            query = """
            UPDATE users 
            SET two_factor_enabled = false,
                two_factor_method = NULL,
                two_factor_secret = NULL,
                backup_codes = NULL,
                updated_at = %s
            WHERE id = %s
            """
            
            rds_db.execute_query(query, (datetime.utcnow(), user_id))
            logger.info(f"2FA disabled for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error disabling 2FA: {e}")
            return False
    
    @staticmethod
    def is_2fa_enabled(user_id: str) -> bool:
        """Check if 2FA is enabled for a user"""
        try:
            query = "SELECT two_factor_enabled FROM users WHERE id = %s"
            result = rds_db.execute_query(query, (user_id,), fetch_one=True)
            return result and result.get('two_factor_enabled', False)
        except Exception as e:
            logger.error(f"Error checking 2FA status: {e}")
            return False
    
    @staticmethod
    def get_2fa_secret(user_id: str) -> Optional[str]:
        """Get user's 2FA secret"""
        try:
            query = "SELECT two_factor_secret FROM users WHERE id = %s"
            result = rds_db.execute_query(query, (user_id,), fetch_one=True)
            return result.get('two_factor_secret') if result else None
        except Exception as e:
            logger.error(f"Error getting 2FA secret: {e}")
            return None
    
    @staticmethod
    def expire_inactive_sessions(user_id: str):
        """
        Expire sessions that have been inactive for more than 10 minutes
        """
        try:
            from datetime import datetime, timedelta
            
            # Find active sessions older than 10 minutes
            query = """
            UPDATE user_sessions 
            SET session_type = %s, logged_out_at = %s
            WHERE user_id = %s 
            AND session_type = %s
            AND created_at < %s
            """
            
            inactive_threshold = datetime.now() - timedelta(minutes=10)
            
            rds_db.execute_query(query, (
                Enhanced2FAService.SESSION_EXPIRED,
                datetime.now(),
                user_id,
                Enhanced2FAService.SESSION_ACTIVE,
                inactive_threshold
            ))
            
            logger.info(f"Expired inactive sessions for user: {user_id}")
            
        except Exception as e:
            logger.error(f"Error expiring inactive sessions: {e}")
    
    @staticmethod
    def track_logout(user_id: str, session_id: str):
        """
        Track manual logout to require 2FA on next login
        
        Args:
            user_id: User ID
            session_id: Session ID being logged out
        """
        try:
            # Store logout event
            query = """
            INSERT INTO user_sessions (
                id, user_id, session_type, logged_out_at, created_at
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE 
            SET session_type = %s, logged_out_at = %s
            """
            
            now = datetime.utcnow()
            rds_db.execute_query(query, (
                session_id,
                user_id,
                Enhanced2FAService.SESSION_LOGGED_OUT,
                now,
                now,
                Enhanced2FAService.SESSION_LOGGED_OUT,
                now
            ))
            
            logger.info(f"Logout tracked for user: {user_id}")
            
        except Exception as e:
            logger.error(f"Error tracking logout: {e}")
    
    @staticmethod
    def should_require_2fa_on_login(user_id: str) -> bool:
        """
        Check if 2FA should be required on login
        
        Returns True if:
        - User has 2FA enabled AND
        - (User manually logged out OR session inactive for 10+ minutes)
        """
        try:
            # Check if 2FA is enabled
            if not Enhanced2FAService.is_2fa_enabled(user_id):
                logger.info(f"2FA not enabled for user {user_id}")
                return False
            
            # Check if there's an active session
            query = """
            SELECT session_type, session_id, created_at, logged_out_at
            FROM user_sessions 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
            """
            
            result = rds_db.execute_query(query, (user_id,), fetch_one=True)
            
            if not result:
                # No previous session, require 2FA
                logger.info(f"No session found for user {user_id}, requiring 2FA")
                return True
            
            session_type = result.get('session_type')
            created_at = result.get('created_at')
            
            # Case 1: User manually logged out - ALWAYS require 2FA
            if session_type == Enhanced2FAService.SESSION_LOGGED_OUT:
                logger.info(f"User {user_id} manually logged out, requiring 2FA")
                return True
            
            # Case 2: Session expired - ALWAYS require 2FA
            if session_type == Enhanced2FAService.SESSION_EXPIRED:
                logger.info(f"Session expired for user {user_id}, requiring 2FA")
                return True
            
            # Case 3: Active session - check if it's been inactive for 10+ minutes
            if session_type == Enhanced2FAService.SESSION_ACTIVE:
                from datetime import datetime, timedelta
                
                if isinstance(created_at, datetime):
                    time_since_creation = datetime.now() - created_at
                    inactive_threshold = timedelta(minutes=10)
                    
                    if time_since_creation >= inactive_threshold:
                        # Session inactive for 10+ minutes, require 2FA
                        logger.info(f"Active session for user {user_id} inactive for {time_since_creation.total_seconds()/60:.1f} minutes (>10 min), requiring 2FA")
                        return True
                    else:
                        # Session still active and within 10 minutes
                        logger.info(f"Active session for user {user_id} created {time_since_creation.total_seconds()/60:.1f} minutes ago (<10 min), not requiring 2FA")
                        return False
            
            # Default: require 2FA for safety
            logger.info(f"Unknown session state for user {user_id}, requiring 2FA for safety")
            return True
            
        except Exception as e:
            logger.error(f"Error checking 2FA requirement: {e}")
            # Default to requiring 2FA for security
            return True
    
    @staticmethod
    def create_active_session(user_id: str, session_id: str):
        """
        Create an active session (2FA not required for this session)
        
        Args:
            user_id: User ID
            session_id: New session ID
        """
        try:
            query = """
            INSERT INTO user_sessions (
                id, user_id, session_type, created_at
            )
            VALUES (%s, %s, %s, %s)
            """
            
            rds_db.execute_query(query, (
                session_id,
                user_id,
                Enhanced2FAService.SESSION_ACTIVE,
                datetime.utcnow()
            ))
            
            logger.info(f"Active session created for user: {user_id}")
            
        except Exception as e:
            logger.error(f"Error creating active session: {e}")
    
    @staticmethod
    def verify_2fa_for_operation(user_id: str, operation: str, code: str) -> Tuple[bool, str]:
        """
        Verify 2FA code for sensitive operations
        
        Args:
            user_id: User ID
            operation: Operation type (e.g., 'delete_meeting')
            code: 2FA code
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if operation requires 2FA
            if operation not in Enhanced2FAService.SENSITIVE_OPERATIONS:
                return True, "Operation does not require 2FA"
            
            # Check if user has 2FA enabled
            if not Enhanced2FAService.is_2fa_enabled(user_id):
                return True, "2FA not enabled for user"
            
            # Get user's secret
            secret = Enhanced2FAService.get_2fa_secret(user_id)
            if not secret:
                return False, "2FA secret not found"
            
            # Verify TOTP code
            if Enhanced2FAService.verify_totp_code(secret, code):
                logger.info(f"2FA verified for operation: {operation} by user: {user_id}")
                return True, "2FA verification successful"
            
            # Try backup code
            if Enhanced2FAService.verify_backup_code(user_id, code):
                logger.info(f"Backup code used for operation: {operation} by user: {user_id}")
                return True, "Backup code verification successful"
            
            return False, "Invalid 2FA code"
            
        except Exception as e:
            logger.error(f"Error verifying 2FA for operation: {e}")
            return False, "2FA verification failed"
    
    @staticmethod
    def get_remaining_backup_codes(user_id: str) -> int:
        """Get count of remaining unused backup codes"""
        try:
            query = "SELECT backup_codes FROM users WHERE id = %s"
            result = rds_db.execute_query(query, (user_id,), fetch_one=True)
            
            if not result or not result.get('backup_codes'):
                return 0
            
            import json
            backup_codes = json.loads(result['backup_codes'])
            return sum(1 for code in backup_codes if not code.get('used', False))
            
        except Exception as e:
            logger.error(f"Error getting backup codes count: {e}")
            return 0


# Singleton instance
enhanced_2fa_service = Enhanced2FAService()
