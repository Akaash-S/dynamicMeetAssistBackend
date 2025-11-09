"""
Email Service for Dynamic Meeting Assistant
Handles all email notifications including:
- Meeting transcription completion
- Task assignments and reminders
- Feature updates and announcements
- Calendar sync notifications
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.email_address = os.getenv('EMAIL_ADDRESS')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.from_name = os.getenv('FROM_NAME', 'AI Meeting Assistant')
        
        if not self.email_address or not self.email_password:
            logger.warning("Email credentials not configured. Email notifications will be disabled.")
    
    def _create_message(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> MIMEMultipart:
        """Create email message with HTML and text alternatives"""
        message = MIMEMultipart('alternative')
        message['From'] = f"{self.from_name} <{self.email_address}>"
        message['To'] = to_email
        message['Subject'] = subject
        
        # Add text version (fallback)
        if text_content:
            text_part = MIMEText(text_content, 'plain')
            message.attach(text_part)
        
        # Add HTML version
        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)
        
        return message
    
    def _send_email(self, message: MIMEMultipart) -> bool:
        """Send email via SMTP"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(message)
            
            logger.info(f"Email sent successfully to {message['To']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_meeting_processed_notification(
        self,
        user_email: str,
        user_name: str,
        meeting_title: str,
        meeting_id: str,
        transcription_summary: str,
        timeline_count: int,
        tasks_count: int,
        meeting_duration: int,
        dashboard_url: str
    ) -> bool:
        """
        Send notification when meeting transcription is complete
        
        Args:
            user_email: Recipient email
            user_name: User's name
            meeting_title: Title of the meeting
            meeting_id: Meeting ID for linking
            transcription_summary: Brief summary of transcription
            timeline_count: Number of timeline events
            tasks_count: Number of tasks extracted
            meeting_duration: Duration in minutes
            dashboard_url: URL to view meeting details
        """
        subject = f"✅ Meeting Processed: {meeting_title}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat-box {{ background: white; padding: 15px; border-radius: 8px; text-align: center; flex: 1; margin: 0 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .stat-number {{ font-size: 24px; font-weight: bold; color: #667eea; }}
                .stat-label {{ font-size: 12px; color: #6b7280; margin-top: 5px; }}
                .summary-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Your Meeting is Ready!</h1>
                    <p>We've processed your meeting and extracted key insights</p>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>Great news! Your meeting "<strong>{meeting_title}</strong>" has been successfully processed.</p>
                    
                    <div class="stats">
                        <div class="stat-box">
                            <div class="stat-number">{meeting_duration}</div>
                            <div class="stat-label">Minutes</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-number">{timeline_count}</div>
                            <div class="stat-label">Timeline Events</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-number">{tasks_count}</div>
                            <div class="stat-label">Tasks Extracted</div>
                        </div>
                    </div>
                    
                    <div class="summary-box">
                        <h3>📝 Quick Summary</h3>
                        <p>{transcription_summary}</p>
                    </div>
                    
                    <p><strong>What's included:</strong></p>
                    <ul>
                        <li>✅ Full meeting transcription</li>
                        <li>✅ Interactive timeline with key moments</li>
                        <li>✅ Automatically extracted action items</li>
                        <li>✅ AI-generated meeting summary</li>
                    </ul>
                    
                    <center>
                        <a href="{dashboard_url}/timeline?meeting={meeting_id}" class="button">
                            View Meeting Details →
                        </a>
                    </center>
                    
                    <p style="margin-top: 30px; font-size: 14px; color: #6b7280;">
                        💡 <strong>Tip:</strong> You can export this meeting to PDF or sync tasks to your calendar from the dashboard.
                    </p>
                </div>
                <div class="footer">
                    <p>AI Meeting Assistant | Making meetings more productive</p>
                    <p>You're receiving this because you uploaded a meeting for processing.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {user_name},
        
        Your meeting "{meeting_title}" has been successfully processed!
        
        Meeting Stats:
        - Duration: {meeting_duration} minutes
        - Timeline Events: {timeline_count}
        - Tasks Extracted: {tasks_count}
        
        Summary:
        {transcription_summary}
        
        View full details: {dashboard_url}/timeline?meeting={meeting_id}
        
        Best regards,
        AI Meeting Assistant Team
        """
        
        message = self._create_message(user_email, subject, html_content, text_content)
        return self._send_email(message)
    
    def send_task_assignment_notification(
        self,
        user_email: str,
        user_name: str,
        task_title: str,
        task_description: str,
        assigned_to: str,
        deadline: Optional[datetime],
        meeting_title: str,
        priority: str,
        dashboard_url: str
    ) -> bool:
        """Send notification when a task is assigned"""
        subject = f"📋 New Task Assigned: {task_title}"
        
        deadline_str = deadline.strftime("%B %d, %Y at %I:%M %p") if deadline else "No deadline set"
        priority_color = {
            'high': '#ef4444',
            'medium': '#f59e0b',
            'low': '#10b981'
        }.get(priority.lower(), '#6b7280')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .task-card {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .priority-badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; color: white; background: {priority_color}; }}
                .deadline-box {{ background: #fef3c7; padding: 15px; border-radius: 6px; margin: 15px 0; border-left: 4px solid #f59e0b; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 New Task Assigned</h1>
                    <p>You have a new action item from your meeting</p>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>A new task has been assigned to <strong>{assigned_to}</strong> from the meeting "<strong>{meeting_title}</strong>".</p>
                    
                    <div class="task-card">
                        <div style="margin-bottom: 10px;">
                            <span class="priority-badge">{priority.upper()} PRIORITY</span>
                        </div>
                        <h2 style="margin: 10px 0;">{task_title}</h2>
                        <p style="color: #6b7280;">{task_description}</p>
                    </div>
                    
                    <div class="deadline-box">
                        <strong>⏰ Deadline:</strong> {deadline_str}
                    </div>
                    
                    <p><strong>Next Steps:</strong></p>
                    <ul>
                        <li>Review the task details in your dashboard</li>
                        <li>Add it to your Google Calendar (if enabled)</li>
                        <li>Mark as complete when done</li>
                    </ul>
                    
                    <center>
                        <a href="{dashboard_url}/tasks" class="button">
                            View All Tasks →
                        </a>
                    </center>
                </div>
                <div class="footer">
                    <p>AI Meeting Assistant | Stay on top of your action items</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {user_name},
        
        New Task Assigned: {task_title}
        Priority: {priority.upper()}
        Assigned to: {assigned_to}
        Deadline: {deadline_str}
        
        From meeting: {meeting_title}
        
        Description:
        {task_description}
        
        View task: {dashboard_url}/tasks
        
        Best regards,
        AI Meeting Assistant Team
        """
        
        message = self._create_message(user_email, subject, html_content, text_content)
        return self._send_email(message)
    
    def send_calendar_sync_notification(
        self,
        user_email: str,
        user_name: str,
        tasks_synced: int,
        calendar_name: str,
        dashboard_url: str
    ) -> bool:
        """Send notification when tasks are synced to Google Calendar"""
        subject = f"📅 {tasks_synced} Tasks Synced to Google Calendar"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4285f4 0%, #34a853 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .success-box {{ background: #d1fae5; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981; text-align: center; }}
                .button {{ display: inline-block; background: #4285f4; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📅 Calendar Sync Complete!</h1>
                    <p>Your tasks are now in Google Calendar</p>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    
                    <div class="success-box">
                        <h2 style="margin: 0; color: #10b981;">✓ Successfully Synced</h2>
                        <p style="font-size: 36px; font-weight: bold; margin: 10px 0; color: #059669;">{tasks_synced}</p>
                        <p style="margin: 0; color: #6b7280;">tasks added to {calendar_name}</p>
                    </div>
                    
                    <p>Your meeting tasks have been automatically added to your Google Calendar with:</p>
                    <ul>
                        <li>✅ Task titles and descriptions</li>
                        <li>✅ Due dates and times</li>
                        <li>✅ Priority levels</li>
                        <li>✅ Meeting context</li>
                    </ul>
                    
                    <p><strong>💡 Pro Tip:</strong> Any changes you make to these tasks in our dashboard will automatically sync back to your calendar!</p>
                    
                    <center>
                        <a href="{dashboard_url}/calendar" class="button">
                            View Calendar →
                        </a>
                    </center>
                </div>
                <div class="footer">
                    <p>AI Meeting Assistant | Seamless calendar integration</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {user_name},
        
        Great news! {tasks_synced} tasks have been successfully synced to your Google Calendar ({calendar_name}).
        
        Your tasks now include:
        - Task titles and descriptions
        - Due dates and times
        - Priority levels
        - Meeting context
        
        View your calendar: {dashboard_url}/calendar
        
        Best regards,
        AI Meeting Assistant Team
        """
        
        message = self._create_message(user_email, subject, html_content, text_content)
        return self._send_email(message)
    
    def send_feature_update_announcement(
        self,
        user_email: str,
        user_name: str,
        feature_title: str,
        feature_description: str,
        features_list: List[str],
        cta_url: str,
        cta_text: str = "Try It Now"
    ) -> bool:
        """Send announcement about new features"""
        subject = f"🚀 New Feature: {feature_title}"
        
        features_html = "".join([f"<li>{feature}</li>" for feature in features_list])
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .feature-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
                ul {{ padding-left: 20px; }}
                li {{ margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 Exciting New Feature!</h1>
                    <p>We've added something special for you</p>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>We're excited to announce a new feature that will make your meetings even more productive!</p>
                    
                    <div class="feature-box">
                        <h2>{feature_title}</h2>
                        <p>{feature_description}</p>
                        
                        <h3>What's New:</h3>
                        <ul>
                            {features_html}
                        </ul>
                    </div>
                    
                    <p>This feature is available to all users starting today. Give it a try and let us know what you think!</p>
                    
                    <center>
                        <a href="{cta_url}" class="button">
                            {cta_text} →
                        </a>
                    </center>
                    
                    <p style="margin-top: 30px; font-size: 14px; color: #6b7280;">
                        Have feedback? We'd love to hear from you! Reply to this email or contact us through the app.
                    </p>
                </div>
                <div class="footer">
                    <p>AI Meeting Assistant | Always improving for you</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        features_text = "\n".join([f"- {feature}" for feature in features_list])
        text_content = f"""
        Hi {user_name},
        
        Exciting news! We've just launched a new feature: {feature_title}
        
        {feature_description}
        
        What's New:
        {features_text}
        
        Try it now: {cta_url}
        
        Best regards,
        AI Meeting Assistant Team
        """
        
        message = self._create_message(user_email, subject, html_content, text_content)
        return self._send_email(message)
    
    def send_weekly_summary(
        self,
        user_email: str,
        user_name: str,
        meetings_count: int,
        tasks_completed: int,
        tasks_pending: int,
        total_meeting_time: int,
        top_meetings: List[Dict],
        dashboard_url: str
    ) -> bool:
        """Send weekly summary of user activity"""
        subject = f"📊 Your Weekly Summary - {meetings_count} Meetings Processed"
        
        meetings_html = ""
        for meeting in top_meetings[:3]:
            meetings_html += f"""
            <div style="background: white; padding: 15px; border-radius: 6px; margin: 10px 0; border-left: 3px solid #667eea;">
                <strong>{meeting['title']}</strong><br>
                <span style="color: #6b7280; font-size: 14px;">
                    {meeting['date']} • {meeting['duration']} min • {meeting['tasks']} tasks
                </span>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }}
                .stat-card {{ background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .stat-number {{ font-size: 32px; font-weight: bold; color: #667eea; }}
                .stat-label {{ font-size: 14px; color: #6b7280; margin-top: 5px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Your Weekly Summary</h1>
                    <p>Here's what you accomplished this week</p>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>Great week! Here's a summary of your meeting activity:</p>
                    
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">{meetings_count}</div>
                            <div class="stat-label">Meetings Processed</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{total_meeting_time}</div>
                            <div class="stat-label">Total Minutes</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{tasks_completed}</div>
                            <div class="stat-label">Tasks Completed</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{tasks_pending}</div>
                            <div class="stat-label">Tasks Pending</div>
                        </div>
                    </div>
                    
                    <h3>📅 Top Meetings This Week:</h3>
                    {meetings_html}
                    
                    <center>
                        <a href="{dashboard_url}/dashboard" class="button">
                            View Full Dashboard →
                        </a>
                    </center>
                    
                    <p style="margin-top: 30px; font-size: 14px; color: #6b7280;">
                        Keep up the great work! 🎉
                    </p>
                </div>
                <div class="footer">
                    <p>AI Meeting Assistant | Your productivity partner</p>
                    <p>You can manage email preferences in your settings.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {user_name},
        
        Your Weekly Summary:
        
        - Meetings Processed: {meetings_count}
        - Total Meeting Time: {total_meeting_time} minutes
        - Tasks Completed: {tasks_completed}
        - Tasks Pending: {tasks_pending}
        
        View full dashboard: {dashboard_url}/dashboard
        
        Keep up the great work!
        
        Best regards,
        AI Meeting Assistant Team
        """
        
        message = self._create_message(user_email, subject, html_content, text_content)
        return self._send_email(message)


# Global email service instance
email_service = EmailService()
