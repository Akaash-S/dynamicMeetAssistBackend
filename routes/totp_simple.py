"""
Simplified TOTP Two-Factor Authentication Routes
Google Authenticator (TOTP) only - Single 2FA method
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

totp_bp = Blueprint('totp', __name__)


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get user ID from header or request args
        user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        request.user_id = user_id
        return f(*args, **kwargs)
    return decorated_function


@totp_bp.route('/2fa/setup', methods=['POST'])
def setup_totp():
    """
    Setup TOTP 2FA (Google Authenticator)
    Returns QR code and secret for user to scan
    
    Body: { "user_id": "firebase_uid" }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Get user info
        user = rds_db.execute_query(
            'SELECT email, name FROM users WHERE firebase_uid = %s OR id = %s',
            (user_id, user_id),
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
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
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
        return jsonify({'error': f'Failed to setup 2FA: {str(e)}'}), 500


@totp_bp.route('/2fa/verify', methods=['POST'])
def verify_totp():
    """
    Verify TOTP code and enable 2FA
    
    Body: { "user_id": "firebase_uid", "code": "123456", "secret": "BASE32SECRET" }
    """
    try:
        data = request.get_json()
        code = data.get('code')
        secret = data.get('secret')
        user_id = data.get('user_id')
        
        if not code or not secret or not user_id:
            return jsonify({'error': 'User ID, code, and secret are required'}), 400
        
        # Get user info
        user = rds_db.execute_query(
            'SELECT id, email, name, firebase_uid FROM users WHERE firebase_uid = %s OR id = %s',
            (user_id, user_id),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify TOTP code
        totp = pyotp.TOTP(secret)
        is_valid = totp.verify(code, valid_window=1)  # Allow 1 time step tolerance (30 seconds)
        
        if not is_valid:
            logger.warning(f"Invalid TOTP code for user: {user['email']}")
            return jsonify({
                'success': False,
                'error': 'Invalid verification code. Please try again.'
            }), 400
        
        # Enable 2FA in database
        rds_db.execute_query(
            '''
            UPDATE users 
            SET two_factor_enabled = TRUE,
                two_factor_method = 'totp',
                two_factor_secret = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            ''',
            (secret, user['id'])
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
            'message': '2FA enabled successfully with Google Authenticator'
        }), 200
        
    except Exception as e:
        logger.error(f"Error verifying TOTP: {e}")
        return jsonify({'error': f'Failed to verify code: {str(e)}'}), 500


@totp_bp.route('/2fa/validate', methods=['POST'])
def validate_totp():
    """
    Validate TOTP code during login
    
    Body: { "user_id": "firebase_uid", "code": "123456" }
    """
    try:
        data = request.get_json()
        code = data.get('code')
        user_id = data.get('user_id')
        
        if not code or not user_id:
            return jsonify({'error': 'User ID and verification code are required'}), 400
        
        # Get user's secret
        user = rds_db.execute_query(
            '''
            SELECT id, email, two_factor_secret, two_factor_enabled 
            FROM users 
            WHERE firebase_uid = %s OR id = %s
            ''',
            (user_id, user_id),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user['two_factor_enabled']:
            return jsonify({'error': '2FA is not enabled for this account'}), 400
        
        if not user['two_factor_secret']:
            return jsonify({'error': '2FA secret not found. Please set up 2FA again.'}), 400
        
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
                'error': 'Invalid verification code. Please try again.'
            }), 400
        
    except Exception as e:
        logger.error(f"Error validating TOTP: {e}")
        return jsonify({'error': f'Failed to validate code: {str(e)}'}), 500


@totp_bp.route('/2fa/status', methods=['GET'])
def get_2fa_status():
    """
    Get 2FA status for current user
    
    Query: ?user_id=firebase_uid
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        user = rds_db.execute_query(
            '''
            SELECT two_factor_enabled, two_factor_method 
            FROM users 
            WHERE firebase_uid = %s OR id = %s
            ''',
            (user_id, user_id),
            fetch_one=True
        )
        
        if not user:
            return jsonify({
                'enabled': False,
                'method': 'none'
            }), 200
        
        return jsonify({
            'enabled': bool(user['two_factor_enabled']),
            'method': user['two_factor_method'] or 'none'
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting 2FA status: {e}")
        return jsonify({'error': f'Failed to get 2FA status: {str(e)}'}), 500


@totp_bp.route('/2fa/disable', methods=['POST'])
def disable_2fa():
    """
    Disable 2FA for current user
    
    Body: { "user_id": "firebase_uid", "code": "123456" }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        code = data.get('code')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Get user info
        user = rds_db.execute_query(
            '''
            SELECT id, email, two_factor_secret, two_factor_enabled 
            FROM users 
            WHERE firebase_uid = %s OR id = %s
            ''',
            (user_id, user_id),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user['two_factor_enabled']:
            return jsonify({'error': '2FA is not enabled'}), 400
        
        # Verify code before disabling (security measure)
        if code:
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
                two_factor_secret = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            ''',
            (user['id'],)
        )
        
        logger.info(f"2FA disabled for user: {user['email']}")
        
        return jsonify({
            'success': True,
            'message': '2FA disabled successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error disabling 2FA: {e}")
        return jsonify({'error': f'Failed to disable 2FA: {str(e)}'}), 500


@totp_bp.route('/2fa/backup-codes', methods=['POST'])
def generate_backup_codes():
    """
    Generate backup codes for 2FA
    
    Body: { "user_id": "firebase_uid" }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Get user info
        user = rds_db.execute_query(
            'SELECT id, email, two_factor_enabled FROM users WHERE firebase_uid = %s OR id = %s',
            (user_id, user_id),
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
            SET backup_codes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            ''',
            (','.join(hashed_codes), user['id'])
        )
        
        logger.info(f"Backup codes generated for user: {user['email']}")
        
        return jsonify({
            'success': True,
            'backup_codes': backup_codes,
            'message': 'Save these codes in a safe place. Each code can only be used once.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating backup codes: {e}")
        return jsonify({'error': f'Failed to generate backup codes: {str(e)}'}), 500
