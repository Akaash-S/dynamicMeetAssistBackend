"""
TOTP Two-Factor Authentication Routes
Handles Google Authenticator (TOTP) 2FA only
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import logging
import pyotp
import qrcode
import io
import base64
from config.aws_rds_database import rds_db
from services.email_service import email_service

logger = logging.getLogger(__name__)

totp_auth_bp = Blueprint('totp_auth', __name__)


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


@totp_auth_bp.route('/2fa/setup', methods=['POST'])
@require_auth
def setup_totp():
    """
    Setup TOTP 2FA (Google Authenticator)
    Returns QR code and secret for user to scan
    """
    try:
        user_id = request.headers.get('X-User-ID')
        
        # Get user info
        user = rds_db.execute_query(
            'SELECT email, name FROM users WHERE firebase_uid = %s',
            (user_id, fetch_all==True),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Generate secret
        secret = pyotp.random_base32()
        
        # Create TOTP URI
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user['email'],
            issuer_name='MeetingMind'
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        logger.info(f"TOTP setup initiated for user: {user['email']}")
        
        return jsonify({
            'success': True,
            'secret': secret,
            'qrCode': f'data:image/png;base64,{qr_code_base64}',
            'manualEntry': secret,
            'issuer': 'MeetingMind',
            'account': user['email']
        }), 200
        
    except Exception as e:
        logger.error(f"Error setting up TOTP: {e}")
        return jsonify({'error': 'Failed to setup 2FA'}), 500


@totp_auth_bp.route('/2fa/verify', methods=['POST'])
@require_auth
def verify_totp():
    """
    Verify TOTP code and enable 2FA
    """
    try:
        data = request.get_json()
        code = data.get('code')
        secret = data.get('secret')
        user_id = request.headers.get('X-User-ID')
        
        if not code or not secret:
            return jsonify({'error': 'Code and secret are required'}), 400
        
        # Get user info
        user = rds_db.execute_query(
            'SELECT email, name FROM users WHERE firebase_uid = %s',
            (user_id, fetch_all==True),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify TOTP code
        totp = pyotp.TOTP(secret)
        is_valid = totp.verify(code, valid_window=1)  # Allow 1 time step tolerance
        
        if not is_valid:
            logger.warning(f"Invalid TOTP code for user: {user['email']}")
            return jsonify({
                'success': False,
                'error': 'Invalid verification code'
            }), 400
        
        # Enable 2FA in database
        rds_db.execute_query(
            '''
            UPDATE users 
            SET two_factor_enabled = TRUE,
                two_factor_method = 'totp',
                two_factor_secret = %s
            WHERE firebase_uid = %s
            ''',
            (secret, user_id)
        )
        
        # Send confirmation email
        try:
            email_service.send_2fa_enabled_notification(
                user['email'],
                user['name'],
                'Google Authenticator (TOTP)'
            )
        except Exception as email_error:
            logger.warning(f"Failed to send confirmation email: {email_error}")
        
        logger.info(f"TOTP 2FA enabled for user: {user['email']}")
        
        return jsonify({
            'success': True,
            'message': '2FA enabled successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error verifying TOTP: {e}")
        return jsonify({'error': 'Failed to verify code'}), 500


@totp_auth_bp.route('/2fa/validate', methods=['POST'])
@require_auth
def validate_totp():
    """
    Validate TOTP code during login
    """
    try:
        data = request.get_json()
        code = data.get('code')
        user_id = request.headers.get('X-User-ID')
        
        if not code:
            return jsonify({'error': 'Verification code is required'}), 400
        
        # Get user's secret
        user = rds_db.execute_query(
            '''
            SELECT email, two_factor_secret, two_factor_enabled 
            FROM users 
            WHERE firebase_uid = %s
            ''',
            (user_id, fetch_all==True),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user['two_factor_enabled']:
            return jsonify({'error': '2FA is not enabled'}), 400
        
        if not user['two_factor_secret']:
            return jsonify({'error': '2FA secret not found'}), 400
        
        # Verify TOTP code
        totp = pyotp.TOTP(user['two_factor_secret'])
        is_valid = totp.verify(code, valid_window=1)
        
        if is_valid:
            logger.info(f"TOTP validation successful for user: {user['email']}")
            return jsonify({
                'success': True,
                'message': 'Code verified successfully'
            }), 200
        else:
            logger.warning(f"Invalid TOTP code during login for user: {user['email']}")
            return jsonify({
                'success': False,
                'error': 'Invalid verification code'
            }), 400
        
    except Exception as e:
        logger.error(f"Error validating TOTP: {e}")
        return jsonify({'error': 'Failed to validate code'}), 500


@totp_auth_bp.route('/2fa/status', methods=['GET'])
@require_auth
def get_2fa_status():
    """Get 2FA status for current user"""
    try:
        user_id = request.headers.get('X-User-ID')
        
        user = rds_db.execute_query(
            '''
            SELECT two_factor_enabled, two_factor_method 
            FROM users 
            WHERE firebase_uid = %s
            ''',
            (user_id, fetch_all==True),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'enabled': bool(user['two_factor_enabled']),
            'method': user['two_factor_method'] or 'none'
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting 2FA status: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@totp_auth_bp.route('/2fa/disable', methods=['POST'])
@require_auth
def disable_2fa():
    """Disable 2FA for current user"""
    try:
        data = request.get_json()
        code = data.get('code')  # Require current code to disable
        user_id = request.headers.get('X-User-ID')
        
        if not code:
            return jsonify({'error': 'Verification code is required to disable 2FA'}), 400
        
        # Get user info
        user = rds_db.execute_query(
            '''
            SELECT email, name, two_factor_secret, two_factor_enabled 
            FROM users 
            WHERE firebase_uid = %s
            ''',
            (user_id, fetch_all==True),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user['two_factor_enabled']:
            return jsonify({'error': '2FA is not enabled'}), 400
        
        # Verify code before disabling
        totp = pyotp.TOTP(user['two_factor_secret'])
        is_valid = totp.verify(code, valid_window=1)
        
        if not is_valid:
            return jsonify({'error': 'Invalid verification code'}), 400
        
        # Disable 2FA
        rds_db.execute_query(
            '''
            UPDATE users 
            SET two_factor_enabled = FALSE,
                two_factor_method = NULL,
                two_factor_secret = NULL
            WHERE firebase_uid = %s
            ''',
            (user_id,)
        )
        
        # Send notification email
        try:
            email_service.send_email(
                to_email=user['email'],
                subject='Two-Factor Authentication Disabled',
                body=f"""
                Hello {user['name']},
                
                Two-factor authentication has been disabled for your MeetingMind account.
                
                If you did not make this change, please contact support immediately.
                
                Best regards,
                MeetingMind Team
                """
            )
        except Exception as email_error:
            logger.warning(f"Failed to send notification email: {email_error}")
        
        logger.info(f"2FA disabled for user: {user['email']}")
        
        return jsonify({
            'success': True,
            'message': '2FA disabled successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error disabling 2FA: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@totp_auth_bp.route('/2fa/backup-codes', methods=['POST'])
@require_auth
def generate_backup_codes():
    """
    Generate backup codes for account recovery
    """
    try:
        user_id = request.headers.get('X-User-ID')
        
        # Get user info
        user = rds_db.execute_query(
            'SELECT email, two_factor_enabled FROM users WHERE firebase_uid = %s',
            (user_id, fetch_all==True),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user['two_factor_enabled']:
            return jsonify({'error': '2FA must be enabled first'}), 400
        
        # Generate 10 backup codes
        import secrets
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        
        # Store hashed backup codes in database
        import hashlib
        hashed_codes = [hashlib.sha256(code.encode()).hexdigest() for code in backup_codes]
        
        rds_db.execute_query(
            '''
            UPDATE users 
            SET backup_codes = %s
            WHERE firebase_uid = %s
            ''',
            (','.join(hashed_codes), user_id)
        )
        
        logger.info(f"Backup codes generated for user: {user['email']}")
        
        return jsonify({
            'success': True,
            'codes': backup_codes,
            'message': 'Save these codes in a safe place. Each code can only be used once.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating backup codes: {e}")
        return jsonify({'error': 'Failed to generate backup codes'}), 500
