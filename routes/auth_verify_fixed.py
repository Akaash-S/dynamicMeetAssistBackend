"""
FIXED Authentication Verify Route
Complete rewrite with proper error handling
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
import traceback

from config.aws_rds_database import rds_db
from middleware.validation import add_security_headers, validate_json, RequestValidator

auth_verify_bp = Blueprint('auth_verify_fixed', __name__)

@auth_verify_bp.route('/verify', methods=['POST', 'OPTIONS'])
@add_security_headers()
def verify_user_fixed():
    """
    FIXED: Verify user and create/update user record
    Handles Firebase Google Auth with proper error handling
    """
    # Handle OPTIONS for CORS
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    print('=' * 80)
    print('🔐 AUTH VERIFY ENDPOINT HIT')
    print('=' * 80)
    
    try:
        # Step 1: Get and validate request data
        data = request.get_json()
        if not data:
            print('❌ No JSON data received')
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        print(f'📥 Received data keys: {list(data.keys())}')
        
        # Step 2: Extract and validate required fields
        email = data.get('email')
        if not email:
            print('❌ Email is required')
            return jsonify({
                'success': False,
                'error': 'Email is required'
            }), 400
        
        # Sanitize and validate email
        email = RequestValidator.sanitize_string(email, 255)
        if not RequestValidator.validate_email(email):
            print(f'❌ Invalid email format: {email}')
            return jsonify({
                'success': False,
                'error': 'Invalid email format'
            }), 400
        
        # Extract other fields
        name = RequestValidator.sanitize_string(data.get('name', ''), 255) or email.split('@')[0]
        firebase_uid = data.get('firebase_uid')
        google_oauth_id = data.get('google_oauth_id')
        auth_provider = data.get('auth_provider', 'firebase')
        google_calendar_enabled = data.get('google_calendar_enabled', False)
        
        print(f'✅ Email: {email}')
        print(f'✅ Name: {name}')
        print(f'✅ Firebase UID: {firebase_uid[:10]}...' if firebase_uid else '❌ No Firebase UID')
        print(f'✅ Auth Provider: {auth_provider}')
        
        # Step 3: Validate authentication identifiers
        if not firebase_uid and not google_oauth_id:
            print('❌ No authentication identifier provided')
            return jsonify({
                'success': False,
                'error': 'Firebase UID or Google OAuth ID is required'
            }), 400
        
        # For Firebase Google OAuth, use firebase_uid as google_oauth_id
        if firebase_uid and auth_provider == 'google_oauth' and not google_oauth_id:
            google_oauth_id = firebase_uid
            print(f'✅ Using Firebase UID as Google OAuth ID')
        
        # Step 4: Check if user exists
        print('\n🔍 Checking if user exists...')
        existing_user = None
        
        try:
            # Build query to find user by email, firebase_uid, or google_oauth_id
            conditions = []
            params = []
            
            conditions.append("email = %s")
            params.append(email)
            
            if firebase_uid:
                conditions.append("firebase_uid = %s")
                params.append(firebase_uid)
            
            if google_oauth_id:
                conditions.append("google_oauth_id = %s")
                params.append(google_oauth_id)
            
            lookup_query = f"SELECT * FROM users WHERE {' OR '.join(conditions)} LIMIT 1"
            print(f'🔍 Lookup query: {lookup_query}')
            print(f'🔍 Params: {params}')
            
            result = rds_db.execute_query(lookup_query, tuple(params), fetch_all=True)
            
            if result and len(result) > 0:
                existing_user = result[0]
                print(f'✅ Found existing user: {email}')
                print(f'   User ID: {existing_user.get("id")}')
                print(f'   Role: {existing_user.get("role")}')
            else:
                print(f'ℹ️  No existing user found for: {email}')
                
        except Exception as lookup_error:
            print(f'❌ Error looking up user: {lookup_error}')
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': f'Database lookup failed: {str(lookup_error)}'
            }), 500
        
        # Step 5: Update existing user or create new user
        if existing_user:
            print('\n🔄 Updating existing user...')
            
            # Security check: prevent regular users from accessing admin accounts
            if existing_user.get('role') == 'admin':
                print('❌ Attempted to access admin account via regular login')
                return jsonify({
                    'success': False,
                    'error': 'Admin accounts must use admin login endpoint'
                }), 403
            
            try:
                # Build update query
                update_query = """
                UPDATE users 
                SET email = %s, 
                    name = %s, 
                    auth_provider = %s, 
                    updated_at = %s
                """
                params = [email, name, auth_provider, datetime.utcnow()]
                
                # Add optional fields
                if firebase_uid:
                    update_query += ", firebase_uid = %s"
                    params.append(firebase_uid)
                
                if google_oauth_id:
                    update_query += ", google_oauth_id = %s"
                    params.append(google_oauth_id)
                
                if data.get('google_access_token'):
                    update_query += ", google_access_token = %s"
                    params.append(data['google_access_token'])
                
                if data.get('google_refresh_token'):
                    update_query += ", google_refresh_token = %s"
                    params.append(data['google_refresh_token'])
                
                if data.get('google_token_expires_at'):
                    update_query += ", google_token_expires_at = %s"
                    params.append(data['google_token_expires_at'])
                
                update_query += ", google_calendar_enabled = %s"
                params.append(google_calendar_enabled)
                
                # Add WHERE clause
                update_query += " WHERE id = %s"
                user_id = existing_user.get('id')
                params.append(user_id)
                
                print(f'🔍 Update query prepared with {len(params)} parameters')
                
                # Execute update
                rds_db.execute_query(update_query, tuple(params))
                print('✅ User updated successfully')
                
                # Prepare response
                response_user = {
                    'id': str(user_id),
                    'firebase_uid': firebase_uid or existing_user.get('firebase_uid'),
                    'google_oauth_id': google_oauth_id or existing_user.get('google_oauth_id'),
                    'email': email,
                    'name': name,
                    'auth_provider': auth_provider,
                    'google_calendar_enabled': google_calendar_enabled,
                    'created_at': existing_user.get('created_at').isoformat() if existing_user.get('created_at') and hasattr(existing_user.get('created_at'), 'isoformat') else str(existing_user.get('created_at'))
                }
                
                print('✅ Response prepared successfully')
                print('=' * 80)
                
                return jsonify({
                    'success': True,
                    'user': response_user,
                    'is_new_user': False
                }), 200
                
            except Exception as update_error:
                print(f'❌ Error updating user: {update_error}')
                print(traceback.format_exc())
                return jsonify({
                    'success': False,
                    'error': f'Failed to update user: {str(update_error)}'
                }), 500
        
        else:
            print('\n➕ Creating new user...')
            
            try:
                # Generate new user ID
                user_id = str(uuid.uuid4())
                
                # Build insert query
                insert_query = """
                INSERT INTO users (
                    id, firebase_uid, google_oauth_id, email, name, auth_provider,
                    role, google_access_token, google_refresh_token, google_token_expires_at,
                    google_calendar_enabled, is_active, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                insert_params = (
                    user_id,
                    firebase_uid,
                    google_oauth_id,
                    email,
                    name,
                    auth_provider,
                    'user',  # Regular user, not admin
                    data.get('google_access_token'),
                    data.get('google_refresh_token'),
                    data.get('google_token_expires_at'),
                    google_calendar_enabled,
                    True,  # is_active
                    datetime.utcnow(),
                    datetime.utcnow()
                )
                
                print(f'🔍 Insert query prepared')
                
                # Execute insert
                rds_db.execute_query(insert_query, insert_params)
                print('✅ New user created successfully')
                
                # Prepare response
                response_user = {
                    'id': user_id,
                    'firebase_uid': firebase_uid,
                    'google_oauth_id': google_oauth_id,
                    'email': email,
                    'name': name,
                    'auth_provider': auth_provider,
                    'google_calendar_enabled': google_calendar_enabled,
                    'created_at': datetime.utcnow().isoformat()
                }
                
                print('✅ Response prepared successfully')
                print('=' * 80)
                
                return jsonify({
                    'success': True,
                    'user': response_user,
                    'is_new_user': True
                }), 201
                
            except Exception as create_error:
                print(f'❌ Error creating user: {create_error}')
                print(traceback.format_exc())
                return jsonify({
                    'success': False,
                    'error': f'Failed to create user: {str(create_error)}'
                }), 500
    
    except Exception as e:
        print(f'❌ UNEXPECTED ERROR in verify endpoint: {e}')
        print(traceback.format_exc())
        print('=' * 80)
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500
