#!/usr/bin/env python3
"""
Demo Data Creator for AI Meeting Assistant
Creates sample data to test the frontend data fetching functionality
"""

import os
import sys
from datetime import datetime, timedelta
import json

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import Database

def create_demo_data():
    """Create demo data for testing frontend data fetching"""
    db = Database()
    
    print("🚀 Creating demo data for AI Meeting Assistant...")
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Create a demo user
            print("👤 Creating demo user...")
            demo_user_data = {
                'firebase_uid': 'demo_user_12345',
                'email': 'demo@example.com',
                'name': 'Demo User'
            }
            
            cursor.execute("""
                INSERT INTO users (firebase_uid, email, name, created_at, updated_at)
                VALUES (%(firebase_uid)s, %(email)s, %(name)s, NOW(), NOW())
                ON CONFLICT (firebase_uid) DO UPDATE SET
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    updated_at = NOW()
                RETURNING id
            """, demo_user_data)
            
            user_result = cursor.fetchone()
            user_id = user_result[0]
            print(f"✅ Demo user created with ID: {user_id}")
            
            # 2. Create demo meetings
            print("📅 Creating demo meetings...")
            meetings_data = [
                {
                    'user_id': user_id,
                    'title': 'Weekly Team Standup',
                    'status': 'completed',
                    'duration': 1800,  # 30 minutes
                    'file_size': 15728640,  # 15MB
                    'audio_url': 'https://demo-storage.com/meeting1.mp3',
                    'transcript': 'This was our weekly standup meeting. We discussed project progress, blockers, and next steps.',
                    'summary': 'Team discussed current sprint progress. Main blockers identified in API integration. Next steps include completing user authentication and setting up deployment pipeline.',
                    'created_at': datetime.now() - timedelta(days=2)
                },
                {
                    'user_id': user_id,
                    'title': 'Product Planning Session',
                    'status': 'completed',
                    'duration': 3600,  # 60 minutes
                    'file_size': 31457280,  # 30MB
                    'audio_url': 'https://demo-storage.com/meeting2.mp3',
                    'transcript': 'Product planning session covering Q4 roadmap, feature priorities, and resource allocation.',
                    'summary': 'Discussed Q4 product roadmap. Prioritized user dashboard improvements and mobile app development. Allocated resources for new AI features.',
                    'created_at': datetime.now() - timedelta(days=5)
                },
                {
                    'user_id': user_id,
                    'title': 'Client Feedback Review',
                    'status': 'completed',
                    'duration': 2700,  # 45 minutes
                    'file_size': 23592960,  # 22.5MB
                    'audio_url': 'https://demo-storage.com/meeting3.mp3',
                    'transcript': 'Review of client feedback from recent product demo. Discussion of requested features and implementation timeline.',
                    'summary': 'Reviewed client feedback. Positive response to new features. Clients requested better reporting capabilities and mobile notifications.',
                    'created_at': datetime.now() - timedelta(days=7)
                }
            ]
            
            meeting_ids = []
            for meeting_data in meetings_data:
                cursor.execute("""
                    INSERT INTO meetings (user_id, title, status, duration, file_size, audio_url, transcript, summary, created_at, updated_at)
                    VALUES (%(user_id)s, %(title)s, %(status)s, %(duration)s, %(file_size)s, %(audio_url)s, %(transcript)s, %(summary)s, %(created_at)s, NOW())
                    RETURNING id
                """, meeting_data)
                
                meeting_result = cursor.fetchone()
                meeting_ids.append(meeting_result[0])
                print(f"✅ Meeting '{meeting_data['title']}' created with ID: {meeting_result[0]}")
            
            # 3. Create demo timeline entries
            print("⏰ Creating demo timeline entries...")
            timeline_data = [
                # Meeting 1 timeline
                {
                    'meeting_id': meeting_ids[0],
                    'timestamp': '00:02:30',
                    'timestamp_minutes': 2.5,
                    'event_type': 'discussion',
                    'title': 'Sprint Progress Review',
                    'content': 'Team discussed current sprint progress, completed 8 out of 12 story points.',
                    'participants': json.dumps(['John Doe', 'Jane Smith', 'Mike Johnson'])
                },
                {
                    'meeting_id': meeting_ids[0],
                    'timestamp': '00:15:45',
                    'timestamp_minutes': 15.75,
                    'event_type': 'task_assignment',
                    'title': 'API Integration Task',
                    'content': 'Assigned API integration task to John for completion by Friday.',
                    'participants': json.dumps(['John Doe', 'Team Lead'])
                },
                {
                    'meeting_id': meeting_ids[0],
                    'timestamp': '00:25:10',
                    'timestamp_minutes': 25.17,
                    'event_type': 'decision',
                    'title': 'Deployment Pipeline Decision',
                    'content': 'Decided to implement automated deployment pipeline using GitHub Actions.',
                    'participants': json.dumps(['Jane Smith', 'DevOps Team'])
                },
                # Meeting 2 timeline
                {
                    'meeting_id': meeting_ids[1],
                    'timestamp': '00:10:00',
                    'timestamp_minutes': 10,
                    'event_type': 'presentation',
                    'title': 'Q4 Roadmap Presentation',
                    'content': 'Presented Q4 roadmap including dashboard improvements and mobile app development.',
                    'participants': json.dumps(['Product Manager', 'Development Team'])
                },
                {
                    'meeting_id': meeting_ids[1],
                    'timestamp': '00:35:30',
                    'timestamp_minutes': 35.5,
                    'event_type': 'decision',
                    'title': 'Resource Allocation',
                    'content': 'Allocated 3 developers for AI features and 2 for mobile development.',
                    'participants': json.dumps(['Product Manager', 'Tech Lead'])
                }
            ]
            
            for timeline_entry in timeline_data:
                cursor.execute("""
                    INSERT INTO timeline_entries (meeting_id, timestamp, timestamp_minutes, event_type, title, content, participants, created_at)
                    VALUES (%(meeting_id)s, %(timestamp)s, %(timestamp_minutes)s, %(event_type)s, %(title)s, %(content)s, %(participants)s, NOW())
                """, timeline_entry)
            
            print(f"✅ Created {len(timeline_data)} timeline entries")
            
            # 4. Create demo tasks
            print("📋 Creating demo tasks...")
            tasks_data = [
                {
                    'meeting_id': meeting_ids[0],
                    'title': 'Complete API Integration',
                    'description': 'Integrate third-party payment API with our backend system',
                    'assigned_to': 'John Doe',
                    'deadline': datetime.now() + timedelta(days=3),
                    'priority': 'high',
                    'status': 'in_progress'
                },
                {
                    'meeting_id': meeting_ids[0],
                    'title': 'Set up Deployment Pipeline',
                    'description': 'Configure GitHub Actions for automated deployment',
                    'assigned_to': 'Jane Smith',
                    'deadline': datetime.now() + timedelta(days=5),
                    'priority': 'medium',
                    'status': 'pending'
                },
                {
                    'meeting_id': meeting_ids[1],
                    'title': 'Design Mobile App UI',
                    'description': 'Create wireframes and mockups for mobile application',
                    'assigned_to': 'UI/UX Team',
                    'deadline': datetime.now() + timedelta(days=10),
                    'priority': 'medium',
                    'status': 'pending'
                },
                {
                    'meeting_id': meeting_ids[1],
                    'title': 'Research AI Features',
                    'description': 'Research and document AI features for Q4 implementation',
                    'assigned_to': 'Research Team',
                    'deadline': datetime.now() + timedelta(days=7),
                    'priority': 'low',
                    'status': 'pending'
                },
                {
                    'meeting_id': meeting_ids[2],
                    'title': 'Implement Reporting Dashboard',
                    'description': 'Build comprehensive reporting dashboard based on client feedback',
                    'assigned_to': 'Frontend Team',
                    'deadline': datetime.now() + timedelta(days=14),
                    'priority': 'high',
                    'status': 'pending'
                },
                {
                    'meeting_id': meeting_ids[2],
                    'title': 'Add Mobile Notifications',
                    'description': 'Implement push notifications for mobile app',
                    'assigned_to': 'Mobile Team',
                    'deadline': datetime.now() + timedelta(days=12),
                    'priority': 'medium',
                    'status': 'pending'
                }
            ]
            
            for task_data in tasks_data:
                cursor.execute("""
                    INSERT INTO tasks (meeting_id, title, description, assigned_to, deadline, priority, status, created_at, updated_at)
                    VALUES (%(meeting_id)s, %(title)s, %(description)s, %(assigned_to)s, %(deadline)s, %(priority)s, %(status)s, NOW(), NOW())
                """, task_data)
            
            print(f"✅ Created {len(tasks_data)} tasks")
            
            # Update meeting stats
            print("📊 Updating meeting statistics...")
            for meeting_id in meeting_ids:
                # Update task count
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE meeting_id = %s", (meeting_id,))
                task_count = cursor.fetchone()[0]
                
                # Update timeline count
                cursor.execute("SELECT COUNT(*) FROM timeline_entries WHERE meeting_id = %s", (meeting_id,))
                timeline_count = cursor.fetchone()[0]
                
                # Update meeting with counts
                cursor.execute("""
                    UPDATE meetings 
                    SET task_count = %s, timeline_count = %s, updated_at = NOW()
                    WHERE id = %s
                """, (task_count, timeline_count, meeting_id))
            
            conn.commit()
            print("✅ Meeting statistics updated")
            
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        return False
    
    print("\n🎉 Demo data created successfully!")
    print("\n📋 Demo Data Summary:")
    print(f"👤 User: {demo_user_data['name']} ({demo_user_data['email']})")
    print(f"📅 Meetings: {len(meetings_data)} completed meetings")
    print(f"⏰ Timeline Entries: {len(timeline_data)} entries")
    print(f"📋 Tasks: {len(tasks_data)} tasks with various priorities and deadlines")
    print(f"\n🔑 Demo User Details:")
    print(f"   Firebase UID: {demo_user_data['firebase_uid']}")
    print(f"   Database ID: {user_id}")
    print(f"   Email: {demo_user_data['email']}")
    
    print("\n🚀 You can now test the frontend with this demo data!")
    print("   1. Use the demo user credentials for authentication")
    print("   2. Visit Dashboard to see recent meetings")
    print("   3. Go to Tasks page to see extracted tasks")
    print("   4. Check Timeline page for meeting timelines")
    print("   5. View Calendar page for tasks with deadlines")
    
    return True

if __name__ == "__main__":
    create_demo_data()
