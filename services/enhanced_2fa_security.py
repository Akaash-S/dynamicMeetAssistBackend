"""
Enhanced Two-Factor Authentication Security Service
Uses in-memory storage for session management and rate limiting
"""

import os
import hashlib
import secrets
import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import logging
import json
from twilio.rest import Client

logger = logging.getLogger(__name__)


class Enhanced2FAService:
    def __init__(self):
        # In-memory storage
        self._memory_storage = {}
        
        # Twilio configuration
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        if self.twilio_account_sid and self.twilio_auth_token:
            self.twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
        else:
            self.twilio_client = None
        
        # Security settings
        self.code_expiry_minutes = 10
        self.max_attempts = 5
        self.lockout_duration_minutes = 30
        self.rate_limit_window = 60  # seconds
        self.max_requests_per_window = 3
        
        # App configuration
        self.app_name = os.getenv('APP_NAME', 'AI Meeting Assistant')
        self.app_issuer = os.getenv('APP_ISSUER', 'AI Meeting Assistant')
    
    def _generate_secure_code(self, length: int = 6) -> str:
        """Generate cryptographically secure random code"""
        # Use secrets module for cryptographic randomness
        code = ''.join(secrets.choice('0123456789') for _ in range(length))
        return code
    
    def _hash_identifier(self, identifier: str) -> str:
        """Hash identifier for secure storage"""
        return hashlib.sha256(identifier.encode()).hexdigest()
    
    def _store_data(self, key: str, data: dict, expiry_seconds: int):
        """Store data in memory"""
        self._memory_storage[key] = {
            'data': data,
            'expiry': datetime.now() + timedelta(seconds=expiry_seconds)
        }
    
    def _get_data(self, key: str) -> Optional[dict]:
        """Retrieve data from memory"""
        stored = self._memory_storage.get(key)
        if stored and datetime.now() < stored['expiry']:
            return stored['data']
        elif stored:
            del self._memory_storage[key]
        return None
    
    def _delete_data(self, key: str):
        """Delete data from memory"""
        self._memory_storage.pop(key, None)
    
    def _check_rate_limit(self, identifier: str) -> Tuple[bool, str]:
        """Check if request is within rate limit"""
        rate_key = f"rate_limit:{self._hash_identifier(identifier)}"
        
        # In-memory rate limiting
        rate_data = self._get_data(rate_key)
        if not rate_data:
            self._store_data(rate_key, {'count': 1}, self.rate_limit_window)
            return True, ""
        
        count = rate_data.get('count', 0) + 1
        if count > self.max_requests_per_window:
            return False, "Too many requests. Please wait before trying again."
        
        rate_data['count'] = count
        self._store_data(rate_key, rate_data, self.rate_limit_window)
        return True, ""
    
    def _check_lockout(self, identifier: str) -> Tuple[bool, str]:
        """Check if identifier is locked out"""
        lockout_key = f"lockout:{self._hash_identifier(identifier)}"
        lockout_data = self._get_data(lockout_key)
        
        if lockout_data:
            remaining = lockout_data.get('until', datetime.now().isoformat())
            return True, f"Account temporarily locked. Try again after {remaining}"
        return False, ""
    
    def _apply_lockout(self, identifier: str):
        """Apply lockout to identifier"""
        lockout_key = f"lockout:{self._hash_identifier(identifier)}"
        until = datetime.now() + timedelta(minutes=self.lockout_duration_minutes)
        
        self._store_data(
            lockout_key,
            {'until': until.isoformat()},
            self.lockout_duration_minutes * 60
        )
        logger.warning(f"Lockout applied to: {self._hash_identifier(identifier)}")
    
    # Email 2FA Methods
    def send_email_verification_code(
        self,
        email: str,
        email_service
    ) -> Tuple[bool, str]:
        """Send verification code via email with enhanced security"""
        # Check rate limit
        allowed, message = self._check_rate_limit(f"email_{email}")
        if not allowed:
            return False, message
        
        # Check lockout
        locked, message = self._check_lockout(f"email_{email}")
        if locked:
            return False, message
        
        try:
            code = self._generate_secure_code()
            hashed_code = hashlib.sha256(code.encode()).hexdigest()
            
            key = f"2fa_email:{self._hash_identifier(email)}"
            self._store_data(
                key,
                {
                    'code_hash': hashed_code,
                    'attempts': 0,
                    'created_at': datetime.now().isoformat()
                },
                self.code_expiry_minutes * 60
            )
            
            # Send email
            success = email_service.send_2fa_email_code(email, code)
            
            if success:
                return True, "Verification code sent to your email"
            else:
                return False, "Failed to send verification code"
        except Exception as e:
            logger.error(f"Error sending email verification code: {e}")
            return False, "Failed to send verification code"
    
    def verify_email_code(self, email: str, code: str) -> Tuple[bool, str]:
        """Verify email verification code with enhanced security"""
        # Check lockout
        locked, message = self._check_lockout(f"email_{email}")
        if locked:
            return False, message
        
        key = f"2fa_email:{self._hash_identifier(email)}"
        stored_data = self._get_data(key)
        
        if not stored_data:
            return False, "No verification code found. Please request a new one."
        
        # Check attempts
        attempts = stored_data.get('attempts', 0)
        if attempts >= self.max_attempts:
            self._delete_data(key)
            self._apply_lockout(f"email_{email}")
            return False, "Too many failed attempts. Account temporarily locked."
        
        # Verify code
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        if stored_data['code_hash'] == code_hash:
            self._delete_data(key)
            return True, "Verification successful"
        else:
            # Increment attempts
            stored_data['attempts'] = attempts + 1
            self._store_data(key, stored_data, self.code_expiry_minutes * 60)
            return False, f"Invalid verification code. {self.max_attempts - attempts - 1} attempts remaining."
    
    # SMS 2FA Methods
    def send_sms_verification_code(self, phone_number: str) -> Tuple[bool, str]:
        """Send verification code via SMS with enhanced security"""
        if not self.twilio_client:
            return False, "SMS service not configured"
        
        # Check rate limit
        allowed, message = self._check_rate_limit(f"sms_{phone_number}")
        if not allowed:
            return False, message
        
        # Check lockout
        locked, message = self._check_lockout(f"sms_{phone_number}")
        if locked:
            return False, message
        
        try:
            code = self._generate_secure_code()
            hashed_code = hashlib.sha256(code.encode()).hexdigest()
            
            key = f"2fa_sms:{self._hash_identifier(phone_number)}"
            self._store_data(
                key,
                {
                    'code_hash': hashed_code,
                    'attempts': 0,
                    'created_at': datetime.now().isoformat()
                },
                self.code_expiry_minutes * 60
            )
            
            # Send SMS
            message = self.twilio_client.messages.create(
                body=f"Your {self.app_name} verification code is: {code}. Valid for {self.code_expiry_minutes} minutes. Do not share this code.",
                from_=self.twilio_phone_number,
                to=phone_number
            )
            
            logger.info(f"SMS sent successfully. SID: {message.sid}")
            return True, "Verification code sent to your phone"
        except Exception as e:
            logger.error(f"Error sending SMS verification code: {e}")
            return False, "Failed to send verification code"
    
    def verify_sms_code(self, phone_number: str, code: str) -> Tuple[bool, str]:
        """Verify SMS verification code with enhanced security"""
        # Check lockout
        locked, message = self._check_lockout(f"sms_{phone_number}")
        if locked:
            return False, message
        
        key = f"2fa_sms:{self._hash_identifier(phone_number)}"
        stored_data = self._get_data(key)
        
        if not stored_data:
            return False, "No verification code found. Please request a new one."
        
        # Check attempts
        attempts = stored_data.get('attempts', 0)
        if attempts >= self.max_attempts:
            self._delete_data(key)
            self._apply_lockout(f"sms_{phone_number}")
            return False, "Too many failed attempts. Account temporarily locked."
        
        # Verify code
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        if stored_data['code_hash'] == code_hash:
            self._delete_data(key)
            return True, "Verification successful"
        else:
            # Increment attempts
            stored_data['attempts'] = attempts + 1
            self._store_data(key, stored_data, self.code_expiry_minutes * 60)
            return False, f"Invalid verification code. {self.max_attempts - attempts - 1} attempts remaining."
    
    # Authenticator App (TOTP) Methods
    def setup_authenticator_app(self, user_email: str) -> Tuple[bool, Optional[Dict]]:
        """Setup authenticator app with enhanced security"""
        try:
            # Generate cryptographically secure secret
            secret = pyotp.random_base32()
            
            # Create TOTP instance
            totp = pyotp.TOTP(secret)
            
            # Generate provisioning URI
            provisioning_uri = totp.provisioning_uri(
                name=user_email,
                issuer_name=self.app_issuer
            )
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            qr_code_data_uri = f"data:image/png;base64,{img_str}"
            
            # Store secret temporarily with expiration
            key = f"2fa_app_setup:{self._hash_identifier(user_email)}"
            self._store_data(
                key,
                {
                    'secret': secret,
                    'created_at': datetime.now().isoformat()
                },
                1800  # 30 minutes
            )
            
            return True, {
                'secret': secret,
                'qrCode': qr_code_data_uri
            }
        except Exception as e:
            logger.error(f"Error setting up authenticator app: {e}")
            return False, None
    
    def verify_authenticator_code(
        self,
        user_email: str,
        code: str,
        secret: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Verify authenticator app code with enhanced security"""
        # Check lockout
        locked, message = self._check_lockout(f"app_{user_email}")
        if locked:
            return False, message
        
        try:
            # Get secret from storage if not provided
            if not secret:
                key = f"2fa_app_setup:{self._hash_identifier(user_email)}"
                stored_data = self._get_data(key)
                if not stored_data:
                    return False, "Setup not found. Please start setup again."
                secret = stored_data['secret']
            
            # Create TOTP instance
            totp = pyotp.TOTP(secret)
            
            # Verify code with extended window for time drift
            if totp.verify(code, valid_window=2):
                # Clean up temp secret
                key = f"2fa_app_setup:{self._hash_identifier(user_email)}"
                self._delete_data(key)
                return True, "Verification successful"
            else:
                # Track failed attempts
                attempt_key = f"2fa_app_attempts:{self._hash_identifier(user_email)}"
                attempts_data = self._get_data(attempt_key) or {'count': 0}
                attempts_data['count'] += 1
                
                if attempts_data['count'] >= self.max_attempts:
                    self._apply_lockout(f"app_{user_email}")
                    self._delete_data(attempt_key)
                    return False, "Too many failed attempts. Account temporarily locked."
                
                self._store_data(attempt_key, attempts_data, 300)  # 5 minutes
                return False, f"Invalid verification code. {self.max_attempts - attempts_data['count']} attempts remaining."
        except Exception as e:
            logger.error(f"Error verifying authenticator code: {e}")
            return False, "Verification failed"
    
    def verify_totp_login(self, secret: str, code: str) -> bool:
        """Verify TOTP code during login"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=2)
        except Exception as e:
            logger.error(f"Error verifying TOTP login code: {e}")
            return False
    
    def cleanup_expired_data(self):
        """Cleanup expired data from in-memory storage"""
        now = datetime.now()
        expired_keys = [
            key for key, value in self._memory_storage.items()
            if value['expiry'] < now
        ]
        for key in expired_keys:
            del self._memory_storage[key]
        logger.info(f"Cleaned up {len(expired_keys)} expired entries")


# Global enhanced 2FA service instance
enhanced_2fa_service = Enhanced2FAService()
