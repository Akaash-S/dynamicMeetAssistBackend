from flask import Blueprint, request, jsonify
from datetime import datetime

from config.database import db
from middleware.validation import add_security_headers

meetings_bp = Blueprint('meetings', __name__)

# Test and debug endpoints (must be before parameterized routes)
@meetings_bp.route('/test', methods=['GET'])
def test_meetings_bp():
    """Test endpoint to verify meetings blueprint is working"""
    return jsonify({'message': 'Meetings blueprint is working!', 'timestamp': datetime.utcnow().isoformat()}), 200

@meetings_bp.route('/debug', methods=['GET'])
def debug_meetings_bp():
    """Debug endpoint to check request details"""
    return jsonify({
        'message': 'Debug endpoint working',
        'request_url': request.url,
        'request_method': request.method,
        'request_headers': dict(request.headers),
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@meetings_bp.route('/timeline-test', methods=['GET'])
def timeline_test_simple():
    """Simple test for timeline endpoint"""
    return jsonify({
        'message': 'Timeline test endpoint working',
        'blueprint_name': meetings_bp.name,
        'url_prefix': meetings_bp.url_prefix,
        'timestamp': datetime.utcnow().isoformat()
    }), 200



@meetings_bp.route('/routes', methods=['GET'])
def list_routes():
    """List all available routes in this blueprint"""
    routes = []
    for rule in meetings_bp.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': str(rule)
        })
    
    return jsonify({
        'message': 'Available routes',
        'blueprint': meetings_bp.name,
        'url_prefix': meetings_bp.url_prefix,
        'routes': routes,
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@meetings_bp.route('', methods=['GET'])
def get_meetings():
    """Get all meetings for a user"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Get meetings with pagination
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        offset = (page - 1) * limit
        
        query = """
        SELECT m.*, 
               COUNT(t.id) as task_count,
               COUNT(tl.id) as timeline_count
        FROM meetings m
        LEFT JOIN tasks t ON m.id = t.meeting_id
        LEFT JOIN timeline tl ON m.id = tl.meeting_id
        WHERE m.user_id = %s
        GROUP BY m.id
        ORDER BY m.created_at DESC
        LIMIT %s OFFSET %s
        """
        
        meetings = db.execute_query(query, (user_id, limit, offset))
        print(f"📊 Found {len(meetings) if meetings else 0} meetings for user {user_id}")
        
        # Debug: Print meeting IDs to check format
        if meetings:
            for meeting in meetings:
                print(f"📊 Meeting ID: {meeting['id']} (type: {type(meeting['id'])})")
        
        # Get total count
        count_query = """
        SELECT COUNT(*) as total 
        FROM meetings m
        WHERE m.user_id = %s
        """
        count_result = db.execute_query(count_query, (user_id,))
        total_count = count_result[0]['total'] if count_result else 0
        
        # Format response
        formatted_meetings = []
        for meeting in meetings:
            formatted_meetings.append({
                'id': meeting['id'],
                'title': meeting['title'],
                'status': meeting['status'],
                'duration': meeting['duration'],
                'file_size': meeting['file_size'],
                'task_count': meeting['task_count'],
                'timeline_count': meeting['timeline_count'],
                'created_at': meeting['created_at'].isoformat() if meeting['created_at'] else None,
                'updated_at': meeting['updated_at'].isoformat() if meeting['updated_at'] else None
            })
        
        return jsonify({
            'meetings': formatted_meetings,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get meetings: {str(e)}'}), 500

@meetings_bp.route('/<meeting_id>/timeline', methods=['GET', 'OPTIONS'])
@add_security_headers()
def get_meeting_timeline(meeting_id):
    """Get timeline for a specific meeting"""
    print(f"[DEBUG] Timeline endpoint called with meeting_id: {meeting_id}")
    print(f"[DEBUG] Request method: {request.method}")
    print(f"[DEBUG] Request URL: {request.url}")
    print(f"[DEBUG] Request headers: {dict(request.headers)}")
    print(f"[DEBUG] Blueprint name: {meetings_bp.name}")
    print(f"[DEBUG] Blueprint URL prefix: {meetings_bp.url_prefix}")
    print(f"[DEBUG] Full route pattern: /api/meetings/<meeting_id>/timeline")
    
    try:
        # Handle preflight requests
        if request.method == 'OPTIONS':
            from flask import make_response
            response = make_response()
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
            return response
        
        # Validate meeting_id format
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, meeting_id, re.IGNORECASE):
            print(f"[ERROR] Invalid meeting_id format: {meeting_id}")
            return jsonify({'error': f'Invalid meeting ID format: {meeting_id}'}), 400
        
        # Get timeline entries for the meeting
        query = """
        SELECT id, meeting_id, timestamp_minutes, event_type, title, content, 
               participants, created_at
        FROM timeline 
        WHERE meeting_id = %s 
        ORDER BY timestamp_minutes ASC
        """
        
        result = db.execute_query(query, (meeting_id,))
        
        if result is None:
            return jsonify({'error': 'Failed to fetch timeline'}), 500
        
        timeline_entries = []
        for row in result:
            # Convert timestamp_minutes to MM:SS format
            minutes = int(row['timestamp_minutes']) if row['timestamp_minutes'] else 0
            seconds = int((row['timestamp_minutes'] - minutes) * 60) if row['timestamp_minutes'] else 0
            timestamp_str = f"{minutes:02d}:{seconds:02d}"
            
            timeline_entries.append({
                'id': row['id'],
                'meeting_id': row['meeting_id'],
                'timestamp': timestamp_str,
                'timestamp_minutes': row['timestamp_minutes'],
                'event_type': row['event_type'],
                'title': row['title'],
                'content': row['content'],
                'participants': row['participants'] or [],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            })
        
        print(f"[SUCCESS] Timeline fetched successfully: {len(timeline_entries)} entries")
        
        return jsonify({
            'meeting_id': meeting_id,
            'timeline': timeline_entries,
            'total_entries': len(timeline_entries)
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Timeline error: {str(e)}")
        return jsonify({'error': f'Failed to get timeline: {str(e)}'}), 500

@meetings_bp.route('/<meeting_id>', methods=['GET'])
def get_meeting(meeting_id):
    """Get specific meeting details"""
    try:
        query = """
        SELECT m.*, 
               COUNT(t.id) as task_count,
               COUNT(tl.id) as timeline_count
        FROM meetings m
        LEFT JOIN tasks t ON m.id = t.meeting_id
        LEFT JOIN timeline tl ON m.id = tl.meeting_id
        WHERE m.id = %s
        GROUP BY m.id
        """
        
        result = db.execute_query(query, (meeting_id,))
        
        if not result:
            return jsonify({'error': 'Meeting not found'}), 404
        
        meeting = result[0]
        
        return jsonify({
            'id': meeting['id'],
            'title': meeting['title'],
            'status': meeting['status'],
            'transcript': meeting['transcript'],
            'summary': meeting['summary'],
            'duration': meeting['duration'],
            'file_size': meeting['file_size'],
            'audio_url': meeting['audio_url'],
            'task_count': meeting['task_count'],
            'timeline_count': meeting['timeline_count'],
            'created_at': meeting['created_at'].isoformat() if meeting['created_at'] else None,
            'updated_at': meeting['updated_at'].isoformat() if meeting['updated_at'] else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get meeting: {str(e)}'}), 500


@meetings_bp.route('/<meeting_id>/summary', methods=['GET'])
def get_meeting_summary(meeting_id):
    """Get summary for a specific meeting"""
    try:
        query = "SELECT summary, title, created_at FROM meetings WHERE id = %s"
        result = db.execute_query(query, (meeting_id,))
        
        if not result:
            return jsonify({'error': 'Meeting not found'}), 404
        
        meeting = result[0]
        
        # Parse summary if it's JSON string
        summary = meeting['summary']
        if summary:
            try:
                import json
                if isinstance(summary, str):
                    summary = json.loads(summary)
            except (json.JSONDecodeError, TypeError):
                # If it's not valid JSON, treat as plain text
                summary = {'text': summary}
        
        return jsonify({
            'meeting_id': meeting_id,
            'title': meeting['title'],
            'summary': summary,
            'created_at': meeting['created_at'].isoformat() if meeting['created_at'] else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get summary: {str(e)}'}), 500

@meetings_bp.route('/<meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    """Delete a meeting and all related data"""
    try:
        # Check if meeting exists
        meeting_query = "SELECT audio_url FROM meetings WHERE id = %s"
        meeting_result = db.execute_query(meeting_query, (meeting_id,))
        
        if not meeting_result:
            return jsonify({'error': 'Meeting not found'}), 404
        
        # Delete from database (cascading deletes will handle related tables)
        delete_query = "DELETE FROM meetings WHERE id = %s"
        deleted_count = db.execute_query(delete_query, (meeting_id,))
        
        if deleted_count > 0:
            # TODO: Delete audio file from storage
            # audio_url = meeting_result[0]['audio_url']
            # storage.delete_file(audio_url)
            
            return jsonify({
                'success': True,
                'message': 'Meeting deleted successfully'
            }), 200
        else:
            return jsonify({'error': 'Failed to delete meeting'}), 500
        
    except Exception as e:
        return jsonify({'error': f'Failed to delete meeting: {str(e)}'}), 500

@meetings_bp.route('/<meeting_id>/reprocess', methods=['POST'])
def reprocess_meeting(meeting_id):
    """Reprocess a meeting (re-run AI analysis)"""
    try:
        # Check if meeting exists and has transcript
        meeting_query = "SELECT transcript, title, audio_url FROM meetings WHERE id = %s"
        meeting_result = db.execute_query(meeting_query, (meeting_id,))
        
        if not meeting_result:
            return jsonify({'error': 'Meeting not found'}), 404
        
        meeting = meeting_result[0]
        
        if not meeting['transcript']:
            return jsonify({'error': 'Meeting has no transcript to reprocess'}), 400
        
        # Update meeting status
        update_query = "UPDATE meetings SET status = %s, updated_at = %s WHERE id = %s"
        db.execute_query(update_query, ('processing', datetime.utcnow(), meeting_id))
        
        # Clear existing timeline and tasks
        db.execute_query("DELETE FROM timeline WHERE meeting_id = %s", (meeting_id,))
        db.execute_query("DELETE FROM tasks WHERE meeting_id = %s", (meeting_id,))
        
        # Reset processing status
        db.execute_query("DELETE FROM processing_status WHERE meeting_id = %s", (meeting_id,))
        
        # Start reprocessing (this would typically be done asynchronously)
        # For now, return success message
        return jsonify({
            'success': True,
            'message': 'Meeting reprocessing started',
            'meeting_id': meeting_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to reprocess meeting: {str(e)}'}), 500

@meetings_bp.route('/stats', methods=['GET'])
def get_meeting_stats():
    """Get meeting statistics for a user"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Get various statistics
        stats = {}
        
        # Total meetings
        total_query = """
        SELECT COUNT(*) as count
        FROM meetings m
        WHERE m.user_id = %s
        """
        total_result = db.execute_query(total_query, (user_id,))
        stats['total_meetings'] = total_result[0]['count'] if total_result else 0
        
        # Meetings by status
        status_query = """
        SELECT status, COUNT(*) as count
        FROM meetings m
        WHERE m.user_id = %s 
        GROUP BY status
        """
        status_result = db.execute_query(status_query, (user_id,))
        stats['by_status'] = {row['status']: row['count'] for row in status_result}
        
        # Total tasks
        tasks_query = """
        SELECT COUNT(*) as count
        FROM tasks t
        JOIN meetings m ON t.meeting_id = m.id 
        WHERE m.user_id = %s
        """
        tasks_result = db.execute_query(tasks_query, (user_id,))
        stats['total_tasks'] = tasks_result[0]['count'] if tasks_result else 0
        
        # Tasks by status
        task_status_query = """
        SELECT t.status, COUNT(*) as count
        FROM tasks t
        JOIN meetings m ON t.meeting_id = m.id 
        WHERE m.user_id = %s 
        GROUP BY t.status
        """
        task_status_result = db.execute_query(task_status_query, (user_id,))
        stats['tasks_by_status'] = {row['status']: row['count'] for row in task_status_result}
        
        # Recent activity (last 7 days)
        recent_query = """
        SELECT COUNT(*) as count
        FROM meetings m
        WHERE m.user_id = %s AND m.created_at > NOW() - INTERVAL '7 days'
        """
        recent_result = db.execute_query(recent_query, (user_id,))
        stats['recent_meetings'] = recent_result[0]['count'] if recent_result else 0
        
        # Total duration
        duration_query = """
        SELECT SUM(duration) as total_duration
        FROM meetings m
        WHERE m.user_id = %s AND m.duration IS NOT NULL
        """
        duration_result = db.execute_query(duration_query, (user_id,))
        total_duration = duration_result[0]['total_duration'] if duration_result and duration_result[0]['total_duration'] else 0
        stats['total_duration_minutes'] = int(total_duration)
        stats['total_duration_hours'] = round(total_duration / 60, 2)
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500

