"""
Email Service for AI Meeting Assistant
Handles sending meeting summaries, timelines, and task notifications to users
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any, Optional
from jinja2 import Template
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_address = os.getenv('EMAIL_ADDRESS')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.from_name = os.getenv('FROM_NAME', 'AI Meeting Assistant')
        
        if not self.email_address or not self.email_password:
            logger.warning("Email credentials not configured. Email notifications will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Email service initialized successfully")

    def send_meeting_summary_email(self, 
                                 user_email: str, 
                                 user_name: str,
                                 meeting_data: Dict[str, Any],
                                 timeline_data: List[Dict[str, Any]],
                                 tasks_data: List[Dict[str, Any]]) -> bool:
        """
        Send a comprehensive meeting summary email to the user
        """
        if not self.enabled:
            logger.warning("Email service not enabled. Skipping email notification.")
            return False

        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Meeting Summary: {meeting_data.get('title', 'Untitled Meeting')}"
            msg['From'] = f"{self.from_name} <{self.email_address}>"
            msg['To'] = user_email

            # Generate HTML content
            html_content = self._generate_meeting_summary_html(
                user_name, meeting_data, timeline_data, tasks_data
            )
            
            # Generate plain text content
            text_content = self._generate_meeting_summary_text(
                user_name, meeting_data, timeline_data, tasks_data
            )

            # Attach both HTML and text versions
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)

            # Send email
            return self._send_email(msg)

        except Exception as e:
            logger.error(f"Failed to send meeting summary email: {str(e)}")
            return False

    def send_task_reminder_email(self, 
                               user_email: str, 
                               user_name: str,
                               tasks: List[Dict[str, Any]]) -> bool:
        """
        Send task reminder email to user
        """
        if not self.enabled:
            logger.warning("Email service not enabled. Skipping task reminder.")
            return False

        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Task Reminders - {len(tasks)} pending tasks"
            msg['From'] = f"{self.from_name} <{self.email_address}>"
            msg['To'] = user_email

            # Generate content
            html_content = self._generate_task_reminder_html(user_name, tasks)
            text_content = self._generate_task_reminder_text(user_name, tasks)

            # Attach both versions
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)

            # Send email
            return self._send_email(msg)

        except Exception as e:
            logger.error(f"Failed to send task reminder email: {str(e)}")
            return False

    def _send_email(self, msg: MIMEMultipart) -> bool:
        """
        Send email using SMTP
        """
        try:
            # Create SMTP session
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable TLS encryption
            server.login(self.email_address, self.email_password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.email_address, msg['To'], text)
            server.quit()
            
            logger.info(f"Email sent successfully to {msg['To']}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False

    def _generate_meeting_summary_html(self, 
                                     user_name: str,
                                     meeting_data: Dict[str, Any],
                                     timeline_data: List[Dict[str, Any]],
                                     tasks_data: List[Dict[str, Any]]) -> str:
        """
        Generate HTML email content for meeting summary
        """
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meeting Summary</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px; }
        .section { background: #f8f9fa; padding: 25px; margin-bottom: 25px; border-radius: 8px; border-left: 4px solid #667eea; }
        .section h2 { color: #667eea; margin-top: 0; font-size: 1.4em; }
        .timeline-item { background: white; padding: 15px; margin-bottom: 15px; border-radius: 6px; border-left: 3px solid #28a745; }
        .timeline-time { font-weight: bold; color: #28a745; font-size: 0.9em; }
        .timeline-title { font-weight: bold; margin: 5px 0; color: #333; }
        .timeline-content { color: #666; }
        .task-item { background: white; padding: 15px; margin-bottom: 10px; border-radius: 6px; border-left: 3px solid #ffc107; }
        .task-priority { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
        .priority-high { background: #dc3545; color: white; }
        .priority-medium { background: #ffc107; color: #333; }
        .priority-low { background: #28a745; color: white; }
        .task-status { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 0.8em; margin-left: 10px; }
        .status-pending { background: #6c757d; color: white; }
        .status-in_progress { background: #007bff; color: white; }
        .status-completed { background: #28a745; color: white; }
        .meeting-info { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .info-card { background: white; padding: 15px; border-radius: 6px; text-align: center; }
        .info-number { font-size: 2em; font-weight: bold; color: #667eea; }
        .info-label { color: #666; font-size: 0.9em; }
        .footer { text-align: center; margin-top: 40px; padding: 20px; color: #666; font-size: 0.9em; }
        .participants { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI Meeting Assistant</h1>
        <h2>Meeting Summary Report</h2>
        <p>Hello {{ user_name }}! Here's your comprehensive meeting summary.</p>
    </div>

    <div class="section">
        <h2>📋 Meeting Overview</h2>
        <h3>{{ meeting_title }}</h3>
        <div class="meeting-info">
            <div class="info-card">
                <div class="info-number">{{ duration_minutes }}</div>
                <div class="info-label">Minutes</div>
            </div>
            <div class="info-card">
                <div class="info-number">{{ timeline_count }}</div>
                <div class="info-label">Timeline Events</div>
            </div>
            <div class="info-card">
                <div class="info-number">{{ task_count }}</div>
                <div class="info-label">Tasks Created</div>
            </div>
        </div>
        <p><strong>Date:</strong> {{ meeting_date }}</p>
        <p><strong>Status:</strong> <span style="color: #28a745;">✅ Processed Successfully</span></p>
    </div>

    {% if timeline_data %}
    <div class="section">
        <h2>⏰ Minute-by-Minute Timeline</h2>
        {% for item in timeline_data %}
        <div class="timeline-item">
            <div class="timeline-time">{{ item.timestamp }} ({{ item.timestamp_minutes }} min)</div>
            <div class="timeline-title">{{ item.title }}</div>
            <div class="timeline-content">{{ item.content }}</div>
            {% if item.participants %}
            <div class="participants">👥 Participants: {{ item.participants | join(', ') }}</div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {% if tasks_data %}
    <div class="section">
        <h2>✅ Action Items & Tasks</h2>
        {% for task in tasks_data %}
        <div class="task-item">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <strong>{{ task.title }}</strong>
                <div>
                    <span class="task-priority priority-{{ task.priority }}">{{ task.priority | upper }}</span>
                    <span class="task-status status-{{ task.status }}">{{ task.status | replace('_', ' ') | title }}</span>
                </div>
            </div>
            {% if task.description %}
            <p>{{ task.description }}</p>
            {% endif %}
            {% if task.assigned_to %}
            <p><strong>Assigned to:</strong> {{ task.assigned_to }}</p>
            {% endif %}
            {% if task.deadline %}
            <p><strong>Deadline:</strong> {{ task.deadline }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="footer">
        <p>This summary was automatically generated by AI Meeting Assistant</p>
        <p>📧 You're receiving this because you have email notifications enabled</p>
        <p>🔧 Manage your notification preferences in Settings</p>
    </div>
</body>
</html>
        """

        template = Template(html_template)
        return template.render(
            user_name=user_name,
            meeting_title=meeting_data.get('title', 'Untitled Meeting'),
            meeting_date=meeting_data.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M')),
            duration_minutes=meeting_data.get('duration', 0),
            timeline_count=len(timeline_data),
            task_count=len(tasks_data),
            timeline_data=timeline_data,
            tasks_data=tasks_data
        )

    def _generate_meeting_summary_text(self, 
                                     user_name: str,
                                     meeting_data: Dict[str, Any],
                                     timeline_data: List[Dict[str, Any]],
                                     tasks_data: List[Dict[str, Any]]) -> str:
        """
        Generate plain text email content for meeting summary
        """
        text_content = f"""
AI MEETING ASSISTANT - MEETING SUMMARY
=====================================

Hello {user_name}!

Here's your comprehensive meeting summary:

MEETING OVERVIEW
---------------
Title: {meeting_data.get('title', 'Untitled Meeting')}
Date: {meeting_data.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M'))}
Duration: {meeting_data.get('duration', 0)} minutes
Timeline Events: {len(timeline_data)}
Tasks Created: {len(tasks_data)}
Status: ✅ Processed Successfully

"""

        if timeline_data:
            text_content += "\nMINUTE-BY-MINUTE TIMELINE\n"
            text_content += "========================\n\n"
            for item in timeline_data:
                text_content += f"⏰ {item.get('timestamp', '')} ({item.get('timestamp_minutes', 0)} min)\n"
                text_content += f"📋 {item.get('title', '')}\n"
                text_content += f"💬 {item.get('content', '')}\n"
                if item.get('participants'):
                    text_content += f"👥 Participants: {', '.join(item['participants'])}\n"
                text_content += "\n" + "-" * 50 + "\n\n"

        if tasks_data:
            text_content += "\nACTION ITEMS & TASKS\n"
            text_content += "===================\n\n"
            for task in tasks_data:
                text_content += f"✅ {task.get('title', '')}\n"
                text_content += f"   Priority: {task.get('priority', 'medium').upper()}\n"
                text_content += f"   Status: {task.get('status', 'pending').replace('_', ' ').title()}\n"
                if task.get('description'):
                    text_content += f"   Description: {task['description']}\n"
                if task.get('assigned_to'):
                    text_content += f"   Assigned to: {task['assigned_to']}\n"
                if task.get('deadline'):
                    text_content += f"   Deadline: {task['deadline']}\n"
                text_content += "\n"

        text_content += """
---
This summary was automatically generated by AI Meeting Assistant
📧 You're receiving this because you have email notifications enabled
🔧 Manage your notification preferences in Settings
"""

        return text_content

    def _generate_task_reminder_html(self, user_name: str, tasks: List[Dict[str, Any]]) -> str:
        """Generate HTML for task reminder email"""
        # Similar structure to meeting summary but focused on tasks
        # Implementation would be similar to above
        return f"<h1>Task Reminders for {user_name}</h1><!-- Task reminder HTML -->"

    def _generate_task_reminder_text(self, user_name: str, tasks: List[Dict[str, Any]]) -> str:
        """Generate plain text for task reminder email"""
        return f"Task Reminders for {user_name}\n\n<!-- Task reminder text -->"

    def get_email_health(self) -> Dict[str, Any]:
        """
        Check email service health
        """
        return {
            'service': 'email_service',
            'status': 'healthy' if self.enabled else 'disabled',
            'smtp_server': self.smtp_server,
            'smtp_port': self.smtp_port,
            'email_configured': bool(self.email_address),
            'from_name': self.from_name
        }

# Create global email service instance
email_service = EmailService()
