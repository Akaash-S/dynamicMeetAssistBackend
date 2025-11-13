"""
Data Export Routes
Handles user data export requests
"""

from flask import Blueprint, request, jsonify, send_file
from functools import wraps
import logging
import json
import os
from datetime import datetime, timedelta
import uuid
from services.email_service import email_service
# Removed: # Removed: from config.database import get_db_connection

logger = logging.getLogger(__name__)

data_export_bp = Blueprint('data_export', __name__)

# Directory for temporary export files
EXPORT_DIR = os.path.join(os.path.dirname(__file__), '..', 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


@data_export_bp.route('/export-data', methods=['POST'])
@require_auth
def request_data_export():
    """Request data export - generates export and sends email"""
    try:
        data = request.get_json()
        email = data.get('email')
        user_id = request.headers.get('X-User-ID')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Get user data from database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute('SELECT * FROM users WHERE firebase_uid = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Get meetings
        cursor.execute('''
            SELECT id, title, date, duration, transcription, summary, status
            FROM meetings 
            WHERE user_id = ?
            ORDER BY date DESC
        ''', (user['id'],))
        meetings = [dict(row) for row in cursor.fetchall()]
        
        # Get tasks
        cursor.execute('''
            SELECT id, title, description, status, priority, deadline, meeting_id
            FROM tasks 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user['id'],))
        tasks = [dict(row) for row in cursor.fetchall()]
        
        # Get timeline events
        cursor.execute('''
            SELECT id, meeting_id, timestamp, event_type, description, speaker
            FROM timeline_events 
            WHERE meeting_id IN (SELECT id FROM meetings WHERE user_id = ?)
            ORDER BY timestamp DESC
        ''', (user['id'],))
        timeline_events = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # Create export data
        export_data = {
            'export_info': {
                'generated_at': datetime.now().isoformat(),
                'user_id': user['firebase_uid'],
                'export_version': '1.0'
            },
            'user': {
                'name': user['name'],
                'email': user['email'],
                'auth_provider': user['auth_provider'],
                'created_at': user['created_at'],
                'two_factor_enabled': bool(user.get('two_factor_enabled', 0))
            },
            'meetings': meetings,
            'tasks': tasks,
            'timeline_events': timeline_events,
            'statistics': {
                'total_meetings': len(meetings),
                'total_tasks': len(tasks),
                'total_timeline_events': len(timeline_events)
            }
        }
        
        # Generate unique filename
        export_id = str(uuid.uuid4())
        filename = f"data_export_{user_id}_{export_id}.json"
        filepath = os.path.join(EXPORT_DIR, filename)
        
        # Save export file
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        # Generate download URL (adjust based on your deployment)
        base_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        download_url = f"{base_url}/api/download-export/{export_id}"
        
        # Send email with download link
        email_service.send_data_export_notification(
            email,
            user['name'],
            download_url,
            expires_in_hours=24
        )
        
        # Store export record in database (optional)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO data_exports (user_id, export_id, filename, created_at, expires_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, datetime('now', '+24 hours'))
        ''', (user['id'], export_id, filename))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Data export initiated. You will receive an email with the download link.'
        }), 200
    except Exception as e:
        logger.error(f"Error requesting data export: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@data_export_bp.route('/download-export/<export_id>', methods=['GET'])
def download_export(export_id):
    """Download export file"""
    try:
        # Get export info from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT filename, expires_at 
            FROM data_exports 
            WHERE export_id = ?
        ''', (export_id,))
        export = cursor.fetchone()
        conn.close()
        
        if not export:
            return jsonify({'error': 'Export not found'}), 404
        
        # Check if expired
        expires_at = datetime.fromisoformat(export['expires_at'])
        if datetime.now() > expires_at:
            return jsonify({'error': 'Export link has expired'}), 410
        
        # Send file
        filepath = os.path.join(EXPORT_DIR, export['filename'])
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Export file not found'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=export['filename'],
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error downloading export: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@data_export_bp.route('/cleanup-exports', methods=['POST'])
def cleanup_expired_exports():
    """Cleanup expired export files (should be called periodically)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get expired exports
        cursor.execute('''
            SELECT filename 
            FROM data_exports 
            WHERE expires_at < datetime('now')
        ''')
        expired_exports = cursor.fetchall()
        
        # Delete files
        for export in expired_exports:
            filepath = os.path.join(EXPORT_DIR, export['filename'])
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Delete database records
        cursor.execute('''
            DELETE FROM data_exports 
            WHERE expires_at < datetime('now')
        ''')
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'deleted_count': len(expired_exports)
        }), 200
    except Exception as e:
        logger.error(f"Error cleaning up exports: {e}")
        return jsonify({'error': 'Internal server error'}), 500
