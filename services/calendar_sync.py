import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

class CalendarSyncService:
    def __init__(self):
        # For now, we'll implement a simple calendar service
        # In production, you can integrate with Google Calendar, Outlook, etc.
        self.calendar_events = []  # In-memory storage for demo
    
    def create_task_events(self, tasks: List[Dict], meeting_title: str) -> Dict:
        """
        Create calendar events for extracted tasks
        """
        try:
            created_events = []
            
            for task in tasks:
                event = self._create_calendar_event(task, meeting_title)
                if event:
                    created_events.append(event)
            
            print(f"📅 Created {len(created_events)} calendar events")
            
            return {
                'success': True,
                'events_created': len(created_events),
                'events': created_events
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Calendar sync error: {str(e)}'
            }
    
    def _create_calendar_event(self, task: Dict, meeting_title: str) -> Optional[Dict]:
        """
        Create a single calendar event for a task
        """
        try:
            # Parse deadline
            deadline_str = task.get('deadline')
            if deadline_str:
                try:
                    deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                except ValueError:
                    # Try different date formats
                    try:
                        deadline = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        deadline = datetime.now() + timedelta(days=7)  # Default to 1 week
            else:
                deadline = datetime.now() + timedelta(days=7)
            
            # Create event data
            event = {
                'id': f"task_{len(self.calendar_events) + 1}",
                'title': f"📋 {task.get('title', 'Untitled Task')}",
                'description': self._format_task_description(task, meeting_title),
                'start_time': deadline.replace(hour=9, minute=0),  # Default to 9 AM
                'end_time': deadline.replace(hour=10, minute=0),   # 1 hour duration
                'all_day': False,
                'priority': task.get('priority', 'medium'),
                'assigned_to': task.get('assigned_to', 'Unassigned'),
                'task_id': task.get('id'),
                'meeting_title': meeting_title,
                'created_at': datetime.now().isoformat()
            }
            
            # Add to our in-memory storage
            self.calendar_events.append(event)
            
            return event
            
        except Exception as e:
            print(f"❌ Error creating calendar event: {e}")
            return None
    
    def _format_task_description(self, task: Dict, meeting_title: str) -> str:
        """
        Format task description for calendar event
        """
        description_parts = [
            f"Task from meeting: {meeting_title}",
            "",
            f"Description: {task.get('description', 'No description provided')}",
            f"Assigned to: {task.get('assigned_to', 'Unassigned')}",
            f"Priority: {task.get('priority', 'medium').upper()}",
            f"Status: {task.get('status', 'pending').upper()}"
        ]
        
        if task.get('dependencies'):
            description_parts.extend([
                "",
                "Dependencies:",
                *[f"• {dep}" for dep in task['dependencies']]
            ])
        
        if task.get('estimated_hours'):
            description_parts.extend([
                "",
                f"Estimated time: {task['estimated_hours']} hours"
            ])
        
        return "\n".join(description_parts)
    
    def get_upcoming_tasks(self, days_ahead: int = 30) -> List[Dict]:
        """
        Get upcoming task events
        """
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        
        upcoming = [
            event for event in self.calendar_events
            if datetime.fromisoformat(event['start_time'].replace('Z', '+00:00')) <= cutoff_date
        ]
        
        # Sort by start time
        upcoming.sort(key=lambda x: x['start_time'])
        
        return upcoming
    
    def update_task_status(self, task_id: str, status: str) -> Dict:
        """
        Update task status in calendar
        """
        try:
            for event in self.calendar_events:
                if event.get('task_id') == task_id:
                    # Update event title to reflect status
                    if status == 'completed':
                        event['title'] = f"✅ {event['title'].replace('📋 ', '').replace('✅ ', '')}"
                    elif status == 'in_progress':
                        event['title'] = f"🔄 {event['title'].replace('📋 ', '').replace('🔄 ', '')}"
                    else:
                        event['title'] = f"📋 {event['title'].replace('📋 ', '').replace('✅ ', '').replace('🔄 ', '')}"
                    
                    event['updated_at'] = datetime.now().isoformat()
                    
                    return {
                        'success': True,
                        'message': f'Task status updated to {status}'
                    }
            
            return {
                'success': False,
                'error': 'Task not found in calendar'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error updating task status: {str(e)}'
            }
    
    def delete_task_event(self, task_id: str) -> Dict:
        """
        Delete task event from calendar
        """
        try:
            original_count = len(self.calendar_events)
            self.calendar_events = [
                event for event in self.calendar_events
                if event.get('task_id') != task_id
            ]
            
            deleted_count = original_count - len(self.calendar_events)
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Deleted {deleted_count} calendar event(s)'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error deleting task event: {str(e)}'
            }
    
    def integrate_google_calendar(self, credentials: Dict) -> Dict:
        """
        Future implementation for Google Calendar integration
        """
        # This would integrate with Google Calendar API
        # For now, return a placeholder response
        return {
            'success': False,
            'error': 'Google Calendar integration not implemented yet',
            'message': 'Using in-memory calendar for demo purposes'
        }
    
    def integrate_outlook_calendar(self, credentials: Dict) -> Dict:
        """
        Future implementation for Outlook Calendar integration
        """
        # This would integrate with Microsoft Graph API
        # For now, return a placeholder response
        return {
            'success': False,
            'error': 'Outlook Calendar integration not implemented yet',
            'message': 'Using in-memory calendar for demo purposes'
        }
    
    def get_calendar_health(self) -> Dict:
        """Check if calendar service is healthy"""
        try:
            return {
                'service': 'calendar_sync',
                'status': 'healthy',
                'events_count': len(self.calendar_events),
                'integrations': {
                    'google_calendar': 'not_configured',
                    'outlook_calendar': 'not_configured',
                    'in_memory_storage': 'active'
                }
            }
            
        except Exception as e:
            return {
                'service': 'calendar_sync',
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def export_calendar_data(self) -> Dict:
        """
        Export calendar data for debugging or migration
        """
        return {
            'total_events': len(self.calendar_events),
            'events': self.calendar_events,
            'export_timestamp': datetime.now().isoformat()
        }

# Global calendar sync service instance
calendar_service = CalendarSyncService()
