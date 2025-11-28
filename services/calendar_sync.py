import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

class CalendarSyncService:
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.scopes = ['https://www.googleapis.com/auth/calendar']

    def build_service_with_refresh(self, access_token: str, refresh_token: Optional[str] = None) -> Tuple[object, Optional[str]]:
        """
        Build Google Calendar service with automatic token refresh
        
        Returns:
            Tuple of (service, new_access_token) where new_access_token is None if no refresh occurred
        """
        try:
            creds = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes
            )
            
            # Check if credentials are expired and refresh if needed
            if creds.expired and creds.refresh_token:
                logger.info("Access token expired, attempting to refresh...")
                try:
                    creds.refresh(Request())
                    logger.info("✅ Token refreshed successfully")
                    new_access_token = creds.token
                except Exception as refresh_error:
                    logger.error(f"❌ Token refresh failed: {refresh_error}")
                    raise ValueError("Google Calendar access has expired and could not be refreshed. Please reconnect your Google account in the settings.")
            else:
                new_access_token = None
            
            service = build('calendar', 'v3', credentials=creds)
            
            # Test the service by making a simple call
            service.calendarList().list(maxResults=1).execute()
            
            return service, new_access_token
            
        except ValueError:
            # Re-raise ValueError as-is (token refresh issues)
            raise
        except Exception as e:
            error_msg = str(e)
            if 'invalid_grant' in error_msg or 'Token has been expired or revoked' in error_msg:
                logger.error(f"❌ Google Calendar tokens expired and cannot be refreshed: {e}")
                raise ValueError("Google Calendar access has expired. Please reconnect your Google account in the settings.")
            else:
                logger.error(f"❌ Failed to build calendar service: {e}")
                raise ValueError(f"Failed to connect to Google Calendar: {str(e)}")

    def build_service(self, access_token: str, refresh_token: Optional[str] = None):
        """Build Google Calendar service with OAuth credentials (legacy method)"""
        service, _ = self.build_service_with_refresh(access_token, refresh_token)
        return service

    def create_google_calendar_event(self, task: Dict, meeting_title: str, access_token: str, refresh_token: Optional[str] = None) -> Dict:
        try:
            service = self.build_service(access_token, refresh_token)

            # Parse deadline
            deadline_str = task.get('deadline')
            if deadline_str:
                try:
                    if isinstance(deadline_str, str):
                        deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                    else:
                        deadline = deadline_str
                except (ValueError, TypeError):
                    deadline = datetime.now() + timedelta(days=7)
            else:
                deadline = datetime.now() + timedelta(days=7)

            # Create a 30-minute reminder event before the deadline
            event_start = deadline - timedelta(minutes=30)
            event_end = deadline

            # Create event data
            event_data = {
                'summary': f'📋 Task: {task.get("title", "Untitled Task")}',
                'description': self._format_task_description(task, meeting_title),
                'start': {
                    'dateTime': event_start.isoformat(),
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': event_end.isoformat(),
                    'timeZone': 'UTC'
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 60},
                        {'method': 'popup', 'minutes': 15}
                    ]
                },
                'colorId': self._get_priority_color(task.get('priority', 'medium')),
                'source': {
                    'title': 'AI Meeting Assistant',
                    'url': 'https://your-app-domain.com'
                }
            }

            event = service.events().insert(calendarId='primary', body=event_data).execute()

            return {
                'success': True,
                'event_id': event.get('id'),
                'event_link': event.get('htmlLink'),
                'message': f'Task "{task.get("title")}" synced to Google Calendar'
            }

        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8'))
            return {
                'success': False,
                'error': f'Google Calendar API error: {error_details.get("error", {}).get("message", str(e))}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error creating Google Calendar event: {str(e)}'
            }

    def _format_task_description(self, task: Dict, meeting_title: str) -> str:
        """Format task description for calendar event"""
        description_parts = [
            f"🎯 Task from meeting: {meeting_title}",
            "",
            f"📝 Description: {task.get('description', 'No description provided')}",
            f"👤 Assigned to: {task.get('assigned_to', 'Unassigned')}",
            f"⚡ Priority: {task.get('priority', 'medium').upper()}",
            f"📊 Status: {task.get('status', 'pending').upper()}",
            "",
            "🤖 This event was automatically created by AI Meeting Assistant",
            "📅 This is a reminder for your task deadline"
        ]
        return "\n".join(description_parts)
    
    def _get_priority_color(self, priority: str) -> str:
        """Get Google Calendar color ID based on task priority"""
        color_map = {
            'high': '11',    # Red
            'medium': '5',   # Yellow
            'low': '2'       # Green
        }
        return color_map.get(priority.lower(), '5')  # Default to yellow
    
    def sync_multiple_tasks(self, tasks: List[Dict], meeting_title: str, access_token: str, refresh_token: Optional[str] = None) -> Dict:
        """Sync multiple tasks to Google Calendar"""
        results = {
            'success': True,
            'synced_count': 0,
            'failed_count': 0,
            'events': [],
            'errors': []
        }
        
        try:
            service = self.build_service(access_token, refresh_token)
            
            for task in tasks:
                try:
                    sync_result = self.create_google_calendar_event(task, meeting_title, access_token, refresh_token)
                    
                    if sync_result['success']:
                        results['synced_count'] += 1
                        results['events'].append({
                            'task_title': task.get('title'),
                            'event_id': sync_result['event_id'],
                            'event_link': sync_result['event_link']
                        })
                    else:
                        results['failed_count'] += 1
                        results['errors'].append({
                            'task_title': task.get('title'),
                            'error': sync_result['error']
                        })
                        
                except Exception as e:
                    results['failed_count'] += 1
                    results['errors'].append({
                        'task_title': task.get('title', 'Unknown'),
                        'error': str(e)
                    })
            
            if results['failed_count'] > 0:
                results['success'] = False
                
            return results
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to sync tasks to calendar: {str(e)}',
                'synced_count': 0,
                'failed_count': len(tasks)
            }
    
    def update_calendar_event(self, event_id: str, task: Dict, meeting_title: str, access_token: str, refresh_token: Optional[str] = None) -> Dict:
        """Update an existing calendar event"""
        try:
            service = self.build_service(access_token, refresh_token)
            
            # Get existing event
            event = service.events().get(calendarId='primary', eventId=event_id).execute()
            
            # Update event data
            deadline_str = task.get('deadline')
            if deadline_str:
                try:
                    deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    deadline = datetime.now() + timedelta(days=7)
            else:
                deadline = datetime.now() + timedelta(days=7)

            event_start = deadline - timedelta(minutes=30)
            event_end = deadline
            
            event['summary'] = f'📋 Task: {task.get("title", "Untitled Task")}'
            event['description'] = self._format_task_description(task, meeting_title)
            event['start'] = {
                'dateTime': event_start.isoformat(),
                'timeZone': 'UTC'
            }
            event['end'] = {
                'dateTime': event_end.isoformat(),
                'timeZone': 'UTC'
            }
            event['colorId'] = self._get_priority_color(task.get('priority', 'medium'))
            
            # Update the event
            updated_event = service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event
            ).execute()
            
            return {
                'success': True,
                'event_id': updated_event.get('id'),
                'event_link': updated_event.get('htmlLink'),
                'message': f'Task "{task.get("title")}" updated in Google Calendar'
            }
            
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8'))
            return {
                'success': False,
                'error': f'Google Calendar API error: {error_details.get("error", {}).get("message", str(e))}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error updating Google Calendar event: {str(e)}'
            }
    
    def delete_calendar_event(self, event_id: str, access_token: str, refresh_token: Optional[str] = None) -> Dict:
        """Delete a calendar event"""
        try:
            service = self.build_service(access_token, refresh_token)
            
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            
            return {
                'success': True,
                'message': 'Calendar event deleted successfully'
            }
            
        except HttpError as e:
            if e.resp.status == 404:
                return {
                    'success': True,
                    'message': 'Calendar event not found (may have been already deleted)'
                }
            else:
                error_details = json.loads(e.content.decode('utf-8'))
                return {
                    'success': False,
                    'error': f'Google Calendar API error: {error_details.get("error", {}).get("message", str(e))}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error deleting Google Calendar event: {str(e)}'
            }
    
    def test_calendar_access(self, access_token: str, refresh_token: Optional[str] = None) -> Dict:
        """Test if calendar access is working and refresh token if needed"""
        try:
            service, new_access_token = self.build_service_with_refresh(access_token, refresh_token)
            
            # Try to list calendars
            calendar_list = service.calendarList().list(maxResults=1).execute()
            
            result = {
                'success': True,
                'message': 'Google Calendar access is working',
                'calendar_count': len(calendar_list.get('items', []))
            }
            
            # Include new access token if it was refreshed
            if new_access_token:
                result['new_access_token'] = new_access_token
                result['token_refreshed'] = True
                logger.info("✅ Calendar access verified and token refreshed")
            else:
                result['token_refreshed'] = False
                logger.info("✅ Calendar access verified")
            
            return result
            
        except ValueError as e:
            # Handle token expiration specifically
            logger.warning(f"Calendar access failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'TOKEN_EXPIRED',
                'action_required': 'reconnect_google_account'
            }
        except Exception as e:
            logger.error(f"Calendar access test failed: {e}")
            return {
                'success': False,
                'error': f'Calendar access test failed: {str(e)}',
                'error_code': 'CALENDAR_ERROR'
            }

calendar_service = CalendarSyncService()