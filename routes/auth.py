from flask import Blueprint, request, jsonify
import uuid
from datetime import datetime

from config.database import db
from middleware.validation import validate_json, add_security_headers, RequestValidator

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/verify', methods=['POST'])
@add_security_headers()
@validate_json('email')
def verify_user():
    """Verify user and create/update user record - supports both Firebase and OAuth2"""
    try:
        data = request.get_json()
        
        email = RequestValidator.sanitize_string(data['email'], 255)
        name = RequestValidator.sanitize_string(data.get('name', ''), 255) or email.split('@')[0]
        
        # Validate email format
        if not RequestValidator.validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Determine authentication method
        firebase_uid = data.get('firebase_uid')
        google_oauth_id = data.get('google_oauth_id')
        auth_provider = 'firebase' if firebase_uid else 'google_oauth'
        
        # Validate that at least one auth method is provided
        if not firebase_uid and not google_oauth_id:
            return jsonify({'error': 'Either firebase_uid or google_oauth_id is required'}), 400
        
        # Check if user already exists by email or auth identifiers
        check_query = """
        SELECT * FROM users 
        WHERE email = %s OR firebase_uid = %s OR google_oauth_id = %s
        """
        existing_user = db.execute_query(check_query, (email, firebase_uid or '', google_oauth_id or ''))
        
        if existing_user:
            # Update existing user
            user = existing_user[0]
            update_query = """
            UPDATE users 
            SET email = %s, name = %s, auth_provider = %s, updated_at = %s
            """
            params = [email, name or user['name'], auth_provider, datetime.utcnow()]
            
            # Update auth-specific fields
            if firebase_uid and auth_provider == 'firebase':
                update_query += ", firebase_uid = %s"
                params.append(firebase_uid)
            elif google_oauth_id and auth_provider == 'google_oauth':
                update_query += ", google_oauth_id = %s"
                params.append(google_oauth_id)
                
            # Add Google OAuth tokens if provided
            if data.get('google_access_token'):
                update_query += ", google_access_token = %s"
                params.append(data['google_access_token'])
            if data.get('google_refresh_token'):
                update_query += ", google_refresh_token = %s"
                params.append(data['google_refresh_token'])
            if data.get('google_token_expires_at'):
                update_query += ", google_token_expires_at = %s"
                params.append(data['google_token_expires_at'])
            if data.get('google_calendar_enabled') is not None:
                update_query += ", google_calendar_enabled = %s"
                params.append(data['google_calendar_enabled'])
            
            update_query += " WHERE id = %s"
            params.append(user['id'])
            
            db.execute_query(update_query, params)
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user['id'],
                    'firebase_uid': firebase_uid or user.get('firebase_uid'),
                    'google_oauth_id': google_oauth_id or user.get('google_oauth_id'),
                    'email': email,
                    'name': name or user['name'],
                    'auth_provider': auth_provider,
                    'google_calendar_enabled': user.get('google_calendar_enabled', False),
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None
                },
                'is_new_user': False
            }), 200
        else:
            # Create new user
            user_id = str(uuid.uuid4())
            insert_query = """
            INSERT INTO users (id, firebase_uid, google_oauth_id, email, name, auth_provider, 
                             google_access_token, google_refresh_token, google_token_expires_at, 
                             google_calendar_enabled, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            db.execute_query(insert_query, (
                user_id,
                firebase_uid,
                google_oauth_id,
                email,
                name or email.split('@')[0],
                auth_provider,
                data.get('google_access_token'),
                data.get('google_refresh_token'),
                data.get('google_token_expires_at'),
                data.get('google_calendar_enabled', False),
                datetime.utcnow(),
                datetime.utcnow()
            ))
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user_id,
                    'firebase_uid': firebase_uid,
                    'google_oauth_id': google_oauth_id,
                    'email': email,
                    'name': name or email.split('@')[0],
                    'auth_provider': auth_provider,
                    'google_calendar_enabled': data.get('google_calendar_enabled', False),
                    'created_at': datetime.utcnow().isoformat()
                },
                'is_new_user': True
            }), 201
        
    except Exception as e:
        return jsonify({'error': f'User verification failed: {str(e)}'}), 500

@auth_bp.route('/user/<firebase_uid>', methods=['GET'])
def get_user(firebase_uid):
    """Get user by Firebase UID - Always returns latest data from PostgreSQL (source of truth)"""
    try:
        # Validate firebase_uid parameter
        if not firebase_uid or not firebase_uid.strip():
            print(f"❌ Invalid firebase_uid parameter: '{firebase_uid}'")
            return jsonify({
                'error': 'Invalid firebase_uid parameter',
                'message': 'firebase_uid is required and cannot be empty'
            }), 400
        
        print(f"🔍 Getting user data for firebase_uid: {firebase_uid}")
        
        # Query database for latest user data (PostgreSQL is source of truth)
        query = """
        SELECT id, firebase_uid, email, name, email_notifications, in_app_notifications, 
               created_at, updated_at 
        FROM users 
        WHERE firebase_uid = %s
        """
        
        try:
            result = db.execute_query(query, (firebase_uid,))
            print(f"🔍 Database query result: {len(result) if result else 0} users found")
        except Exception as db_error:
            print(f"❌ Database query failed: {db_error}")
            return jsonify({
                'error': 'Database query failed',
                'message': 'Unable to retrieve user from database',
                'details': str(db_error)
            }), 500
        
        if not result or len(result) == 0:
            print(f"❌ User not found with firebase_uid: {firebase_uid}")
            return jsonify({
                'error': 'User not found',
                'message': f'No user found with firebase_uid: {firebase_uid}. Please verify user first.',
                'firebase_uid': firebase_uid,
                'action_required': 'verify_user'
            }), 404
        
        user = result[0]
        
        return jsonify({
            'success': True,
            'source': 'postgresql_database',
            'user': {
                'id': str(user['id']),
                'firebase_uid': user.get('firebase_uid'),
                'google_oauth_id': user.get('google_oauth_id'),
                'email': user['email'],
                'name': user['name'],  # This is the latest value from DB
                'auth_provider': user.get('auth_provider', 'firebase'),
                'email_notifications': bool(user['email_notifications']),
                'in_app_notifications': bool(user['in_app_notifications']),
                'google_calendar_enabled': bool(user.get('google_calendar_enabled', False)),
                'created_at': user['created_at'].isoformat() if user['created_at'] else None,
                'updated_at': user['updated_at'].isoformat() if user['updated_at'] else None
            }
        }), 200
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_user: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred while retrieving user data',
            'details': str(e)
        }), 500

@auth_bp.route('/user/<firebase_uid>', methods=['PUT'])
def update_user(firebase_uid):
    """Update user profile"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Check if user exists
        check_query = "SELECT id FROM users WHERE firebase_uid = %s"
        check_result = db.execute_query(check_query, (firebase_uid,))
        
        if not check_result:
            return jsonify({'error': 'User not found'}), 404
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        if 'name' in data:
            update_fields.append("name = %s")
            params.append(data['name'])
        
        if 'email' in data:
            update_fields.append("email = %s")
            params.append(data['email'])
        
        if not update_fields:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        # Add updated_at
        update_fields.append("updated_at = %s")
        params.append(datetime.utcnow())
        
        # Add firebase_uid for WHERE clause
        params.append(firebase_uid)
        
        # Execute update
        update_query = f"""
        UPDATE users 
        SET {', '.join(update_fields)}
        WHERE firebase_uid = %s
        """
        
        # Execute database update
        try:
            updated_count = db.execute_query(update_query, params)
        except Exception as db_error:
            return jsonify({'error': f'Failed to update user in database: {str(db_error)}'}), 500
        
        if updated_count > 0:
            # Get updated user data from database (single source of truth)
            get_query = "SELECT * FROM users WHERE firebase_uid = %s"
            updated_user_result = db.execute_query(get_query, (firebase_uid,))
            updated_user = updated_user_result[0]
            
            return jsonify({
                'success': True,
                'message': 'User updated successfully in database',
                'user': {
                    'id': str(updated_user['id']),
                    'firebase_uid': updated_user['firebase_uid'],
                    'email': updated_user['email'],
                    'name': updated_user['name'],
                    'created_at': updated_user['created_at'].isoformat() if updated_user['created_at'] else None,
                    'updated_at': updated_user['updated_at'].isoformat() if updated_user['updated_at'] else None
                }
            }), 200
        else:
            return jsonify({'error': 'Failed to update user'}), 500
        
    except Exception as e:
        return jsonify({'error': f'Failed to update user: {str(e)}'}), 500

@auth_bp.route('/user/<firebase_uid>/notifications', methods=['PUT', 'OPTIONS'])
def update_notification_preferences(firebase_uid):
    """Update user notification preferences"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = jsonify()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
        return response
    
    try:
        # Validate firebase_uid parameter
        if not firebase_uid or not firebase_uid.strip():
            return jsonify({
                'error': 'Invalid firebase_uid parameter',
                'message': 'firebase_uid is required and cannot be empty'
            }), 400
        
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Invalid request data',
                'message': 'Request body must contain JSON data'
            }), 400
        
        # Check if user exists with proper error handling
        check_query = "SELECT id, name, email FROM users WHERE firebase_uid = %s"
        
        try:
            check_result = db.execute_query(check_query, (firebase_uid,))
        except Exception as db_error:
            return jsonify({
                'error': 'Database query failed',
                'message': 'Unable to verify user existence',
                'details': str(db_error)
            }), 500
        
        if not check_result or len(check_result) == 0:
            print(f"❌ User not found for notification update with firebase_uid: {firebase_uid}")
            return jsonify({
                'error': 'User not found',
                'message': f'No user found with firebase_uid: {firebase_uid}',
                'firebase_uid': firebase_uid
            }), 404
        
        # Validate notification preferences
        email_notifications = data.get('email_notifications')
        in_app_notifications = data.get('in_app_notifications')
        
        if email_notifications is None or in_app_notifications is None:
            return jsonify({
                'error': 'Missing notification preferences',
                'message': 'Both email_notifications and in_app_notifications are required',
                'received': data
            }), 400
        
        # Ensure boolean values
        email_notifications = bool(email_notifications)
        in_app_notifications = bool(in_app_notifications)
        
        # Update user preferences with proper error handling
        update_query = """
        UPDATE users 
        SET email_notifications = %s, in_app_notifications = %s, updated_at = %s 
        WHERE firebase_uid = %s
        """
        
        try:
            db.execute_query(update_query, (
                email_notifications, 
                in_app_notifications, 
                datetime.utcnow(), 
                firebase_uid
            ))
        except Exception as db_error:
            return jsonify({
                'error': 'Database update failed',
                'message': 'Unable to update notification preferences',
                'details': str(db_error)
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Notification preferences updated successfully',
            'preferences': {
                'email_notifications': email_notifications,
                'in_app_notifications': in_app_notifications
            },
            'user_info': {
                'id': str(check_result[0]['id']),
                'name': check_result[0]['name'],
                'email': check_result[0]['email']
            }
        }), 200
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error in update_notification_preferences: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred while updating notification preferences',
            'details': str(e)
        }), 500

@auth_bp.route('/user/<firebase_uid>/notifications', methods=['GET', 'OPTIONS'])
def get_notification_preferences(firebase_uid):
    """Get user notification preferences"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = jsonify()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response
    
    try:
        # Validate firebase_uid parameter
        if not firebase_uid or not firebase_uid.strip():
            print(f"❌ Invalid firebase_uid parameter: '{firebase_uid}'")
            return jsonify({
                'error': 'Invalid firebase_uid parameter',
                'message': 'firebase_uid is required and cannot be empty'
            }), 400
        
        print(f"🔍 Getting notification preferences for firebase_uid: {firebase_uid}")
        
        # Check if database is available
        try:
            db.test_connection()
            print("✅ Database connection test passed")
        except Exception as db_error:
            print(f"❌ Database connection failed: {db_error}")
            # Return default preferences when database is unavailable
            return jsonify({
                'success': True,
                'preferences': {
                    'email_notifications': True,
                    'in_app_notifications': True
                },
                'user_info': {
                    'id': 'offline',
                    'name': 'User',
                    'email': 'user@example.com'
                },
                'message': 'Using default preferences (database offline)'
            }), 200
        
        # Get user preferences from database with proper error handling
        user_query = """
        SELECT id, email_notifications, in_app_notifications, name, email
        FROM users 
        WHERE firebase_uid = %s
        """
        
        try:
            user_result = db.execute_query(user_query, (firebase_uid,))
            print(f"🔍 Database query result: {len(user_result) if user_result else 0} users found")
        except Exception as db_error:
            print(f"❌ Database query failed: {db_error}")
            return jsonify({
                'error': 'Database query failed',
                'message': 'Unable to query user preferences from database',
                'details': str(db_error)
            }), 500
        
        if not user_result or len(user_result) == 0:
            print(f"❌ User not found with firebase_uid: {firebase_uid}")
            # Instead of returning 404, return default preferences to prevent frontend errors
            return jsonify({
                'success': True,
                'preferences': {
                    'email_notifications': True,
                    'in_app_notifications': True
                },
                'user_info': {
                    'id': 'new_user',
                    'name': 'User',
                    'email': 'user@example.com'
                },
                'message': 'User not found, using default preferences'
            }), 200
        
        user_data = user_result[0]
        
        # Return preferences with additional user info
        return jsonify({
            'success': True,
            'preferences': {
                'email_notifications': bool(user_data['email_notifications']),
                'in_app_notifications': bool(user_data['in_app_notifications'])
            },
            'user_info': {
                'id': str(user_data['id']),
                'name': user_data['name'],
                'email': user_data['email']
            }
        }), 200
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_notification_preferences: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred while fetching notification preferences',
            'details': str(e)
        }), 500

@auth_bp.route('/user/<firebase_uid>', methods=['DELETE', 'OPTIONS'])
def delete_user_account(firebase_uid):
    """Delete user account and all associated data"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = jsonify()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'DELETE,OPTIONS')
        return response
    
    try:
        data = request.get_json()
        confirmation = data.get('confirmation') if data else None
        
        if confirmation != 'DELETE_MY_ACCOUNT':
            return jsonify({'error': 'Account deletion requires confirmation'}), 400
        
        # Check if user exists
        check_query = "SELECT id FROM users WHERE firebase_uid = %s"
        check_result = db.execute_query(check_query, (firebase_uid,))
        
        if not check_result:
            return jsonify({'error': 'User not found'}), 404
        
        user_id = check_result[0]['id']
        
        # Delete user data in order (foreign key constraints)
        try:
            # Delete tasks
            db.execute_query("DELETE FROM tasks WHERE user_id = %s", (user_id,))
            
            # Delete timeline entries for user's meetings
            db.execute_query("""
                DELETE FROM timeline 
                WHERE meeting_id IN (
                    SELECT id FROM meetings WHERE user_id = %s
                )
            """, (user_id,))
            
            # Delete processing status for user's meetings
            db.execute_query("""
                DELETE FROM processing_status 
                WHERE meeting_id IN (
                    SELECT id FROM meetings WHERE user_id = %s
                )
            """, (user_id,))
            
            # Delete meetings
            db.execute_query("DELETE FROM meetings WHERE user_id = %s", (user_id,))
            
            # Finally, delete user
            db.execute_query("DELETE FROM users WHERE firebase_uid = %s", (firebase_uid,))
            
            return jsonify({
                'success': True,
                'message': 'Account deleted successfully'
            }), 200
            
        except Exception as db_error:
            return jsonify({'error': f'Failed to delete account data: {str(db_error)}'}), 500
        
    except Exception as e:
        return jsonify({'error': f'Failed to delete account: {str(e)}'}), 500

@auth_bp.route('/user/<firebase_uid>/google-auth', methods=['PUT'])
def link_google_account(firebase_uid):
    """Link Google account and store OAuth tokens"""
    try:
        data = request.get_json()
        if not data or 'access_token' not in data:
            return jsonify({'error': 'Access token is required'}), 400

        access_token = data['access_token']
        refresh_token = data.get('refresh_token')  # Optional

        # Check if user exists
        check_query = "SELECT id FROM users WHERE firebase_uid = %s"
        check_result = db.execute_query(check_query, (firebase_uid,))

        if not check_result:
            return jsonify({'error': 'User not found'}), 404

        # Update user with Google tokens
        update_query = """
        UPDATE users
        SET google_access_token = %s, google_refresh_token = %s, updated_at = %s
        WHERE firebase_uid = %s
        """

        db.execute_query(update_query, (access_token, refresh_token, datetime.utcnow(), firebase_uid))

        return jsonify({
            'success': True,
            'message': 'Google account linked successfully'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to link Google account: {str(e)}'}), 500

@auth_bp.route('/google-oauth', methods=['POST'])
@add_security_headers()
@validate_json('access_token', 'email')
def verify_google_oauth():
    """Verify Google OAuth user and create/update user record"""
    try:
        data = request.get_json()
        
        access_token = data['access_token']
        email = RequestValidator.sanitize_string(data['email'], 255)
        name = RequestValidator.sanitize_string(data.get('name', ''), 255) or email.split('@')[0]
        google_oauth_id = data.get('google_oauth_id', data.get('id'))
        
        # Validate email format
        if not RequestValidator.validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Check if user already exists
        check_query = """
        SELECT * FROM users 
        WHERE email = %s OR google_oauth_id = %s
        """
        existing_user = db.execute_query(check_query, (email, google_oauth_id or ''))
        
        if existing_user:
            # Update existing user with Google OAuth info
            user = existing_user[0]
            update_query = """
            UPDATE users 
            SET email = %s, name = %s, auth_provider = 'google_oauth', 
                google_oauth_id = %s, google_access_token = %s, 
                google_refresh_token = %s, google_token_expires_at = %s,
                google_calendar_enabled = %s, updated_at = %s
            WHERE id = %s
            """
            
            db.execute_query(update_query, (
                email, name or user['name'], google_oauth_id, access_token,
                data.get('refresh_token'), data.get('expires_at'),
                data.get('google_calendar_enabled', True),
                datetime.utcnow(), user['id']
            ))
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user['id'],
                    'firebase_uid': user.get('firebase_uid'),
                    'google_oauth_id': google_oauth_id,
                    'email': email,
                    'name': name or user['name'],
                    'auth_provider': 'google_oauth',
                    'google_calendar_enabled': data.get('google_calendar_enabled', True),
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None
                },
                'is_new_user': False
            }), 200
        else:
            # Create new user with Google OAuth
            user_id = str(uuid.uuid4())
            insert_query = """
            INSERT INTO users (id, google_oauth_id, email, name, auth_provider, 
                             google_access_token, google_refresh_token, google_token_expires_at, 
                             google_calendar_enabled, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            db.execute_query(insert_query, (
                user_id, google_oauth_id, email, name or email.split('@')[0], 'google_oauth',
                access_token, data.get('refresh_token'), data.get('expires_at'),
                data.get('google_calendar_enabled', True),
                datetime.utcnow(), datetime.utcnow()
            ))
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user_id,
                    'firebase_uid': None,
                    'google_oauth_id': google_oauth_id,
                    'email': email,
                    'name': name or email.split('@')[0],
                    'auth_provider': 'google_oauth',
                    'google_calendar_enabled': data.get('google_calendar_enabled', True),
                    'created_at': datetime.utcnow().isoformat()
                },
                'is_new_user': True
            }), 201
        
    except Exception as e:
        return jsonify({'error': f'Google OAuth verification failed: {str(e)}'}), 500