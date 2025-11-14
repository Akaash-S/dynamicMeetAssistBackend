from flask import Blueprint, request, jsonify
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

from config.aws_rds_database import rds_db
from services.aws_s3_service import s3_service
from services.transcription import transcription_service
from services.ai_processor import ai_processor
from services.calendar_sync import calendar_service
from services.email_service import email_service
from middleware.validation import validate_file_upload, validate_user_id, add_security_headers
from routes.notifications import create_notification

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'mp4', 'webm'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/audio', methods=['POST'])
@add_security_headers()
def upload_audio():
    """Upload audio file and start processing pipeline"""
    try:
        print(f"🔍 Received upload request - Method: {request.method}")
        print(f"🔍 Request files: {list(request.files.keys())}")
        print(f"🔍 Request form data: {dict(request.form)}")
        
        # Manual validation since decorators might be failing
        if 'audio' not in request.files:
            print("❌ No audio file in request.files")
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            print("❌ Empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate user_id
        user_id = request.form.get('user_id')
        if not user_id:
            print("❌ No user_id in form data")
            return jsonify({'error': 'User ID is required'}), 400
        
        # Validate file manually
        from middleware.validation import RequestValidator
        try:
            file_info = RequestValidator.validate_file_upload(file)
            print(f"✅ File validation passed: {file_info}")
        except Exception as validation_error:
            print(f"❌ File validation failed: {validation_error}")
            return jsonify({'error': f'File validation failed: {str(validation_error)}'}), 400
        
        # Validate and sanitize user_id
        try:
            user_id = RequestValidator.sanitize_string(user_id, 255)
            print(f"✅ User ID validated: {user_id}")
        except Exception as user_error:
            print(f"❌ User ID validation failed: {user_error}")
            return jsonify({'error': f'User ID validation failed: {str(user_error)}'}), 400
        
        # Check if S3 service is properly initialized
        if not s3_service:
            print("❌ S3 service not properly initialized - check AWS credentials")
            return jsonify({'error': 'Storage service not available. Please check server configuration.'}), 500
        
        meeting_title = request.form.get('title', 'Untitled Meeting')
        
        # Sanitize meeting title
        try:
            meeting_title = RequestValidator.sanitize_string(meeting_title, 255)
        except Exception as title_error:
            print(f"❌ Meeting title validation failed: {title_error}")
            meeting_title = 'Untitled Meeting'  # Default fallback
        
        # Generate unique filename using validated info
        unique_filename = f"{user_id}/{uuid.uuid4()}.{file_info['file_extension']}"
        
        # Read file data - ensure file pointer is at beginning
        file.seek(0)
        file_data = file.read()
        
        if len(file_data) == 0:
            print("❌ File data is empty after reading")
            return jsonify({'error': 'File is empty or could not be read'}), 400
        
        print(f"📁 Uploading file: {file_info['original_filename']} ({len(file_data)} bytes read, expected {file_info['file_size']} bytes)")
        
        # Upload to AWS S3
        try:
            # Create a file-like object from the bytes data
            from io import BytesIO
            file_obj = BytesIO(file_data)
            
            # Upload to S3 and get the S3 key
            s3_key = s3_service.upload_file(
                file_obj=file_obj,
                file_name=file_info['original_filename'],
                folder=f'meetings/{user_id}',
                content_type=f'audio/{file_info["file_extension"]}'
            )
            
            if not s3_key:
                print(f"❌ S3 upload returned None for file: {file_info['original_filename']}")
                return jsonify({
                    'error': 'Failed to upload file to storage. This may be due to network connectivity issues or server configuration problems.'
                }), 500
            
            # Generate presigned URL for accessing the file
            audio_url = s3_service.generate_presigned_url(s3_key, expiration=86400)  # 24 hours
            
            if not audio_url:
                print(f"❌ Failed to generate presigned URL for: {s3_key}")
                return jsonify({
                    'error': 'Failed to generate access URL for uploaded file.'
                }), 500
                
        except Exception as storage_error:
            print(f"❌ Storage upload error: {storage_error}")
            error_message = str(storage_error)
            
            # Provide specific error messages for common issues
            if "getaddrinfo failed" in error_message:
                return jsonify({
                    'error': 'Network connectivity issue - unable to connect to storage server. Please check your internet connection and try again.'
                }), 500
            elif "ConnectionError" in error_message:
                return jsonify({
                    'error': 'Connection error - storage service is temporarily unavailable. Please try again later.'
                }), 500
            else:
                return jsonify({
                    'error': f'Storage upload failed: {error_message}'
                }), 500
        
        print(f"☁️ File uploaded successfully: {audio_url}")
        
        # user_id is now the database user ID (not Firebase UID)
        print(f"📁 Creating meeting for database user ID: {user_id}")
        
        # Test database connection before proceeding
        try:
            # Simple query to test connection
            test_result = rds_db.execute_query("SELECT 1 as test", fetch_one=True)
            if not test_result:
                print("❌ Database connection test failed")
                return jsonify({'error': 'Database connection failed'}), 500
            print("✅ Database connection verified")
        except Exception as db_test_error:
            print(f"❌ Database connection test error: {db_test_error}")
            return jsonify({'error': f'Database connection error: {str(db_test_error)}'}), 500
        
        # Create meeting record in database
        meeting_id = str(uuid.uuid4())
        
        try:
            insert_meeting_query = """
            INSERT INTO meetings (id, user_id, title, audio_url, status, file_size, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            rds_db.execute_query(insert_meeting_query, (
                meeting_id,
                user_id,  # Use database user ID directly
                meeting_title,
                audio_url,
                'processing',
                file_info['file_size'],
                datetime.utcnow()
            ))
            
            print(f"💾 Meeting record created: {meeting_id}")
            
        except Exception as db_error:
            print(f"❌ Database error creating meeting: {db_error}")
            return jsonify({'error': f'Failed to create meeting record: {str(db_error)}'}), 500
        
        # Create initial processing status
        try:
            processing_steps = ['transcription', 'ai_analysis', 'task_extraction', 'calendar_sync']
            
            for step in processing_steps:
                insert_status_query = """
                INSERT INTO processing_status (meeting_id, step, status, progress)
                VALUES (%s, %s, %s, %s)
                """
                rds_db.execute_query(insert_status_query, (meeting_id, step, 'pending', 0))
                
            print(f"✅ Processing status records created for meeting: {meeting_id}")
            
        except Exception as status_error:
            print(f"❌ Database error creating processing status: {status_error}")
            # Don't fail the entire request if status creation fails, just log it
        
        print(f"📊 Meeting details: title='{meeting_title}', user_id='{user_id}', status='processing'")
        
        # Start processing pipeline asynchronously (in a real app, use Celery or similar)
        # For now, we'll process synchronously but return immediately
        try:
            process_meeting_pipeline(meeting_id, audio_url, meeting_title)
        except Exception as e:
            print(f"❌ Processing pipeline error: {e}")
            # Update meeting status to failed
            try:
                update_meeting_query = "UPDATE meetings SET status = %s WHERE id = %s"
                rds_db.execute_query(update_meeting_query, ('failed', meeting_id))
            except Exception as update_error:
                print(f"❌ Failed to update meeting status to failed: {update_error}")
        
        return jsonify({
            'success': True,
            'meeting_id': meeting_id,
            'audio_url': audio_url,
            'file_size': file_info['file_size'],
            'status': 'processing',
            'message': 'File uploaded successfully. Processing started.'
        }), 200
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Upload error: {e}")
        print(f"❌ Error traceback: {error_details}")
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
        rds_db.execute_query(update_query, (status, progress, error, status, meeting_id, step))
    
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
        rds_db.execute_query(update_meeting_query, (transcript, duration, datetime.utcnow(), meeting_id))
        
        update_processing_status('transcription', 'completed', 100)
        print(f"✅ Transcription completed for meeting {meeting_id}")
        
        # Create notification for transcription completion
        get_user_query = "SELECT user_id FROM meetings WHERE id = %s"
        user_result = rds_db.execute_query(get_user_query, (meeting_id,), fetch_all=True)
        if user_result:
            user_id = user_result[0]['user_id']
            create_notification(
                user_id=user_id,
                notification_type='transcription_ready',
                title='Transcription Complete',
                message=f'Transcription for "{meeting_title}" is ready',
                data={'meeting_id': meeting_id, 'duration': duration}
            )
        
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
                rds_db.execute_query(insert_timeline_query, (
                    meeting_id,
                    entry.get('timestamp_minutes', 0),
                    entry.get('event_type', 'discussion'),
                    entry.get('title', ''),
                    entry.get('content', ''),
                    entry.get('participants', [])
                ))
        
        update_processing_status('ai_analysis', 'completed', 100)
        print(f"✅ AI analysis completed for meeting {meeting_id}")
        
        # Create notification for timeline generation
        if user_result:
            user_id = user_result[0]['user_id']
            timeline_count = len(timeline_data.get('timeline', []))
            create_notification(
                user_id=user_id,
                notification_type='timeline_generated',
                title='Timeline Generated',
                message=f'Timeline with {timeline_count} events created for "{meeting_title}"',
                data={'meeting_id': meeting_id, 'event_count': timeline_count}
            )
        
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
                user_result = rds_db.execute_query(get_user_query, (meeting_id,), fetch_all=True)
                user_id = user_result[0]['user_id'] if user_result else None
                
                rds_db.execute_query(insert_task_query, (
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
        
        # Create notification for task extraction
        if user_result:
            user_id = user_result[0]['user_id']
            task_count = len(tasks_data.get('tasks', []))
            create_notification(
                user_id=user_id,
                notification_type='tasks_extracted',
                title='Tasks Extracted',
                message=f'{task_count} tasks extracted from "{meeting_title}"',
                data={'meeting_id': meeting_id, 'task_count': task_count, 'task_ids': task_ids}
            )
        
        # Step 4: Calendar Sync
        print(f"📅 Starting calendar sync for meeting {meeting_id}")
        update_processing_status('calendar_sync', 'processing', 40)

        if tasks_data.get('tasks'):
            # Get user_id from meeting
            get_user_query = "SELECT user_id FROM meetings WHERE id = %s"
            user_result = rds_db.execute_query(get_user_query, (meeting_id,), fetch_all=True)
            user_id = user_result[0]['user_id'] if user_result else None

            if user_id:
                # Get user's Google access token and refresh token
                get_token_query = "SELECT google_access_token, google_refresh_token FROM users WHERE id = %s"
                token_result = rds_db.execute_query(get_token_query, (user_id,), fetch_all=True)
                
                if token_result and token_result[0]['google_access_token']:
                    access_token = token_result[0]['google_access_token']
                    refresh_token = token_result[0].get('google_refresh_token')
                    
                    print(f"🔑 Found Google Calendar access token for user {user_id}")
                    
                    # Test calendar access first
                    test_result = calendar_service.test_calendar_access(access_token, refresh_token)
                    
                    if test_result['success']:
                        print(f"✅ Calendar access verified for user {user_id}")
                        
                        # Sync all tasks at once
                        sync_result = calendar_service.sync_multiple_tasks(
                            tasks=tasks_data['tasks'],
                            meeting_title=meeting_title,
                            access_token=access_token,
                            refresh_token=refresh_token
                        )
                        
                        if sync_result['success']:
                            print(f"✅ Synced {sync_result['synced_count']}/{len(tasks_data['tasks'])} tasks to Google Calendar")
                            
                            # Update task records with calendar event IDs
                            for event in sync_result['events']:
                                update_task_query = """
                                UPDATE tasks SET calendar_event_id = %s 
                                WHERE title = %s AND meeting_id = %s
                                """
                                rds_db.execute_query(update_task_query, (
                                    event['event_id'], 
                                    event['task_title'], 
                                    meeting_id
                                ))
                            
                            update_processing_status('calendar_sync', 'completed', 100)
                            
                            # Create notification for calendar sync
                            create_notification(
                                user_id=user_id,
                                notification_type='calendar_synced',
                                title='Calendar Synced',
                                message=f'{sync_result["synced_count"]} tasks synced to Google Calendar',
                                data={'meeting_id': meeting_id, 'synced_count': sync_result['synced_count']}
                            )
                        else:
                            error_msg = f"Synced {sync_result['synced_count']}/{len(tasks_data['tasks'])} tasks. Errors: {sync_result.get('errors', [])}"
                            print(f"⚠️ Partial calendar sync: {error_msg}")
                            update_processing_status('calendar_sync', 'completed', 100, error=error_msg)
                    else:
                        print(f"❌ Calendar access test failed: {test_result['error']}")
                        update_processing_status('calendar_sync', 'failed', 0, error=f"Calendar access failed: {test_result['error']}")
                else:
                    print("⚠️ No Google Calendar access token found for user. Skipping sync.")
                    update_processing_status('calendar_sync', 'completed', 100, error="Google Calendar not connected - user needs to re-authenticate")
            else:
                print("⚠️ Could not find user for meeting. Skipping calendar sync.")
                update_processing_status('calendar_sync', 'failed', 0, error="User not found for meeting")
        else:
            update_processing_status('calendar_sync', 'completed', 100)
            print(f"✅ Calendar sync completed (no tasks to sync) for meeting {meeting_id}")
        
        # Generate meeting summary
        summary_result = ai_processor.generate_meeting_summary(transcript, timeline_data, tasks_data)
        if summary_result['success']:
            summary_text = str(summary_result['data'])
            update_summary_query = "UPDATE meetings SET summary = %s WHERE id = %s"
            rds_db.execute_query(update_summary_query, (summary_text, meeting_id))
        
        # Update overall meeting status
        update_meeting_query = "UPDATE meetings SET status = %s, updated_at = %s WHERE id = %s"
        rds_db.execute_query(update_meeting_query, ('completed', datetime.utcnow(), meeting_id))
        
        print(f"🎉 Complete processing pipeline finished for meeting {meeting_id}")
        
        # Create final notification for meeting completion
        get_user_query = "SELECT user_id FROM meetings WHERE id = %s"
        user_result = rds_db.execute_query(get_user_query, (meeting_id,), fetch_all=True)
        if user_result:
            user_id = user_result[0]['user_id']
            create_notification(
                user_id=user_id,
                notification_type='meeting_completed',
                title='Meeting Processing Complete',
                message=f'"{meeting_title}" has been fully processed and is ready to view',
                data={'meeting_id': meeting_id}
            )
        
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
        rds_db.execute_query(update_meeting_query, ('failed', datetime.utcnow(), meeting_id))

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
        meeting_result = rds_db.execute_query(meeting_query, (meeting_id,), fetch_all=True)
        
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
        status_result = rds_db.execute_query(status_query, (meeting_id,), fetch_all=True)
        
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
        meetings = rds_db.execute_query(query)
        
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
        meeting_result = rds_db.execute_query(meeting_query, (meeting_id,), fetch_all=True)
        
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
        timeline_result = rds_db.execute_query(timeline_query, (meeting_id,), fetch_all=True)
        timeline_data = timeline_result or []
        
        # Get tasks data
        tasks_query = """
        SELECT * FROM tasks 
        WHERE meeting_id = %s 
        ORDER BY priority DESC, created_at ASC
        """
        tasks_result = rds_db.execute_query(tasks_query, (meeting_id,), fetch_all=True)
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
