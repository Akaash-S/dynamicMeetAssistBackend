"""
Notification scheduler for checking due tasks and creating notifications
"""
from datetime import datetime, timedelta
from config.aws_rds_database import rds_db
from routes.notifications import create_notification

def check_due_tasks():
    """Check for tasks that are due soon or overdue and create notifications"""
    try:
        # Get tasks due in the next 24 hours
        due_soon_query = """
        SELECT t.*, u.id as user_id, m.title as meeting_title
        FROM tasks t
        JOIN meetings m ON t.meeting_id = m.id
        JOIN users u ON t.user_id = u.id
        WHERE t.deadline IS NOT NULL
        AND t.deadline BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
        AND t.status != 'completed'
        AND NOT EXISTS (
            SELECT 1 FROM notifications n
            WHERE n.type = 'task_due_soon'
            AND n.data->>'task_id' = t.id::text
            AND n.created_at > NOW() - INTERVAL '24 hours'
        )
        """
        
        due_soon_tasks = rds_db.execute_query(due_soon_query, fetch_all=True)
        
        for task in due_soon_tasks or []:
            hours_until = int((task['deadline'] - datetime.now()).total_seconds() / 3600)
            create_notification(
                user_id=task['user_id'],
                notification_type='task_due_soon',
                title='Task Due Soon',
                message=f'"{task["title"]}" is due in {hours_until} hours',
                data={
                    'task_id': task['id'],
                    'meeting_id': task['meeting_id'],
                    'deadline': task['deadline'].isoformat(),
                    'hours_until': hours_until
                }
            )
        
        print(f"✅ Created {len(due_soon_tasks or [])} due soon notifications")
        
        # Get overdue tasks
        overdue_query = """
        SELECT t.*, u.id as user_id, m.title as meeting_title
        FROM tasks t
        JOIN meetings m ON t.meeting_id = m.id
        JOIN users u ON t.user_id = u.id
        WHERE t.deadline IS NOT NULL
        AND t.deadline < NOW()
        AND t.status != 'completed'
        AND NOT EXISTS (
            SELECT 1 FROM notifications n
            WHERE n.type = 'task_overdue'
            AND n.data->>'task_id' = t.id::text
            AND n.created_at > NOW() - INTERVAL '24 hours'
        )
        """
        
        overdue_tasks = rds_db.execute_query(overdue_query, fetch_all=True)
        
        for task in overdue_tasks or []:
            days_overdue = (datetime.now() - task['deadline']).days
            create_notification(
                user_id=task['user_id'],
                notification_type='task_overdue',
                title='Task Overdue',
                message=f'"{task["title"]}" is {days_overdue} days overdue',
                data={
                    'task_id': task['id'],
                    'meeting_id': task['meeting_id'],
                    'deadline': task['deadline'].isoformat(),
                    'days_overdue': days_overdue
                }
            )
        
        print(f"✅ Created {len(overdue_tasks or [])} overdue notifications")
        
        return {
            'success': True,
            'due_soon_count': len(due_soon_tasks or []),
            'overdue_count': len(overdue_tasks or [])
        }
        
    except Exception as e:
        print(f"❌ Error checking due tasks: {e}")
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == '__main__':
    # Can be run as a cron job or scheduled task
    result = check_due_tasks()
    print(f"Task notification check result: {result}")
