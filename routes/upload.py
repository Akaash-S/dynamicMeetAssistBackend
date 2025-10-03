from flask import Blueprint, request, jsonify
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

from config.database import db
from config.storage import storage
from services.transcription import transcription_service
from services.ai_processor import ai_processor
from services.calendar_sync import calendar_service
from services.email_service import email_service
from middleware.validation import validate_file_upload, validate_user_id, add_security_headers

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'mp4', 'webm'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/audio', methods=['POST'])
@add_security_headers()
@validate_file_upload()
@validate_user_id()
def upload_audio():
    """Upload audio file and start processing pipeline"""
    try:
        file = request.files['audio']
        file_info = request.file_info  # Added by validation middleware
        user_id = request.validated_user_id  # Added by validation middleware
        meeting_title = request.form.get('title', 'Untitled Meeting')
        
        # Sanitize meeting title
        from middleware.validation import RequestValidator
        meeting_title = RequestValidator.sanitize_string(meeting_title, 255)
        
        # Generate unique filename using validated info
        unique_filename = f"{user_id}/{uuid.uuid4()}.{file_info['file_extension']}"
        
        # Read file data
        file_data = file.read()
        
        print(f"📁 Uploading file: {file_info['original_filename']} ({file_info['file_size']} bytes)")
        
        # Upload to Supabase Storage
        audio_url = storage.upload_file(
            file_path=unique_filename,
            file_data=file_data,
            content_type=f'audio/{file_info["file_extension"]}'
        )
        
        if not audio_url:
            return jsonify({'error': 'Failed to upload file to storage'}), 500
        
        print(f"☁️ File uploaded successfully: {audio_url}")
        
        # user_id is now the database user ID (not Firebase UID)
        print(f"📁 Creating meeting for database user ID: {user_id}")
        
        # Create meeting record in database
        meeting_id = str(uuid.uuid4())
        
        insert_meeting_query = """
        INSERT INTO meetings (id, user_id, title, audio_url, status, file_size, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        db.execute_query(insert_meeting_query, (
            meeting_id,
            user_id,  # Use database user ID directly
            meeting_title,
            audio_url,
            'processing',
            file_info['file_size'],
            datetime.utcnow()
        ))
        
        # Create initial processing status
        processing_steps = ['transcription', 'ai_analysis', 'task_extraction', 'calendar_sync']
        
        for step in processing_steps:
            insert_status_query = """
            INSERT INTO processing_status (meeting_id, step, status, progress)
            VALUES (%s, %s, %s, %s)
            """
            db.execute_query(insert_status_query, (meeting_id, step, 'pending', 0))
        
        print(f"💾 Meeting record created: {meeting_id}")
        print(f"📊 Meeting details: title='{meeting_title}', user_id='{user_id}', status='processing'")
        
        # Start processing pipeline asynchronously (in a real app, use Celery or similar)
        # For now, we'll process synchronously but return immediately
        try:
            process_meeting_pipeline(meeting_id, audio_url, meeting_title)
        except Exception as e:
            print(f"❌ Processing pipeline error: {e}")
            # Update meeting status to failed
            update_meeting_query = "UPDATE meetings SET status = %s WHERE id = %s"
            db.execute_query(update_meeting_query, ('failed', meeting_id))
        
        return jsonify({
            'success': True,
            'meeting_id': meeting_id,
            'audio_url': audio_url,
            'file_size': file_info['file_size'],
            'status': 'processing',
            'message': 'File uploaded successfully. Processing started.'
        }), 200
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

def process_meeting_pipeline(meeting_id: str, audio_url: str, meeting_title: str):
    """Process the complete meeting pipeline"""
    
    def update_processing_status(step: str, status: str, progress: int = 0, error: str = None):
        """Update processing status in database"""
        update_query = """
        UPDATE processing_status 
        SET status = %s, progress = %s, error_message = %s, 
            completed_at = CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END
        WHERE meeting_id = %s AND step = %s
        """
        db.execute_query(update_query, (status, progress, error, status, meeting_id, step))
    
    try:
        # Step 1: Transcription
        print(f"🎵 Starting transcription for meeting {meeting_id}")
        update_processing_status('transcription', 'processing', 10)
        
        transcription_result = transcription_service.transcribe_audio(audio_url)
        
        if not transcription_result['success']:
            update_processing_status('transcription', 'failed', 0, transcription_result['error'])
            raise Exception(f"Transcription failed: {transcription_result['error']}")
        
        transcript = transcription_result['transcript']
        duration = transcription_result.get('duration', 0)
        
        # Update meeting with transcript
        update_meeting_query = """
        UPDATE meetings SET transcript = %s, duration = %s, updated_at = %s 
        WHERE id = %s
        """
        db.execute_query(update_meeting_query, (transcript, duration, datetime.utcnow(), meeting_id))
        
        update_processing_status('transcription', 'completed', 100)
        print(f"✅ Transcription completed for meeting {meeting_id}")
        
        # Step 2: AI Analysis (Timeline)
        print(f"🤖 Starting AI analysis for meeting {meeting_id}")
        update_processing_status('ai_analysis', 'processing', 20)
        
        timeline_result = ai_processor.extract_timeline(transcript, duration)
        
        if not timeline_result['success']:
            update_processing_status('ai_analysis', 'failed', 0, timeline_result['error'])
            raise Exception(f"Timeline extraction failed: {timeline_result['error']}")
        
        timeline_data = timeline_result['data']
        
        # Save timeline entries to database
        if timeline_data.get('timeline'):
            for entry in timeline_data['timeline']:
                insert_timeline_query = """
                INSERT INTO timeline (meeting_id, timestamp_minutes, event_type, title, content, participants)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                db.execute_query(insert_timeline_query, (
                    meeting_id,
                    entry.get('timestamp_minutes', 0),
                    entry.get('event_type', 'discussion'),
                    entry.get('title', ''),
                    entry.get('content', ''),
                    entry.get('participants', [])
                ))
        
        update_processing_status('ai_analysis', 'completed', 100)
        print(f"✅ AI analysis completed for meeting {meeting_id}")
        
        # Step 3: Task Extraction
        print(f"🎯 Starting task extraction for meeting {meeting_id}")
        update_processing_status('task_extraction', 'processing', 30)
        
        tasks_result = ai_processor.extract_tasks(transcript, timeline_data)
        
        if not tasks_result['success']:
            update_processing_status('task_extraction', 'failed', 0, tasks_result['error'])
            raise Exception(f"Task extraction failed: {tasks_result['error']}")
        
        tasks_data = tasks_result['data']
        
        # Save tasks to database
        task_ids = []
        if tasks_data.get('tasks'):
            for task in tasks_data['tasks']:
                task_id = str(uuid.uuid4())
                task_ids.append(task_id)
                
                # Parse deadline
                deadline = None
                if task.get('deadline'):
                    try:
                        deadline = datetime.strptime(task['deadline'], '%Y-%m-%d')
                    except ValueError:
                        deadline = None
                
                insert_task_query = """
                INSERT INTO tasks (id, meeting_id, user_id, title, description, assigned_to, 
                                 deadline, priority, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                # Get user_id from meeting
                get_user_query = "SELECT user_id FROM meetings WHERE id = %s"
                user_result = db.execute_query(get_user_query, (meeting_id,))
                user_id = user_result[0]['user_id'] if user_result else None
                
                db.execute_query(insert_task_query, (
                    task_id,
                    meeting_id,
                    user_id,
                    task.get('title', ''),
                    task.get('description', ''),
                    task.get('assigned_to', ''),
                    deadline,
                    task.get('priority', 'medium'),
                    task.get('status', 'pending'),
                    datetime.utcnow()
                ))
        
        update_processing_status('task_extraction', 'completed', 100)
        print(f"✅ Task extraction completed for meeting {meeting_id}")
        
        # Step 4: Calendar Sync
        print(f"📅 Starting calendar sync for meeting {meeting_id}")
        update_processing_status('calendar_sync', 'processing', 40)
        
        if tasks_data.get('tasks'):
            calendar_result = calendar_service.create_task_events(tasks_data['tasks'], meeting_title)
            
            if not calendar_result['success']:
                update_processing_status('calendar_sync', 'failed', 0, calendar_result['error'])
                print(f"⚠️ Calendar sync failed: {calendar_result['error']}")
            else:
                update_processing_status('calendar_sync', 'completed', 100)
                print(f"✅ Calendar sync completed for meeting {meeting_id}")
        else:
            update_processing_status('calendar_sync', 'completed', 100)
            print(f"✅ Calendar sync completed (no tasks to sync) for meeting {meeting_id}")
        
        # Generate meeting summary
        summary_result = ai_processor.generate_meeting_summary(transcript, timeline_data, tasks_data)
        if summary_result['success']:
            summary_text = str(summary_result['data'])
            update_summary_query = "UPDATE meetings SET summary = %s WHERE id = %s"
            db.execute_query(update_summary_query, (summary_text, meeting_id))
        
        # Update overall meeting status
        update_meeting_query = "UPDATE meetings SET status = %s, updated_at = %s WHERE id = %s"
        db.execute_query(update_meeting_query, ('completed', datetime.utcnow(), meeting_id))
        
        print(f"🎉 Complete processing pipeline finished for meeting {meeting_id}")
        
        # Step 5: Send Email Notification
        print(f"📧 Sending email notification for meeting {meeting_id}")
        try:
            send_meeting_email_notification(meeting_id)
        except Exception as email_error:
            print(f"⚠️ Email notification failed for meeting {meeting_id}: {email_error}")
            # Don't fail the entire process if email fails
        
    except Exception as e:
        print(f"❌ Pipeline error for meeting {meeting_id}: {e}")
        # Update meeting status to failed
        update_meeting_query = "UPDATE meetings SET status = %s, updated_at = %s WHERE id = %s"
        db.execute_query(update_meeting_query, ('failed', datetime.utcnow(), meeting_id))

@upload_bp.route('/status/<meeting_id>', methods=['GET', 'OPTIONS'])
@add_security_headers()
def get_processing_status(meeting_id):
    """Get processing status for a meeting"""
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
        from middleware.validation import RequestValidator
        if not RequestValidator.validate_uuid(meeting_id):
            return jsonify({'error': 'Invalid meeting ID format'}), 400
        
        print(f"🔍 Getting processing status for meeting: {meeting_id}")
        
        # Get meeting info
        meeting_query = "SELECT * FROM meetings WHERE id = %s"
        meeting_result = db.execute_query(meeting_query, (meeting_id,))
        
        if not meeting_result:
            print(f"❌ Meeting not found: {meeting_id}")
            return jsonify({
                'error': 'Meeting not found',
                'meeting_id': meeting_id,
                'message': 'The requested meeting does not exist. It may have been deleted or never created successfully.'
            }), 404
        
        meeting = meeting_result[0]
        
        # Get processing status
        status_query = "SELECT * FROM processing_status WHERE meeting_id = %s ORDER BY started_at"
        status_result = db.execute_query(status_query, (meeting_id,))
        
        print(f"✅ Found meeting: {meeting['title']} (status: {meeting['status']})")
        print(f"✅ Found {len(status_result) if status_result else 0} processing steps")
        
        return jsonify({
            'meeting_id': meeting_id,
            'meeting_status': meeting['status'],
            'title': meeting['title'],
            'created_at': meeting['created_at'].isoformat() if meeting['created_at'] else None,
            'processing_steps': [
                {
                    'step': step['step'],
                    'status': step['status'],
                    'progress': step['progress'],
                    'error_message': step['error_message'],
                    'started_at': step['started_at'].isoformat() if step['started_at'] else None,
                    'completed_at': step['completed_at'].isoformat() if step['completed_at'] else None
                }
                for step in (status_result or [])
            ]
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting status for meeting {meeting_id}: {e}")
        return jsonify({'error': f'Failed to get status: {str(e)}'}), 500

@upload_bp.route('/meetings', methods=['GET'])
@add_security_headers()
def list_recent_meetings():
    """List recent meetings for debugging"""
    try:
        # Get recent meetings
        query = """
        SELECT id, title, status, created_at, user_id 
        FROM meetings 
        ORDER BY created_at DESC 
        LIMIT 10
        """
        meetings = db.execute_query(query)
        
        print(f"📋 Found {len(meetings) if meetings else 0} recent meetings")
        
        return jsonify({
            'meetings': [
                {
                    'id': meeting['id'],
                    'title': meeting['title'],
                    'status': meeting['status'],
                    'created_at': meeting['created_at'].isoformat() if meeting['created_at'] else None,
                    'user_id': meeting['user_id']
                }
                for meeting in (meetings or [])
            ]
        }), 200
        
    except Exception as e:
        print(f"❌ Error listing meetings: {e}")
        return jsonify({'error': f'Failed to list meetings: {str(e)}'}), 500

def send_meeting_email_notification(meeting_id: str):
    """
    Send email notification to user with meeting summary, timeline, and tasks
    """
    try:
        # Get meeting data and user preferences
        meeting_query = """
        SELECT m.*, u.email, u.name, u.email_notifications 
        FROM meetings m 
        JOIN users u ON m.user_id = u.id 
        WHERE m.id = %s
        """
        meeting_result = db.execute_query(meeting_query, (meeting_id,))
        
        if not meeting_result:
            print(f"❌ Meeting {meeting_id} not found for email notification")
            return
        
        meeting_data = meeting_result[0]
        user_email = meeting_data['email']
        user_name = meeting_data['name']
        email_notifications_enabled = meeting_data['email_notifications']
        
        # Check if user has email notifications enabled
        if not email_notifications_enabled:
            print(f"📧 Email notifications disabled for user {user_email}, skipping email for meeting {meeting_id}")
            return
        
        # Get timeline data
        timeline_query = """
        SELECT * FROM timeline 
        WHERE meeting_id = %s 
        ORDER BY timestamp_minutes ASC
        """
        timeline_result = db.execute_query(timeline_query, (meeting_id,))
        timeline_data = timeline_result or []
        
        # Get tasks data
        tasks_query = """
        SELECT * FROM tasks 
        WHERE meeting_id = %s 
        ORDER BY priority DESC, created_at ASC
        """
        tasks_result = db.execute_query(tasks_query, (meeting_id,))
        tasks_data = tasks_result or []
        
        # Convert data to proper format for email
        formatted_meeting_data = {
            'id': meeting_data['id'],
            'title': meeting_data['title'],
            'duration': meeting_data['duration'],
            'created_at': meeting_data['created_at'].strftime('%Y-%m-%d %H:%M') if meeting_data['created_at'] else None,
            'status': meeting_data['status']
        }
        
        formatted_timeline_data = []
        for item in timeline_data:
            formatted_timeline_data.append({
                'timestamp': item['timestamp'],
                'timestamp_minutes': float(item['timestamp_minutes']) if item['timestamp_minutes'] else 0,
                'event_type': item['event_type'],
                'title': item['title'],
                'content': item['content'],
                'participants': item['participants'] if item['participants'] else []
            })
        
        formatted_tasks_data = []
        for task in tasks_data:
            formatted_tasks_data.append({
                'title': task['title'],
                'description': task['description'],
                'assigned_to': task['assigned_to'],
                'deadline': task['deadline'].strftime('%Y-%m-%d') if task['deadline'] else None,
                'priority': task['priority'],
                'status': task['status']
            })
        
        # Send email
        success = email_service.send_meeting_summary_email(
            user_email=user_email,
            user_name=user_name,
            meeting_data=formatted_meeting_data,
            timeline_data=formatted_timeline_data,
            tasks_data=formatted_tasks_data
        )
        
        if success:
            print(f"✅ Email notification sent successfully to {user_email} for meeting {meeting_id}")
        else:
            print(f"❌ Failed to send email notification to {user_email} for meeting {meeting_id}")
            
    except Exception as e:
        print(f"❌ Error sending email notification for meeting {meeting_id}: {str(e)}")
        raise e
