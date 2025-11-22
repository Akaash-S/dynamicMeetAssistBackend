"""
Comprehensive Notification Service
===================================
Handles all notifications for both client and admin apps.
Triggers notifications for every important action in the application.

Features:
- Real-time notifications
- Email notifications (optional)
- Push notifications (optional)
- Notification history
- Read/unread status
- Priority levels
- Action types
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid
import logging
from config.aws_rds_database import rds_db

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating and managing notifications"""
    
    # Notification types
    TYPES = {
        # User actions
        'USER_REGISTERED': 'user',
        'USER_UPDATED': 'user',
        'USER_DELETED': 'user',
        'USER_LOGIN': 'user',
        'USER_LOGOUT': 'user',
        
        # Meeting actions
        'MEETING_CREATED': 'meeting',
        'MEETING_UPDATED': 'meeting',
        'MEETING_DELETED': 'meeting',
        'MEETING_PROCESSED': 'meeting',
        'MEETING_SHARED': 'meeting',
        
        # Task actions
        'TASK_CREATED': 'task',
        'TASK_UPDATED': 'task',
        'TASK_COMPLETED': 'task',
        'TASK_DELETED': 'task',
        'TASK_ASSIGNED': 'task',
        
        # Admin actions
        'ADMIN_ISSUE_CREATED': 'issue',
        'ADMIN_ISSUE_UPDATED': 'issue',
        'ADMIN_ISSUE_RESOLVED': 'issue',
        'ADMIN_PAYMENT_RECEIVED': 'payment',
        'ADMIN_PAYMENT_REFUNDED': 'payment',
        'ADMIN_USER_PROMOTED': 'admin',
        'ADMIN_USER_DEMOTED': 'admin',
        
        # System notifications
        'SYSTEM_MAINTENANCE': 'system',
        'SYSTEM_UPDATE': 'system',
        'SYSTEM_ALERT': 'system',
        'SYSTEM_ANNOUNCEMENT': 'system',
    }
    
    # Priority levels
    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    
    @staticmethod
    def create_notification(
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        priority: str = PRIORITY_MEDIUM,
        action_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        send_email: bool = False
    ) -> Optional[str]:
        """
        Create a notification for a user
        
        Args:
            user_id: User ID to send notification to
            notification_type: Type of notification (from TYPES)
            title: Notification title
            message: Notification message
            priority: Priority level (low, medium, high, urgent)
            action_url: Optional URL for action button
            metadata: Optional metadata dictionary
            send_email: Whether to send email notification
            
        Returns:
            Notification ID if successful, None otherwise
        """
        try:
            notification_id = str(uuid.uuid4())
            
            # Insert into notifications table
            query = """
            INSERT INTO notifications (
                id, user_id, type, title, message, priority, 
                action_url, metadata, is_read, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            import json
            metadata_json = json.dumps(metadata) if metadata else None
            
            rds_db.execute_query(query, (
                notification_id,
                user_id,
                notification_type,
                title,
                message,
                priority,
                action_url,
                metadata_json,
                False,  # is_read
                datetime.utcnow()
            ))
            
            logger.info(f"Notification created: {notification_id} for user {user_id}")
            
            # Send email if requested
            if send_email:
                NotificationService._send_email_notification(
                    user_id, title, message, action_url
                )
            
            return notification_id
            
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            return None
    
    @staticmethod
    def create_admin_notification(
        admin_email: str,
        notification_type: str,
        title: str,
        message: str,
        priority: str = PRIORITY_MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create a notification for admin dashboard
        
        Args:
            admin_email: Admin email
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            priority: Priority level
            metadata: Optional metadata
            
        Returns:
            Notification ID if successful
        """
        try:
            notification_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO admin_notifications (
                id, message, type, priority, is_read, 
                metadata, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            import json
            metadata_json = json.dumps(metadata or {
                'admin_email': admin_email,
                'title': title
            })
            
            rds_db.execute_query(query, (
                notification_id,
                message,
                notification_type,
                priority,
                False,
                metadata_json,
                datetime.utcnow()
            ))
            
            logger.info(f"Admin notification created: {notification_id}")
            return notification_id
            
        except Exception as e:
            logger.error(f"Failed to create admin notification: {e}")
            return None
    
    @staticmethod
    def notify_user_action(user_id: str, action: str, details: str = None):
        """Notify about user-related actions"""
        messages = {
            'registered': ('Welcome!', 'Your account has been created successfully.'),
            'updated': ('Profile Updated', 'Your profile information has been updated.'),
            'login': ('Login Successful', 'You have successfully logged in.'),
        }
        
        if action in messages:
            title, message = messages[action]
            if details:
                message += f' {details}'
            
            NotificationService.create_notification(
                user_id=user_id,
                notification_type=f'USER_{action.upper()}',
                title=title,
                message=message,
                priority=NotificationService.PRIORITY_LOW
            )
    
    @staticmethod
    def notify_meeting_action(user_id: str, meeting_id: str, action: str, meeting_title: str = None):
        """Notify about meeting-related actions"""
        messages = {
            'created': ('Meeting Created', f'Meeting "{meeting_title}" has been created.'),
            'updated': ('Meeting Updated', f'Meeting "{meeting_title}" has been updated.'),
            'deleted': ('Meeting Deleted', f'Meeting "{meeting_title}" has been deleted.'),
            'processed': ('Meeting Processed', f'Meeting "{meeting_title}" has been processed successfully.'),
            'shared': ('Meeting Shared', f'Meeting "{meeting_title}" has been shared.'),
        }
        
        if action in messages:
            title, message = messages[action]
            
            NotificationService.create_notification(
                user_id=user_id,
                notification_type=f'MEETING_{action.upper()}',
                title=title,
                message=message,
                priority=NotificationService.PRIORITY_MEDIUM,
                action_url=f'/meetings/{meeting_id}',
                metadata={'meeting_id': meeting_id, 'meeting_title': meeting_title}
            )
    
    @staticmethod
    def notify_task_action(user_id: str, task_id: str, action: str, task_title: str = None):
        """Notify about task-related actions"""
        messages = {
            'created': ('Task Created', f'New task: "{task_title}"'),
            'updated': ('Task Updated', f'Task "{task_title}" has been updated.'),
            'completed': ('Task Completed', f'Task "{task_title}" has been completed! 🎉'),
            'deleted': ('Task Deleted', f'Task "{task_title}" has been deleted.'),
            'assigned': ('Task Assigned', f'You have been assigned task: "{task_title}"'),
        }
        
        if action in messages:
            title, message = messages[action]
            priority = NotificationService.PRIORITY_HIGH if action == 'assigned' else NotificationService.PRIORITY_MEDIUM
            
            NotificationService.create_notification(
                user_id=user_id,
                notification_type=f'TASK_{action.upper()}',
                title=title,
                message=message,
                priority=priority,
                action_url=f'/tasks/{task_id}',
                metadata={'task_id': task_id, 'task_title': task_title}
            )
    
    @staticmethod
    def notify_admin_issue(admin_email: str, issue_id: str, action: str, issue_title: str, user_email: str = None):
        """Notify admins about issue-related actions"""
        messages = {
            'created': f'New issue reported: "{issue_title}"' + (f' by {user_email}' if user_email else ''),
            'updated': f'Issue updated: "{issue_title}"',
            'resolved': f'Issue resolved: "{issue_title}"',
        }
        
        if action in messages:
            NotificationService.create_admin_notification(
                admin_email=admin_email,
                notification_type=f'ADMIN_ISSUE_{action.upper()}',
                title=f'Issue {action.title()}',
                message=messages[action],
                priority=NotificationService.PRIORITY_HIGH if action == 'created' else NotificationService.PRIORITY_MEDIUM,
                metadata={'issue_id': issue_id, 'issue_title': issue_title, 'user_email': user_email}
            )
    
    @staticmethod
    def notify_admin_payment(admin_email: str, payment_id: str, action: str, amount: float, user_email: str = None):
        """Notify admins about payment-related actions"""
        messages = {
            'received': f'Payment received: ${amount:.2f}' + (f' from {user_email}' if user_email else ''),
            'refunded': f'Payment refunded: ${amount:.2f}' + (f' to {user_email}' if user_email else ''),
        }
        
        if action in messages:
            NotificationService.create_admin_notification(
                admin_email=admin_email,
                notification_type=f'ADMIN_PAYMENT_{action.upper()}',
                title=f'Payment {action.title()}',
                message=messages[action],
                priority=NotificationService.PRIORITY_MEDIUM,
                metadata={'payment_id': payment_id, 'amount': amount, 'user_email': user_email}
            )
    
    @staticmethod
    def notify_system_announcement(message: str, priority: str = PRIORITY_MEDIUM, target_users: List[str] = None):
        """Send system-wide announcement to all users or specific users"""
        try:
            if target_users:
                # Send to specific users
                for user_id in target_users:
                    NotificationService.create_notification(
                        user_id=user_id,
                        notification_type='SYSTEM_ANNOUNCEMENT',
                        title='System Announcement',
                        message=message,
                        priority=priority
                    )
            else:
                # Send to all users
                users_query = "SELECT id FROM users WHERE is_active = true"
                users = rds_db.execute_query(users_query, fetch_all=True)
                
                for user in (users or []):
                    NotificationService.create_notification(
                        user_id=user['id'],
                        notification_type='SYSTEM_ANNOUNCEMENT',
                        title='System Announcement',
                        message=message,
                        priority=priority
                    )
            
            logger.info(f"System announcement sent: {message}")
            
        except Exception as e:
            logger.error(f"Failed to send system announcement: {e}")
    
    @staticmethod
    def _send_email_notification(user_id: str, title: str, message: str, action_url: Optional[str] = None):
        """Send email notification (placeholder for email service integration)"""
        try:
            # Get user email
            user_query = "SELECT email, name FROM users WHERE id = %s"
            user = rds_db.execute_query(user_query, (user_id,), fetch_one=True)
            
            if not user:
                return
            
            # TODO: Integrate with email service (SendGrid, AWS SES, etc.)
            logger.info(f"Email notification would be sent to {user['email']}: {title}")
            
            # Example email content:
            # Subject: {title}
            # Body: Hi {user['name']}, {message}
            # Action: {action_url}
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    @staticmethod
    def mark_as_read(notification_id: str, user_id: str) -> bool:
        """Mark a notification as read"""
        try:
            query = """
            UPDATE notifications 
            SET is_read = true, read_at = %s 
            WHERE id = %s AND user_id = %s
            """
            rds_db.execute_query(query, (datetime.utcnow(), notification_id, user_id))
            return True
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            return False
    
    @staticmethod
    def mark_all_as_read(user_id: str) -> bool:
        """Mark all notifications as read for a user"""
        try:
            query = """
            UPDATE notifications 
            SET is_read = true, read_at = %s 
            WHERE user_id = %s AND is_read = false
            """
            rds_db.execute_query(query, (datetime.utcnow(), user_id))
            return True
        except Exception as e:
            logger.error(f"Failed to mark all notifications as read: {e}")
            return False
    
    @staticmethod
    def get_unread_count(user_id: str) -> int:
        """Get count of unread notifications for a user"""
        try:
            query = "SELECT COUNT(*) as count FROM notifications WHERE user_id = %s AND is_read = false"
            result = rds_db.execute_query(query, (user_id,), fetch_one=True)
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return 0
    
    @staticmethod
    def delete_old_notifications(days: int = 30):
        """Delete notifications older than specified days"""
        try:
            query = """
            DELETE FROM notifications 
            WHERE created_at < NOW() - INTERVAL '%s days' 
            AND is_read = true
            """
            rds_db.execute_query(query, (days,))
            logger.info(f"Deleted notifications older than {days} days")
        except Exception as e:
            logger.error(f"Failed to delete old notifications: {e}")


# Convenience functions for easy access
def notify_user(user_id: str, action: str, details: str = None):
    """Quick function to notify user actions"""
    NotificationService.notify_user_action(user_id, action, details)

def notify_meeting(user_id: str, meeting_id: str, action: str, meeting_title: str = None):
    """Quick function to notify meeting actions"""
    NotificationService.notify_meeting_action(user_id, meeting_id, action, meeting_title)

def notify_task(user_id: str, task_id: str, action: str, task_title: str = None):
    """Quick function to notify task actions"""
    NotificationService.notify_task_action(user_id, task_id, action, task_title)

def notify_admin_issue(admin_email: str, issue_id: str, action: str, issue_title: str, user_email: str = None):
    """Quick function to notify admin about issues"""
    NotificationService.notify_admin_issue(admin_email, issue_id, action, issue_title, user_email)

def notify_admin_payment(admin_email: str, payment_id: str, action: str, amount: float, user_email: str = None):
    """Quick function to notify admin about payments"""
    NotificationService.notify_admin_payment(admin_email, payment_id, action, amount, user_email)
