"""
Enhanced 2FA Authentication Routes
===================================
Handles 2FA for:
- Manual logout/login
- Sensitive operations (data deletion)
- Active session management
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import logging
import pyotp
import qrcode
import io
import base64
from datetime import datetime
from config.aws_rds_database import rds_db
from services.enhanced_2fa_service import enhanced_2fa_service
from middleware.validation import add_security_headers

logger = logging.getLogger(__name__)

auth_2fa_bp = Blueprint('auth_2fa', __name__)


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            logger.error(f"❌ Authentication failed: No X-User-ID header")
            logger.error(f"❌ Request headers: {dict(request.headers)}")
            return jsonify({
                'error': 'Authentication required',
                'message': 'X-User-ID header is missing',
                'hint': 'Make sure you are logged in and Firebase Auth is initialized'
            }), 401
        logger.info(f"✅ Authentication successful for user: {user_id}")
        return f(*args, **kwargs)
    return decorated_function


@auth_2fa_bp.route('/2fa/setup', methods=['POST'])
@add_security_headers()
@require_auth
def setup_2fa():
    """
    Setup 2FA for user
    Returns QR code and secret
    """
    try:
        user_id = request.headers.get('X-User-ID')
        
        # Get user info
        user = rds_db.execute_query(
            'SELECT id, email, name FROM users WHERE firebase_uid = %s',
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Generate secret
        secret = enhanced_2fa_service.generate_secret()
        
        # Create TOTP URI
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user['email'],
            issuer_name='Dynamic Meeting Assistant'
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
        
        logger.info(f"2FA setup initiated for user: {user['email']}")
        
        return jsonify({
            'success': True,
            'data': {
                'secret': secret,
                'qrCode': f'data:image/png;base64,{qr_code_base64}',
                'manualEntry': secret,
                'issuer': 'Dynamic Meeting Assistant',
                'account': user['email']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error setting up 2FA: {e}")
        return jsonify({'error': 'Failed to setup 2FA'}), 500


@auth_2fa_bp.route('/2fa/enable', methods=['POST'])
@add_security_headers()
@require_auth
def enable_2fa():
    """
    Enable 2FA after verifying initial code
    Returns backup codes
    """
    try:
        data = request.get_json()
        code = data.get('code')
        secret = data.get('secret')
        user_id = request.headers.get('X-User-ID')
        
        if not code or not secret:
            return jsonify({'error': 'Code and secret are required'}), 400
        
        # Get user's internal ID
        user = rds_db.execute_query(
            'SELECT id FROM users WHERE firebase_uid = %s',
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        internal_user_id = user['id']
        
        # Verify code
        if not enhanced_2fa_service.verify_totp_code(secret, code):
            return jsonify({'error': 'Invalid verification code'}), 400
        
        # Enable 2FA
        success, backup_codes = enhanced_2fa_service.enable_2fa(internal_user_id, secret)
        
        if not success:
            return jsonify({'error': 'Failed to enable 2FA'}), 500
        
        logger.info(f"2FA enabled for user: {internal_user_id}")
        
        return jsonify({
            'success': True,
            'message': '2FA enabled successfully',
            'data': {
                'backupCodes': backup_codes
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error enabling 2FA: {e}")
        return jsonify({'error': 'Failed to enable 2FA'}), 500


@auth_2fa_bp.route('/2fa/disable', methods=['POST'])
@add_security_headers()
@require_auth
def disable_2fa():
    """
    Disable 2FA (requires 2FA verification)
    """
    try:
        data = request.get_json()
        code = data.get('code')
        user_id = request.headers.get('X-User-ID')
        
        if not code:
            return jsonify({'error': 'Verification code is required'}), 400
        
        # Get user's internal ID
        user = rds_db.execute_query(
            'SELECT id FROM users WHERE firebase_uid = %s',
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        internal_user_id = user['id']
        
        # Verify 2FA code before disabling
        success, message = enhanced_2fa_service.verify_2fa_for_operation(
            internal_user_id, 'disable_2fa', code
        )
        
        if not success:
            return jsonify({'error': message}), 400
        
        # Disable 2FA
        if not enhanced_2fa_service.disable_2fa(internal_user_id):
            return jsonify({'error': 'Failed to disable 2FA'}), 500
        
        logger.info(f"2FA disabled for user: {internal_user_id}")
        
        return jsonify({
            'success': True,
            'message': '2FA disabled successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error disabling 2FA: {e}")
        return jsonify({'error': 'Failed to disable 2FA'}), 500


@auth_2fa_bp.route('/2fa/verify-login', methods=['POST'])
@add_security_headers()
def verify_2fa_login():
    """
    Verify 2FA code during login (after manual logout)
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')  # Firebase UID
        code = data.get('code')
        session_id = data.get('session_id')
        
        if not user_id or not code:
            return jsonify({'error': 'User ID and code are required'}), 400
        
        # Get user's internal ID
        user = rds_db.execute_query(
            'SELECT id FROM users WHERE firebase_uid = %s',
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        internal_user_id = user['id']
        
        # Get user's secret
        secret = enhanced_2fa_service.get_2fa_secret(internal_user_id)
        if not secret:
            return jsonify({'error': '2FA not enabled'}), 400
        
        # Verify code
        if enhanced_2fa_service.verify_totp_code(secret, code):
            # Create active session
            if session_id:
                enhanced_2fa_service.create_active_session(internal_user_id, session_id)
            
            logger.info(f"2FA login verified for user: {internal_user_id}")
            
            return jsonify({
                'success': True,
                'message': '2FA verification successful'
            }), 200
        
        # Try backup code
        if enhanced_2fa_service.verify_backup_code(internal_user_id, code):
            # Create active session
            if session_id:
                enhanced_2fa_service.create_active_session(internal_user_id, session_id)
            
            # Get remaining backup codes
            remaining = enhanced_2fa_service.get_remaining_backup_codes(internal_user_id)
            
            logger.info(f"Backup code used for login by user: {internal_user_id}")
            
            return jsonify({
                'success': True,
                'message': 'Backup code verification successful',
                'data': {
                    'remainingBackupCodes': remaining
                }
            }), 200
        
        return jsonify({'error': 'Invalid verification code'}), 400
        
    except Exception as e:
        logger.error(f"Error verifying 2FA login: {e}")
        return jsonify({'error': 'Failed to verify 2FA'}), 500


@auth_2fa_bp.route('/2fa/verify-operation', methods=['POST'])
@add_security_headers()
@require_auth
def verify_2fa_operation():
    """
    Verify 2FA code for sensitive operations (e.g., data deletion)
    """
    try:
        data = request.get_json()
        code = data.get('code')
        operation = data.get('operation')
        user_id = request.headers.get('X-User-ID')
        
        if not code or not operation:
            return jsonify({'error': 'Code and operation are required'}), 400
        
        # Get user's internal ID
        user = rds_db.execute_query(
            'SELECT id FROM users WHERE firebase_uid = %s',
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        internal_user_id = user['id']
        
        # Verify 2FA for operation
        success, message = enhanced_2fa_service.verify_2fa_for_operation(
            internal_user_id, operation, code
        )
        
        if not success:
            return jsonify({'error': message}), 400
        
        logger.info(f"2FA verified for operation: {operation} by user: {internal_user_id}")
        
        return jsonify({
            'success': True,
            'message': message
        }), 200
        
    except Exception as e:
        logger.error(f"Error verifying 2FA operation: {e}")
        return jsonify({'error': 'Failed to verify 2FA'}), 500


@auth_2fa_bp.route('/2fa/status', methods=['GET'])
@add_security_headers()
@require_auth
def get_2fa_status():
    """
    Get 2FA status for user
    """
    try:
        logger.info("=" * 60)
        logger.info("📡 2FA STATUS ENDPOINT CALLED")
        logger.info(f"📡 Request method: {request.method}")
        logger.info(f"📡 Request path: {request.path}")
        logger.info(f"📡 Request headers: {dict(request.headers)}")
        
        user_id = request.headers.get('X-User-ID')
        
        logger.info(f"📡 2FA status check for Firebase UID: {user_id}")
        
        if not user_id:
            logger.error("❌ No X-User-ID header provided")
            return jsonify({'error': 'X-User-ID header is required'}), 400
        
        # Get user's internal ID
        user = rds_db.execute_query(
            'SELECT id, email FROM users WHERE firebase_uid = %s',
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            logger.error(f"❌ User not found for Firebase UID: {user_id}")
            return jsonify({'error': 'User not found in database'}), 404
        
        internal_user_id = user['id']
        user_email = user.get('email', 'unknown')
        
        logger.info(f"✅ User found: {user_email} (internal ID: {internal_user_id})")
        
        # Expire inactive sessions (10+ minutes old)
        enhanced_2fa_service.expire_inactive_sessions(internal_user_id)
        
        # Check if 2FA is enabled
        is_enabled = enhanced_2fa_service.is_2fa_enabled(internal_user_id)
        logger.info(f"🔐 2FA enabled for {user_email}: {is_enabled}")
        
        # Get remaining backup codes if enabled
        remaining_codes = 0
        if is_enabled:
            remaining_codes = enhanced_2fa_service.get_remaining_backup_codes(internal_user_id)
        
        # Check if 2FA required on next login
        requires_on_login = enhanced_2fa_service.should_require_2fa_on_login(internal_user_id)
        logger.info(f"🔐 2FA required on login for {user_email}: {requires_on_login}")
        
        return jsonify({
            'success': True,
            'data': {
                'enabled': is_enabled,
                'requiresOnLogin': requires_on_login,
                'remainingBackupCodes': remaining_codes
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting 2FA status: {e}", exc_info=True)
        return jsonify({'error': f'Failed to get 2FA status: {str(e)}'}), 500


@auth_2fa_bp.route('/2fa/regenerate-backup-codes', methods=['POST'])
@add_security_headers()
@require_auth
def regenerate_backup_codes():
    """
    Regenerate backup codes (requires 2FA verification)
    """
    try:
        data = request.get_json()
        code = data.get('code')
        user_id = request.headers.get('X-User-ID')
        
        if not code:
            return jsonify({'error': 'Verification code is required'}), 400
        
        # Get user's internal ID
        user = rds_db.execute_query(
            'SELECT id FROM users WHERE firebase_uid = %s',
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        internal_user_id = user['id']
        
        # Verify 2FA code
        success, message = enhanced_2fa_service.verify_2fa_for_operation(
            internal_user_id, 'regenerate_backup_codes', code
        )
        
        if not success:
            return jsonify({'error': message}), 400
        
        # Generate new backup codes
        backup_codes = enhanced_2fa_service.generate_backup_codes()
        
        # Store hashed backup codes
        import json
        backup_codes_data = [
            {
                'hash': enhanced_2fa_service.hash_backup_code(code),
                'used': False
            }
            for code in backup_codes
        ]
        
        # Update database
        query = "UPDATE users SET backup_codes = %s WHERE id = %s"
        rds_db.execute_query(query, (json.dumps(backup_codes_data), internal_user_id))
        
        logger.info(f"Backup codes regenerated for user: {internal_user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Backup codes regenerated successfully',
            'data': {
                'backupCodes': backup_codes
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error regenerating backup codes: {e}")
        return jsonify({'error': 'Failed to regenerate backup codes'}), 500


@auth_2fa_bp.route('/logout', methods=['POST'])
@add_security_headers()
@require_auth
def logout_with_2fa_tracking():
    """
    Logout and track for 2FA requirement on next login
    """
    try:
        user_id = request.headers.get('X-User-ID')
        session_id = request.headers.get('X-Session-ID')
        
        # Try to get session_id from JSON body if not in header
        if not session_id:
            try:
                data = request.get_json(silent=True)
                if data:
                    session_id = data.get('session_id')
            except:
                pass
        
        # Get user's internal ID
        user = rds_db.execute_query(
            'SELECT id FROM users WHERE firebase_uid = %s',
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        internal_user_id = user['id']
        
        # Track logout
        if session_id:
            enhanced_2fa_service.track_logout(internal_user_id, session_id)
        
        logger.info(f"User logged out: {internal_user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return jsonify({'error': 'Failed to logout'}), 500
