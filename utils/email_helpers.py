"""
Email Helper Functions
Convenience functions to send emails from various parts of the application
"""

from services.email_service import email_service
from config.database import get_db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def notify_meeting_processed(meeting_id: str, user_id: str):
    """
    Send email notification when a meeting is processed
    Called from upload/processing routes
    """
    try:
        # Get meeting details
        meeting_query = """
        SELECT m.*, u.email, u.name 
        FROM meetings m
        JOIN users u ON m.user_id = u.id
        WHERE m.id = %s AND m.user_id = %s
        """
        meeting_result = get_db().execute_query(meeting_query, (meeting_id, user_id))
        
        if not meeting_result:
            logger.warning(f"Meeting {meeting_id} not found for notification")
            return False
        
        meeting = meeting_result[0]
        
        # Check if user has email notifications enabled
        if not meeting.get('email_notifications', True):
            logger.info(f"Email notifications disabled for user {user_id}")
            return False
        
        # Get timeline count
        timeline_query = "SELECT COUNT(*) as count FROM timeline WHERE meeting_id = %s"
        timeline_result = get_db().execute_query(timeline_query, (meeting_id,))
        timeline_count = timeline_result[0]['count'] if timeline_result else 0
        
        # Get tasks count
        tasks_query = "SELECT COUNT(*) as count FROM tasks WHERE meeting_id = %s"
        tasks_result = get_db().execute_query(tasks_query, (meeting_id,))
        tasks_count = tasks_result[0]['count'] if tasks_result else 0
        
        # Get summary (first 200 chars of transcript or summary)
        summary = meeting.get('summary', meeting.get('transcript', ''))[:200] + "..."
        
        # Send email
        dashboard_url = "http://localhost:8080"  # TODO: Get from config
        
        return email_service.send_meeting_processed_notification(
            user_email=meeting['email'],
            user_name=meeting['name'],
            meeting_title=meeting['title'],
            meeting_id=meeting_id,
            transcription_summary=summary,
            timeline_count=timeline_count,
            tasks_count=tasks_count,
            meeting_duration=meeting.get('duration', 0) or 0,
            dashboard_url=dashboard_url
        )
    
    except Exception as e:
        logger.error(f"Error sending meeting processed notification: {e}")
        return False


def notify_task_assigned(task_id: str, user_id: str):
    """
    Send email notification when a task is assigned
    Called from tasks routes
    """
    try:
        # Get task details with meeting info
        task_query = """
        SELECT t.*, m.title as meeting_title, u.email, u.name
        FROM tasks t
        JOIN meetings m ON t.meeting_id = m.id
        JOIN users u ON t.user_id = u.id
        WHERE t.id = %s AND t.user_id = %s
        """
        task_result = get_db().execute_query(task_query, (task_id, user_id))
        
        if not task_result:
            logger.warning(f"Task {task_id} not found for notification")
            return False
        
        task = task_result[0]
        
        # Check if user has email notifications enabled
        user_query = "SELECT email_notifications FROM users WHERE id = %s"
        user_result = get_db().execute_query(user_query, (user_id,))
        
        if user_result and not user_result[0].get('email_notifications', True):
            logger.info(f"Email notifications disabled for user {user_id}")
            return False
        
        dashboard_url = "http://localhost:8080"  # TODO: Get from config
        
        return email_service.send_task_assignment_notification(
            user_email=task['email'],
            user_name=task['name'],
            task_title=task['title'],
            task_description=task.get('description', ''),
            assigned_to=task.get('assigned_to', task['name']),
            deadline=task.get('deadline'),
            meeting_title=task['meeting_title'],
            priority=task.get('priority', 'medium'),
            dashboard_url=dashboard_url
        )
    
    except Exception as e:
        logger.error(f"Error sending task assignment notification: {e}")
        return False


def notify_calendar_sync(user_id: str, tasks_synced: int):
    """
    Send email notification when tasks are synced to calendar
    Called from calendar sync routes
    """
    try:
        # Get user details
        user_query = "SELECT email, name, email_notifications FROM users WHERE id = %s"
        user_result = get_db().execute_query(user_query, (user_id,))
        
        if not user_result:
            logger.warning(f"User {user_id} not found for notification")
            return False
        
        user = user_result[0]
        
        if not user.get('email_notifications', True):
            logger.info(f"Email notifications disabled for user {user_id}")
            return False
        
        dashboard_url = "http://localhost:8080"  # TODO: Get from config
        
        return email_service.send_calendar_sync_notification(
            user_email=user['email'],
            user_name=user['name'],
            tasks_synced=tasks_synced,
            calendar_name="Google Calendar",
            dashboard_url=dashboard_url
        )
    
    except Exception as e:
        logger.error(f"Error sending calendar sync notification: {e}")
        return False


def send_feature_announcement(feature_title: str, feature_description: str, features_list: list):
    """
    Send feature announcement to all users with email notifications enabled
    Called manually or from admin panel
    """
    try:
        # Get all users with email notifications enabled
        users_query = """
        SELECT email, name 
        FROM users 
        WHERE email_notifications = TRUE AND is_active = TRUE
        """
        users_result = get_db().execute_query(users_query)
        
        if not users_result:
            logger.warning("No users found for feature announcement")
            return 0
        
        dashboard_url = "http://localhost:8080"  # TODO: Get from config
        sent_count = 0
        
        for user in users_result:
            try:
                success = email_service.send_feature_update_announcement(
                    user_email=user['email'],
                    user_name=user['name'],
                    feature_title=feature_title,
                    feature_description=feature_description,
                    features_list=features_list,
                    cta_url=dashboard_url,
                    cta_text="Try It Now"
                )
                if success:
                    sent_count += 1
            except Exception as e:
                logger.error(f"Error sending announcement to {user['email']}: {e}")
                continue
        
        logger.info(f"Feature announcement sent to {sent_count} users")
        return sent_count
    
    except Exception as e:
        logger.error(f"Error sending feature announcements: {e}")
        return 0


def send_weekly_summaries():
    """
    Send weekly summary emails to all active users
    Should be called by a scheduled job (cron/celery)
    """
    try:
        from datetime import timedelta
        
        # Get all active users
        users_query = """
        SELECT id, email, name 
        FROM users 
        WHERE email_notifications = TRUE AND is_active = TRUE
        """
        users_result = get_db().execute_query(users_query)
        
        if not users_result:
            logger.warning("No users found for weekly summary")
            return 0
        
        dashboard_url = "http://localhost:8080"  # TODO: Get from config
        sent_count = 0
        week_ago = datetime.now() - timedelta(days=7)
        
        for user in users_result:
            try:
                user_id = user['id']
                
                # Get user's weekly stats
                meetings_query = """
                SELECT COUNT(*) as count, SUM(duration) as total_time
                FROM meetings
                WHERE user_id = %s AND created_at >= %s
                """
                meetings_result = get_db().execute_query(meetings_query, (user_id, week_ago))
                meetings_count = meetings_result[0]['count'] if meetings_result else 0
                total_time = meetings_result[0]['total_time'] if meetings_result else 0
                
                # Get tasks stats
                tasks_completed_query = """
                SELECT COUNT(*) as count
                FROM tasks
                WHERE user_id = %s AND status = 'completed' AND updated_at >= %s
                """
                tasks_completed_result = get_db().execute_query(tasks_completed_query, (user_id, week_ago))
                tasks_completed = tasks_completed_result[0]['count'] if tasks_completed_result else 0
                
                tasks_pending_query = """
                SELECT COUNT(*) as count
                FROM tasks
                WHERE user_id = %s AND status = 'pending'
                """
                tasks_pending_result = get_db().execute_query(tasks_pending_query, (user_id,))
                tasks_pending = tasks_pending_result[0]['count'] if tasks_pending_result else 0
                
                # Get top meetings
                top_meetings_query = """
                SELECT title, created_at, duration,
                       (SELECT COUNT(*) FROM tasks WHERE meeting_id = m.id) as tasks
                FROM meetings m
                WHERE user_id = %s AND created_at >= %s
                ORDER BY created_at DESC
                LIMIT 3
                """
                top_meetings_result = get_db().execute_query(top_meetings_query, (user_id, week_ago))
                
                top_meetings = []
                if top_meetings_result:
                    for meeting in top_meetings_result:
                        top_meetings.append({
                            'title': meeting['title'],
                            'date': meeting['created_at'].strftime('%b %d'),
                            'duration': meeting['duration'] or 0,
                            'tasks': meeting['tasks']
                        })
                
                # Only send if user had activity
                if meetings_count > 0:
                    success = email_service.send_weekly_summary(
                        user_email=user['email'],
                        user_name=user['name'],
                        meetings_count=meetings_count,
                        tasks_completed=tasks_completed,
                        tasks_pending=tasks_pending,
                        total_meeting_time=total_time or 0,
                        top_meetings=top_meetings,
                        dashboard_url=dashboard_url
                    )
                    if success:
                        sent_count += 1
            
            except Exception as e:
                logger.error(f"Error sending weekly summary to {user['email']}: {e}")
                continue
        
        logger.info(f"Weekly summaries sent to {sent_count} users")
        return sent_count
    
    except Exception as e:
        logger.error(f"Error sending weekly summaries: {e}")
        return 0
