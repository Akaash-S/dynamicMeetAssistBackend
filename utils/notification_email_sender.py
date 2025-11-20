"""
Notification Email Sender
Automatically sends emails when notifications are created
"""
import logging
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from services.email_service import email_service
from config.aws_rds_database import rds_db

logger = logging.getLogger(__name__)

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=5)

async def send_notification_email_async(notification_id: str, user_id: str):
    """
    Async wrapper for sending notification emails
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor, 
        send_notification_email, 
        notification_id, 
        user_id
    )

def send_notification_email(notification_id: str, user_id: str):
    """
    Send email for a notification
    Called after creating a notification in the database
    """
    try:
        # Get notification details
        notification_query = """
        SELECT n.*, u.email, u.name, u.email_notifications
        FROM notifications n
        JOIN users u ON n.user_id = u.id
        WHERE n.id = %s AND u.id = %s
        """
        notification = rds_db.execute_query(
            notification_query, 
            (notification_id, user_id), 
            fetch_one=True
        )
        
        if not notification:
            logger.warning(f"Notification {notification_id} not found")
            return False
        
        # Check if user has email notifications enabled
        if not notification.get('email_notifications', True):
            logger.info(f"Email notifications disabled for user {user_id}")
            return False
        
        user_email = notification['email']
        user_name = notification['name']
        notif_type = notification['type']
        title = notification['title']
        message = notification['message']
        data = notification.get('data', {})
        
        # Route to appropriate email template based on notification type
        # Using sync versions since this function runs in executor
        if notif_type == 'meeting_completed':
            return _send_meeting_completed_email(
                user_email, user_name, title, message, data
            )
        elif notif_type == 'task_assigned':
            return _send_task_assigned_email(
                user_email, user_name, title, message, data
            )
        elif notif_type == 'task_due_soon':
            return _send_task_reminder_email(
                user_email, user_name, title, message, data
            )
        elif notif_type == 'calendar_synced':
            return _send_calendar_sync_email(
                user_email, user_name, title, message, data
            )
        else:
            return _send_generic_notification_email(
                user_email, user_name, title, message
            )
            
    except Exception as e:
        logger.error(f"Error sending notification email: {e}")
        return False

async def _send_meeting_completed_email_async(user_email, user_name, title, message, data):
    """Async send email for completed meeting"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        _send_meeting_completed_email,
        user_email, user_name, title, message, data
    )

def _send_meeting_completed_email(user_email, user_name, title, message, data):
    """Send email for completed meeting"""
    meeting_id = data.get('meeting_id', '')
    meeting_title = data.get('meeting_title', 'Your Meeting')
    timeline_count = data.get('timeline_count', 0)
    tasks_count = data.get('tasks_count', 0)
    duration = data.get('duration', 0)
    summary = data.get('summary', message)
    
    dashboard_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    
    return email_service.send_meeting_processed_notification(
        user_email=user_email,
        user_name=user_name,
        meeting_title=meeting_title,
        meeting_id=meeting_id,
        transcription_summary=summary,
        timeline_count=timeline_count,
        tasks_count=tasks_count,
        meeting_duration=duration,
        dashboard_url=dashboard_url
    )

async def _send_task_assigned_email_async(user_email, user_name, title, message, data):
    """Async send email for task assignment"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        _send_task_assigned_email,
        user_email, user_name, title, message, data
    )

def _send_task_assigned_email(user_email, user_name, title, message, data):
    """Send email for task assignment"""
    task_title = data.get('task_title', title)
    task_description = data.get('description', message)
    assigned_to = data.get('assigned_to', user_name)
    deadline = data.get('deadline')
    meeting_title = data.get('meeting_title', 'Meeting')
    priority = data.get('priority', 'medium')
    
    dashboard_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    
    from datetime import datetime
    deadline_dt = datetime.fromisoformat(deadline) if deadline else None
    
    return email_service.send_task_assignment_notification(
        user_email=user_email,
        user_name=user_name,
        task_title=task_title,
        task_description=task_description,
        assigned_to=assigned_to,
        deadline=deadline_dt,
        meeting_title=meeting_title,
        priority=priority,
        dashboard_url=dashboard_url
    )

async def _send_task_reminder_email_async(user_email, user_name, title, message, data):
    """Async send email for task deadline reminder"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        _send_task_reminder_email,
        user_email, user_name, title, message, data
    )

def _send_task_reminder_email(user_email, user_name, title, message, data):
    """Send email for task deadline reminder"""
    # Use generic notification for now, can be customized later
    return _send_generic_notification_email(user_email, user_name, title, message)

async def _send_calendar_sync_email_async(user_email, user_name, title, message, data):
    """Async send email for calendar sync"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        _send_calendar_sync_email,
        user_email, user_name, title, message, data
    )

def _send_calendar_sync_email(user_email, user_name, title, message, data):
    """Send email for calendar sync"""
    tasks_synced = data.get('tasks_synced', 0)
    calendar_name = data.get('calendar_name', 'Google Calendar')
    
    dashboard_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    
    return email_service.send_calendar_sync_notification(
        user_email=user_email,
        user_name=user_name,
        tasks_synced=tasks_synced,
        calendar_name=calendar_name,
        dashboard_url=dashboard_url
    )

async def _send_generic_notification_email_async(user_email, user_name, title, message):
    """Async send generic notification email"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        _send_generic_notification_email,
        user_email, user_name, title, message
    )

def _send_generic_notification_email(user_email, user_name, title, message):
    """Send generic notification email"""
    subject = f"🔔 {title}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .message-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔔 {title}</h1>
            </div>
            <div class="content">
                <p>Hi {user_name},</p>
                <div class="message-box">
                    <p>{message}</p>
                </div>
            </div>
            <div class="footer">
                <p>AI Meeting Assistant</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Hi {user_name},
    
    {title}
    
    {message}
    
    Best regards,
    AI Meeting Assistant Team
    """
    
    msg = email_service._create_message(user_email, subject, html_content, text_content)
    return email_service._send_email(msg)
