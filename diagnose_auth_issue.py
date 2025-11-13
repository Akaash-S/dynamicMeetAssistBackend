"""
Diagnostic script to identify authentication and data fetching issues
"""

import os
import sys
import time
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables FIRST before importing anything else
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

print(f"📁 Loading .env from: {env_path}")
print(f"   File exists: {env_path.exists()}\n")

# Now import after env vars are loaded
from config.aws_rds_database import rds_db

def force_reinitialize_db():
    """Force reinitialize the database connection with current env vars"""
    print("⏳ Initializing database connection...")
    
    # Reload the database configuration with current environment variables
    rds_db.db_host = os.getenv('RDS_HOST')
    rds_db.db_port = os.getenv('RDS_PORT', '5432')
    rds_db.db_name = os.getenv('RDS_DATABASE')
    rds_db.db_user = os.getenv('RDS_USER')
    rds_db.db_password = os.getenv('RDS_PASSWORD')
    rds_db.db_ssl_mode = os.getenv('RDS_SSL_MODE', 'prefer')
    
    print(f"   Connecting to: {rds_db.db_host}:{rds_db.db_port}/{rds_db.db_name}")
    
    # Close existing pool if any
    if rds_db.connection_pool:
        try:
            rds_db.connection_pool.closeall()
        except:
            pass
        rds_db.connection_pool = None
    
    # Initialize new pool
    try:
        rds_db._initialize_pool()
        if rds_db.connection_pool:
            print("✅ Connection pool initialized successfully")
            return True
        else:
            print("❌ Connection pool initialization failed")
            return False
    except Exception as e:
        print(f"❌ Connection pool initialization failed: {e}")
        return False

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def check_users():
    """Check all users in the database"""
    print_header("USERS IN DATABASE")
    
    try:
        query = """
        SELECT id, firebase_uid, google_oauth_id, email, name, auth_provider, 
               created_at, updated_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 10
        """
        users = rds_db.execute_query(query, fetch_all=True)
        
        if not users:
            print("❌ No users found in database")
            return
        
        print(f"✅ Found {len(users)} users (showing last 10):\n")
        
        for i, user in enumerate(users, 1):
            print(f"{i}. {user['email']}")
            print(f"   ID: {user['id']}")
            print(f"   Firebase UID: {user.get('firebase_uid', 'None')}")
            print(f"   Google OAuth ID: {user.get('google_oauth_id', 'None')}")
            print(f"   Auth Provider: {user.get('auth_provider', 'None')}")
            print(f"   Created: {user.get('created_at', 'None')}")
            print()
            
    except Exception as e:
        print(f"❌ Error checking users: {e}")

def check_meetings():
    """Check meetings in the database"""
    print_header("MEETINGS IN DATABASE")
    
    try:
        query = """
        SELECT m.id, m.title, m.user_id, u.email as user_email, m.created_at
        FROM meetings m
        LEFT JOIN users u ON m.user_id = u.id
        ORDER BY m.created_at DESC
        LIMIT 10
        """
        meetings = rds_db.execute_query(query, fetch_all=True)
        
        if not meetings:
            print("❌ No meetings found in database")
            return
        
        print(f"✅ Found {len(meetings)} meetings (showing last 10):\n")
        
        for i, meeting in enumerate(meetings, 1):
            print(f"{i}. {meeting['title']}")
            print(f"   Meeting ID: {meeting['id']}")
            print(f"   User ID: {meeting['user_id']}")
            print(f"   User Email: {meeting.get('user_email', 'Unknown')}")
            print(f"   Created: {meeting.get('created_at', 'None')}")
            print()
            
    except Exception as e:
        print(f"❌ Error checking meetings: {e}")

def check_tasks():
    """Check tasks in the database"""
    print_header("TASKS IN DATABASE")
    
    try:
        query = """
        SELECT t.id, t.title, t.user_id, u.email as user_email, t.created_at
        FROM tasks t
        LEFT JOIN users u ON t.user_id = u.id
        ORDER BY t.created_at DESC
        LIMIT 10
        """
        tasks = rds_db.execute_query(query, fetch_all=True)
        
        if not tasks:
            print("❌ No tasks found in database")
            return
        
        print(f"✅ Found {len(tasks)} tasks (showing last 10):\n")
        
        for i, task in enumerate(tasks, 1):
            print(f"{i}. {task['title']}")
            print(f"   Task ID: {task['id']}")
            print(f"   User ID: {task['user_id']}")
            print(f"   User Email: {task.get('user_email', 'Unknown')}")
            print(f"   Created: {task.get('created_at', 'None')}")
            print()
            
    except Exception as e:
        print(f"❌ Error checking tasks: {e}")

def check_user_data_relationship(email=None):
    """Check if a specific user has data"""
    if not email:
        print_header("CHECKING USER-DATA RELATIONSHIPS")
        print("Skipping (no email provided)")
        return
    
    print_header(f"CHECKING DATA FOR USER: {email}")
    
    try:
        # Get user
        user_query = "SELECT id, firebase_uid, email FROM users WHERE email = %s"
        users = rds_db.execute_query(user_query, (email,), fetch_all=True)
        
        if not users:
            print(f"❌ User not found: {email}")
            return
        
        user = users[0]
        user_id = user['id']
        
        print(f"✅ User found:")
        print(f"   ID: {user_id}")
        print(f"   Firebase UID: {user.get('firebase_uid', 'None')}")
        print(f"   Email: {user['email']}")
        print()
        
        # Check meetings
        meetings_query = "SELECT COUNT(*) as count FROM meetings WHERE user_id = %s"
        meetings_result = rds_db.execute_query(meetings_query, (user_id,), fetch_one=True)
        meeting_count = meetings_result[0]['count'] if meetings_result else 0
        print(f"   Meetings: {meeting_count}")
        
        # Check tasks
        tasks_query = "SELECT COUNT(*) as count FROM tasks WHERE user_id = %s"
        tasks_result = rds_db.execute_query(tasks_query, (user_id,), fetch_one=True)
        task_count = tasks_result[0]['count'] if tasks_result else 0
        print(f"   Tasks: {task_count}")
        
    except Exception as e:
        print(f"❌ Error checking user data: {e}")

def main():
    print("\n🔍 AUTHENTICATION & DATA DIAGNOSTIC TOOL")
    print("="*60)
    
    # Check if RDS credentials are configured
    if not all([
        os.getenv('RDS_HOST'),
        os.getenv('RDS_DATABASE'),
        os.getenv('RDS_USER'),
        os.getenv('RDS_PASSWORD')
    ]):
        print("\n❌ RDS credentials not configured in .env file")
        print("\nRequired environment variables:")
        print("  - RDS_HOST")
        print("  - RDS_DATABASE")
        print("  - RDS_USER")
        print("  - RDS_PASSWORD")
        print("\nPlease check your backend/.env file")
        return
    
    print(f"\n📋 RDS Configuration:")
    print(f"   Host: {os.getenv('RDS_HOST')}")
    print(f"   Database: {os.getenv('RDS_DATABASE')}")
    print(f"   User: {os.getenv('RDS_USER')}")
    print(f"   Port: {os.getenv('RDS_PORT', '5432')}")
    
    # Force reinitialize database with current environment variables
    if not force_reinitialize_db():
        print("\n❌ Database connection pool failed to initialize")
        print("\nPossible issues:")
        print("  1. RDS instance is not accessible")
        print("  2. Security group rules blocking connection")
        print("  3. Incorrect credentials")
        print("  4. Database is not running")
        print("\nTroubleshooting:")
        print("  - Check AWS RDS console to verify instance is running")
        print("  - Verify security group allows inbound traffic on port 5432")
        print("  - Test connection with: psql -h <host> -U <user> -d <database>")
        return
    
    # Test database connection
    try:
        print("\n🔍 Testing database connection...")
        health = rds_db.health_check()
        if health['status'] == 'healthy':
            print("✅ Database connection successful")
            print(f"   Host: {health['database']['host']}")
            print(f"   Database: {health['database']['name']}")
            print(f"   Connection Pool: {health['connection_pool']['min']}-{health['connection_pool']['max']} connections")
        else:
            print(f"❌ Database health check failed: {health.get('error', 'Unknown error')}")
            print("\nPlease check:")
            print("  - Database credentials in .env file")
            print("  - Network connectivity to RDS instance")
            print("  - RDS instance status in AWS console")
            return
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nError details:")
        print(f"   {type(e).__name__}: {str(e)}")
        return
    
    # Run diagnostics
    check_users()
    check_meetings()
    check_tasks()
    
    # Check specific user if provided
    if len(sys.argv) > 1:
        email = sys.argv[1]
        check_user_data_relationship(email)
    else:
        print_header("USAGE")
        print("To check a specific user's data:")
        print(f"  python {sys.argv[0]} user@example.com")
    
    print("\n" + "="*60)
    print("✅ Diagnostic complete")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
