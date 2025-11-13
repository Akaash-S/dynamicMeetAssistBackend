"""
Two-Factor Authentication Service
Supports Email, SMS, and Authenticator App (TOTP) verification
"""

import os
import random
import string
import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)


class TwoFactorAuthService:
    def __init__(self):
        # Twilio configuration for SMS
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        # App configuration
        self.app_name = os.getenv('APP_NAME', 'AI Meeting Assistant')
        self.app_issuer = os.getenv('APP_ISSUER', 'AI Meeting Assistant')
        
        # Initialize Twilio client if credentials are available
        if self.twilio_account_sid and self.twilio_auth_token:
            self.twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
        else:
            self.twilio_client = None
            logger.warning("Twilio credentials not configured. SMS 2FA will be disabled.")
        
        # In-memory storage for codes
        self.verification_codes = {}
        self.temp_secrets = {}
    
    def generate_verification_code(self, length: int = 6) -> str:
        """Generate a random numeric verification code"""
        return ''.join(random.choices(string.digits, k=length))
    
    def store_verification_code(
        self,
        identifier: str,
        code: str,
        expires_in_minutes: int = 10
    ) -> None:
        """Store verification code with expiration"""
        expiry = datetime.now() + timedelta(minutes=expires_in_minutes)
        self.verification_codes[identifier] = {
            'code': code,
            'expiry': expiry,
            'attempts': 0
        }
    
    def verify_code(
        self,
        identifier: str,
        code: str,
        max_attempts: int = 5
    ) -> Tuple[bool, str]:
        """
        Verify a code
        Returns: (success: bool, message: str)
        """
        if identifier not in self.verification_codes:
            return False, "No verification code found. Please request a new one."
        
        stored_data = self.verification_codes[identifier]
        
        # Check expiration
        if datetime.now() > stored_data['expiry']:
            del self.verification_codes[identifier]
            return False, "Verification code has expired. Please request a new one."
        
        # Check attempts
        if stored_data['attempts'] >= max_attempts:
            del self.verification_codes[identifier]
            return False, "Too many failed attempts. Please request a new code."
        
        # Verify code
        if stored_data['code'] == code:
            del self.verification_codes[identifier]
            return True, "Verification successful"
        else:
            stored_data['attempts'] += 1
            return False, "Invalid verification code"
    
    def cleanup_expired_codes(self) -> None:
        """Remove expired verification codes"""
        now = datetime.now()
        expired_keys = [
            key for key, data in self.verification_codes.items()
            if now > data['expiry']
        ]
        for key in expired_keys:
            del self.verification_codes[key]
    
    # Email 2FA Methods
    def send_email_verification_code(
        self,
        email: str,
        email_service
    ) -> Tuple[bool, str]:
        """
        Send verification code via email
        Returns: (success: bool, message: str)
        """
        try:
            code = self.generate_verification_code()
            self.store_verification_code(f"email_{email}", code)
            
            # Send email using email service
            success = email_service.send_2fa_email_code(email, code)
            
            if success:
                return True, "Verification code sent to your email"
            else:
                return False, "Failed to send verification code"
        except Exception as e:
            logger.error(f"Error sending email verification code: {e}")
            return False, "Failed to send verification code"
    
    def verify_email_code(self, email: str, code: str) -> Tuple[bool, str]:
        """Verify email verification code"""
        return self.verify_code(f"email_{email}", code)
    
    # SMS 2FA Methods
    def send_sms_verification_code(
        self,
        phone_number: str
    ) -> Tuple[bool, str]:
        """
        Send verification code via SMS
        Returns: (success: bool, message: str)
        """
        if not self.twilio_client:
            return False, "SMS service not configured"
        
        try:
            code = self.generate_verification_code()
            self.store_verification_code(f"sms_{phone_number}", code)
            
            # Send SMS via Twilio
            message = self.twilio_client.messages.create(
                body=f"Your {self.app_name} verification code is: {code}. Valid for 10 minutes.",
                from_=self.twilio_phone_number,
                to=phone_number
            )
            
            logger.info(f"SMS sent successfully. SID: {message.sid}")
            return True, "Verification code sent to your phone"
        except Exception as e:
            logger.error(f"Error sending SMS verification code: {e}")
            return False, "Failed to send verification code"
    
    def verify_sms_code(
        self,
        phone_number: str,
        code: str
    ) -> Tuple[bool, str]:
        """Verify SMS verification code"""
        return self.verify_code(f"sms_{phone_number}", code)
    
    # Authenticator App (TOTP) Methods
    def setup_authenticator_app(
        self,
        user_email: str
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Setup authenticator app (TOTP)
        Returns: (success: bool, data: Optional[Dict])
        """
        try:
            # Generate secret
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
                error_correction=qrcode.constants.ERROR_CORRECT_L,
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
            
            # Store secret temporarily
            self.temp_secrets[user_email] = {
                'secret': secret,
                'created_at': datetime.now()
            }
            
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
        """
        Verify authenticator app code
        Returns: (success: bool, message: str)
        """
        try:
            # Use provided secret or get from temp storage
            if not secret:
                if user_email not in self.temp_secrets:
                    return False, "Setup not found. Please start setup again."
                secret = self.temp_secrets[user_email]['secret']
            
            # Create TOTP instance
            totp = pyotp.TOTP(secret)
            
            # Verify code (with 1 time window tolerance)
            if totp.verify(code, valid_window=1):
                # Clean up temp secret
                if user_email in self.temp_secrets:
                    del self.temp_secrets[user_email]
                return True, "Verification successful"
            else:
                return False, "Invalid verification code"
        except Exception as e:
            logger.error(f"Error verifying authenticator code: {e}")
            return False, "Verification failed"
    
    def verify_totp_code(self, secret: str, code: str) -> bool:
        """
        Verify TOTP code for login (when 2FA is already enabled)
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=1)
        except Exception as e:
            logger.error(f"Error verifying TOTP code: {e}")
            return False
    
    def cleanup_temp_secrets(self, max_age_minutes: int = 30) -> None:
        """Remove old temporary secrets"""
        cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
        expired_keys = [
            key for key, data in self.temp_secrets.items()
            if data['created_at'] < cutoff
        ]
        for key in expired_keys:
            del self.temp_secrets[key]


# Global 2FA service instance
two_factor_auth_service = TwoFactorAuthService()
