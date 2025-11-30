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
    
    def send_2fa_email_code(
        self,
        user_email: str,
        code: str
    ) -> bool:
        """Send 2FA verification code via email"""
        subject = f"🔐 Your Verification Code: {code}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .code-box {{ background: white; padding: 30px; border-radius: 8px; margin: 20px 0; text-align: center; border: 2px dashed #667eea; }}
                .code {{ font-size: 48px; font-weight: bold; color: #667eea; letter-spacing: 8px; font-family: monospace; }}
                .warning-box {{ background: #fef3c7; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Verification Code</h1>
                    <p>Two-Factor Authentication</p>
                </div>
                <div class="content">
                    <p>Your verification code for AI Meeting Assistant is:</p>
                    
                    <div class="code-box">
                        <div class="code">{code}</div>
                        <p style="color: #6b7280; font-size: 14px; margin-top: 10px;">Valid for 10 minutes</p>
                    </div>
                    
                    <p>Enter this code in the application to complete your verification.</p>
                    
                    <div class="warning-box">
                        <strong>⚠️ Security Notice:</strong><br>
                        Never share this code with anyone. Our team will never ask for your verification code.
                    </div>
                    
                    <p style="font-size: 14px; color: #6b7280;">
                        If you didn't request this code, please ignore this email or contact support if you're concerned about your account security.
                    </p>
                </div>
                <div class="footer">
                    <p>AI Meeting Assistant | Secure Authentication</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Your verification code for AI Meeting Assistant is: {code}
        
        This code is valid for 10 minutes.
        
        If you didn't request this code, please ignore this email.
        
        Best regards,
        AI Meeting Assistant Team
        """
        
        message = self._create_message(user_email, subject, html_content, text_content)
        return self._send_email(message)
    
    def send_2fa_enabled_notification(
        self,
        user_email: str,
        user_name: str,
        method: str
    ) -> bool:
        """Send notification when 2FA is enabled"""
        method_names = {
            '2fa_email': 'Email',
            '2fa_sms': 'SMS',
            '2fa_app': 'Authenticator App'
        }
        method_name = method_names.get(method, method)
        
        subject = "🔐 Two-Factor Authentication Enabled"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .success-box {{ background: #d1fae5; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981; }}
                .info-box {{ background: #dbeafe; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #3b82f6; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 2FA Enabled Successfully!</h1>
                    <p>Your account is now more secure</p>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    
                    <div class="success-box">
                        <h3 style="margin: 0 0 10px 0; color: #059669;">✓ Two-Factor Authentication Active</h3>
                        <p style="margin: 0; color: #6b7280;">Method: <strong>{method_name}</strong></p>
                    </div>
                    
                    <p>Your account now has an extra layer of security. You'll need to verify your identity with a code each time you log in.</p>
                    
                    <div class="info-box">
                        <strong>💡 What This Means:</strong><br>
                        • Enhanced account security<br>
                        • Protection against unauthorized access<br>
                        • Verification required at each login<br>
                        • You can change your 2FA method anytime in Settings
                    </div>
                    
                    <p><strong>Didn't enable 2FA?</strong> If you didn't make this change, please contact support immediately.</p>
                </div>
                <div class="footer">
                    <p>AI Meeting Assistant | Account Security</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {user_name},
        
        Two-Factor Authentication has been successfully enabled on your account.
        
        Method: {method_name}
        
        Your account now has an extra layer of security. You'll need to verify your identity with a code each time you log in.
        
        If you didn't make this change, please contact support immediately.
        
        Best regards,
        AI Meeting Assistant Team
        """
        
        message = self._create_message(user_email, subject, html_content, text_content)
        return self._send_email(message)
    
    def send_data_export_notification(
        self,
        user_email: str,
        user_name: str,
        download_url: str,
        expires_in_hours: int = 24,
        meetings_count: int = 0,
        tasks_count: int = 0,
        timeline_events_count: int = 0
    ) -> bool:
        """Send notification with data export download link including detailed statistics"""
        subject = "📦 Your Analytics Export is Ready"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .download-box {{ background: white; padding: 30px; border-radius: 8px; margin: 20px 0; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .stats-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .stat-item {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e5e7eb; }}
                .stat-item:last-child {{ border-bottom: none; }}
                .stat-label {{ color: #6b7280; }}
                .stat-value {{ font-weight: bold; color: #667eea; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 40px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
                .warning-box {{ background: #fef3c7; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Analytics Export Ready!</h1>
                    <p>Your comprehensive data export is ready to download</p>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>Your analytics export has been prepared with comprehensive meeting data, tasks, and timeline events.</p>
                    
                    <div class="stats-box">
                        <h3 style="margin: 0 0 15px 0; color: #667eea;">📈 Export Summary</h3>
                        <div class="stat-item">
                            <span class="stat-label">Total Meetings</span>
                            <span class="stat-value">{meetings_count}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Extracted Tasks</span>
                            <span class="stat-value">{tasks_count}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Timeline Events</span>
                            <span class="stat-value">{timeline_events_count}</span>
                        </div>
                    </div>
                    
                    <div class="download-box">
                        <h2 style="margin: 0 0 20px 0;">📦 Your Export Includes:</h2>
                        <ul style="text-align: left; display: inline-block; margin: 0;">
                            <li><strong>Meeting Analytics Dashboard</strong> - Visual charts and key metrics</li>
                            <li><strong>Meeting Details</strong> - All transcriptions with dates and durations</li>
                            <li><strong>Extracted Tasks</strong> - Complete task list with priorities and deadlines</li>
                            <li><strong>Timeline Events</strong> - Key moments and important discussions</li>
                            <li><strong>Productivity Insights</strong> - AI-generated recommendations</li>
                            <li><strong>Resource Usage</strong> - Storage and processing metrics</li>
                        </ul>
                        
                        <a href="{download_url}" class="button">
                            📥 Download PDF Report →
                        </a>
                    </div>
                    
                    <div class="warning-box">
                        <strong>⏰ Important:</strong><br>
                        This download link will expire in {expires_in_hours} hours for security reasons.
                    </div>
                    
                    <p style="font-size: 14px; color: #6b7280;">
                        💡 <strong>Tip:</strong> The export is in professional PDF format with visual charts, 
                        making it perfect for sharing with your team or keeping records of your productivity.
                    </p>
                </div>
                <div class="footer">
                    <p>AI Meeting Assistant | Comprehensive Analytics & Data Privacy</p>
                    <p>Your data is always secure and private.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {user_name},
        
        Your analytics export is ready for download!
        
        Export Summary:
        - Total Meetings: {meetings_count}
        - Extracted Tasks: {tasks_count}
        - Timeline Events: {timeline_events_count}
        
        Your export includes:
        - Meeting Analytics Dashboard with visual charts
        - Complete meeting details with transcriptions
        - Extracted tasks with priorities and deadlines
        - Timeline events with key moments
        - Productivity insights and recommendations
        - Resource usage metrics
        
        Download link: {download_url}
        
        This link will expire in {expires_in_hours} hours.
        
        The export is in professional PDF format, perfect for sharing or record-keeping.
        
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
