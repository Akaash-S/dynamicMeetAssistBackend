"""
Update RDS Database Schema
Adds new columns and improvements for better services
"""

import os
import sys
from dotenv import load_dotenv
from config.aws_rds_database import rds_db
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def print_header(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    query = """
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = %s AND column_name = %s
    """
    result = rds_db.execute_query(query, (table_name, column_name), fetch_one=True)
    return result is not None

def add_column_if_not_exists(table_name, column_name, column_definition):
    """Add a column to a table if it doesn't exist"""
    if check_column_exists(table_name, column_name):
        print(f"  ⏭️  Column {table_name}.{column_name} already exists")
        return False
    
    try:
        query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        rds_db.execute_query(query)
        print(f"  ✅ Added column {table_name}.{column_name}")
        return True
    except Exception as e:
        print(f"  ❌ Error adding column {table_name}.{column_name}: {e}")
        return False

def create_index_if_not_exists(index_name, table_name, columns):
    """Create an index if it doesn't exist"""
    check_query = """
    SELECT indexname 
    FROM pg_indexes 
    WHERE indexname = %s
    """
    result = rds_db.execute_query(check_query, (index_name,), fetch_one=True)
    
    if result:
        print(f"  ⏭️  Index {index_name} already exists")
        return False
    
    try:
        query = f"CREATE INDEX {index_name} ON {table_name} ({columns})"
        rds_db.execute_query(query)
        print(f"  ✅ Created index {index_name}")
        return True
    except Exception as e:
        print(f"  ❌ Error creating index {index_name}: {e}")
        return False

def update_users_table():
    """Add improvements to users table"""
    print_header("Updating Users Table")
    
    updates = [
        # Profile enhancements
        ("profile_picture_url", "TEXT"),
        ("phone_number", "VARCHAR(20)"),
        ("timezone", "VARCHAR(50) DEFAULT 'UTC'"),
        ("language", "VARCHAR(10) DEFAULT 'en'"),
        ("company", "VARCHAR(255)"),
        ("job_title", "VARCHAR(255)"),
        
        # Subscription/billing
        ("subscription_tier", "VARCHAR(50) DEFAULT 'free'"),
        ("subscription_status", "VARCHAR(50) DEFAULT 'active'"),
        ("subscription_started_at", "TIMESTAMP"),
        ("subscription_expires_at", "TIMESTAMP"),
        ("trial_ends_at", "TIMESTAMP"),
        
        # Usage tracking
        ("meetings_count", "INTEGER DEFAULT 0"),
        ("storage_used_bytes", "BIGINT DEFAULT 0"),
        ("last_activity_at", "TIMESTAMP"),
        
        # Security enhancements
        ("failed_login_attempts", "INTEGER DEFAULT 0"),
        ("account_locked_until", "TIMESTAMP"),
        ("password_changed_at", "TIMESTAMP"),
        ("email_verified", "BOOLEAN DEFAULT FALSE"),
        ("email_verification_token", "VARCHAR(255)"),
        ("email_verification_sent_at", "TIMESTAMP"),
        
        # 2FA enhancements
        ("two_factor_phone", "VARCHAR(20)"),
        ("two_factor_backup_codes_used", "INTEGER DEFAULT 0"),
        
        # Preferences
        ("theme", "VARCHAR(20) DEFAULT 'light'"),
        ("auto_transcribe", "BOOLEAN DEFAULT TRUE"),
        ("auto_summarize", "BOOLEAN DEFAULT TRUE"),
        ("auto_extract_tasks", "BOOLEAN DEFAULT TRUE"),
    ]
    
    added_count = 0
    for column_name, column_def in updates:
        if add_column_if_not_exists("users", column_name, column_def):
            added_count += 1
    
    print(f"\n  📊 Added {added_count} new columns to users table")

def update_meetings_table():
    """Add improvements to meetings table"""
    print_header("Updating Meetings Table")
    
    updates = [
        # Meeting metadata
        ("meeting_date", "TIMESTAMP"),
        ("meeting_type", "VARCHAR(50) DEFAULT 'general'"),  # general, standup, review, etc.
        ("participants", "TEXT[]"),
        ("tags", "TEXT[]"),
        
        # Processing enhancements
        ("processing_started_at", "TIMESTAMP"),
        ("processing_completed_at", "TIMESTAMP"),
        ("processing_error", "TEXT"),
        ("retry_count", "INTEGER DEFAULT 0"),
        
        # AI analysis
        ("sentiment_score", "DECIMAL(3,2)"),  # -1.0 to 1.0
        ("key_topics", "TEXT[]"),
        ("action_items_count", "INTEGER DEFAULT 0"),
        ("decisions_made", "TEXT[]"),
        
        # File metadata
        ("original_filename", "VARCHAR(255)"),
        ("file_format", "VARCHAR(20)"),
        ("audio_quality", "VARCHAR(20)"),
        
        # Sharing and collaboration
        ("is_public", "BOOLEAN DEFAULT FALSE"),
        ("share_token", "VARCHAR(255)"),
        ("shared_with_emails", "TEXT[]"),
        
        # Archival
        ("archived", "BOOLEAN DEFAULT FALSE"),
        ("archived_at", "TIMESTAMP"),
    ]
    
    added_count = 0
    for column_name, column_def in updates:
        if add_column_if_not_exists("meetings", column_name, column_def):
            added_count += 1
    
    print(f"\n  📊 Added {added_count} new columns to meetings table")

def update_tasks_table():
    """Add improvements to tasks table"""
    print_header("Updating Tasks Table")
    
    updates = [
        # Task enhancements
        ("estimated_hours", "DECIMAL(5,2)"),
        ("actual_hours", "DECIMAL(5,2)"),
        ("tags", "TEXT[]"),
        ("dependencies", "UUID[]"),  # Array of task IDs this task depends on
        
        # Collaboration
        ("watchers", "TEXT[]"),  # Array of emails watching this task
        ("comments_count", "INTEGER DEFAULT 0"),
        
        # Completion tracking
        ("completed_at", "TIMESTAMP"),
        ("completed_by", "VARCHAR(255)"),
        
        # Reminders
        ("reminder_sent", "BOOLEAN DEFAULT FALSE"),
        ("reminder_sent_at", "TIMESTAMP"),
        
        # Integration
        ("external_task_id", "VARCHAR(255)"),  # For integration with other tools
        ("external_task_url", "TEXT"),
    ]
    
    added_count = 0
    for column_name, column_def in updates:
        if add_column_if_not_exists("tasks", column_name, column_def):
            added_count += 1
    
    print(f"\n  📊 Added {added_count} new columns to tasks table")

def update_notifications_table():
    """Add improvements to notifications table"""
    print_header("Updating Notifications Table")
    
    updates = [
        # Notification enhancements
        ("priority", "VARCHAR(20) DEFAULT 'normal'"),  # low, normal, high, urgent
        ("action_url", "TEXT"),
        ("action_label", "VARCHAR(100)"),
        ("icon", "VARCHAR(50)"),
        ("category", "VARCHAR(50)"),  # task, meeting, system, etc.
        
        # Delivery tracking
        ("push_sent", "BOOLEAN DEFAULT FALSE"),
        ("push_sent_at", "TIMESTAMP"),
        ("sms_sent", "BOOLEAN DEFAULT FALSE"),
        ("sms_sent_at", "TIMESTAMP"),
        
        # Expiration
        ("expires_at", "TIMESTAMP"),
    ]
    
    added_count = 0
    for column_name, column_def in updates:
        if add_column_if_not_exists("notifications", column_name, column_def):
            added_count += 1
    
    print(f"\n  📊 Added {added_count} new columns to notifications table")

def create_new_tables():
    """Create new tables for enhanced functionality"""
    print_header("Creating New Tables")
    
    # Meeting participants table
    create_participants_table = """
    CREATE TABLE IF NOT EXISTS meeting_participants (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255),
        role VARCHAR(50),  -- host, participant, observer
        speaking_time_seconds INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Task comments table
    create_task_comments_table = """
    CREATE TABLE IF NOT EXISTS task_comments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        comment TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # User activity log
    create_activity_log_table = """
    CREATE TABLE IF NOT EXISTS user_activity_log (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        action VARCHAR(100) NOT NULL,
        resource_type VARCHAR(50),
        resource_id UUID,
        details JSONB,
        ip_address VARCHAR(45),
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # API usage tracking
    create_api_usage_table = """
    CREATE TABLE IF NOT EXISTS api_usage (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        endpoint VARCHAR(255) NOT NULL,
        method VARCHAR(10) NOT NULL,
        status_code INTEGER,
        response_time_ms INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Meeting templates
    create_meeting_templates_table = """
    CREATE TABLE IF NOT EXISTS meeting_templates (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        default_participants TEXT[],
        default_tags TEXT[],
        is_public BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    tables = [
        ("meeting_participants", create_participants_table),
        ("task_comments", create_task_comments_table),
        ("user_activity_log", create_activity_log_table),
        ("api_usage", create_api_usage_table),
        ("meeting_templates", create_meeting_templates_table),
    ]
    
    created_count = 0
    for table_name, create_query in tables:
        try:
            rds_db.execute_query(create_query)
            print(f"  ✅ Created table: {table_name}")
            created_count += 1
        except Exception as e:
            print(f"  ⏭️  Table {table_name} may already exist or error: {e}")
    
    print(f"\n  📊 Created {created_count} new tables")

def create_indexes():
    """Create indexes for better performance"""
    print_header("Creating Performance Indexes")
    
    indexes = [
        # Users indexes
        ("idx_users_email", "users", "email"),
        ("idx_users_firebase_uid", "users", "firebase_uid"),
        ("idx_users_google_oauth_id", "users", "google_oauth_id"),
        ("idx_users_subscription_tier", "users", "subscription_tier"),
        
        # Meetings indexes
        ("idx_meetings_user_id", "meetings", "user_id"),
        ("idx_meetings_status", "meetings", "status"),
        ("idx_meetings_created_at", "meetings", "created_at DESC"),
        ("idx_meetings_meeting_date", "meetings", "meeting_date"),
        
        # Tasks indexes
        ("idx_tasks_user_id", "tasks", "user_id"),
        ("idx_tasks_meeting_id", "tasks", "meeting_id"),
        ("idx_tasks_status", "tasks", "status"),
        ("idx_tasks_deadline", "tasks", "deadline"),
        ("idx_tasks_priority", "tasks", "priority"),
        
        # Notifications indexes
        ("idx_notifications_user_id", "notifications", "user_id"),
        ("idx_notifications_created_at", "notifications", "created_at DESC"),
        
        # Timeline indexes
        ("idx_timeline_meeting_id", "timeline", "meeting_id"),
        
        # Activity log indexes
        ("idx_activity_user_id", "user_activity_log", "user_id"),
        ("idx_activity_created_at", "user_activity_log", "created_at DESC"),
    ]
    
    created_count = 0
    for index_name, table_name, columns in indexes:
        if create_index_if_not_exists(index_name, table_name, columns):
            created_count += 1
    
    print(f"\n  📊 Created {created_count} new indexes")

def main():
    print("\n🔧 RDS DATABASE SCHEMA UPDATE")
    print("="*70)
    print("This script will update your database schema with improvements")
    print("="*70)
    
    # Test database connection
    try:
        health = rds_db.health_check()
        if health['status'] == 'healthy':
            print("\n✅ Database connection successful")
            print(f"   Host: {health['database']['host']}")
            print(f"   Database: {health['database']['name']}")
        else:
            print(f"\n❌ Database connection failed: {health.get('error', 'Unknown error')}")
            print("\nPlease check your .env file and ensure RDS credentials are correct:")
            print("  - RDS_HOST")
            print("  - RDS_DATABASE")
            print("  - RDS_USER")
            print("  - RDS_PASSWORD")
            return
    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")
        return
    
    # Confirm before proceeding
    print("\n⚠️  This will modify your database schema.")
    print("   It's recommended to backup your database first.")
    response = input("\nProceed with schema update? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("\n❌ Schema update cancelled")
        return
    
    try:
        # Update existing tables
        update_users_table()
        update_meetings_table()
        update_tasks_table()
        update_notifications_table()
        
        # Create new tables
        create_new_tables()
        
        # Create indexes
        create_indexes()
        
        print_header("SCHEMA UPDATE COMPLETE")
        print("\n✅ Database schema has been successfully updated!")
        print("\nNew features available:")
        print("  • Enhanced user profiles with subscription tracking")
        print("  • Meeting metadata and AI analysis fields")
        print("  • Task collaboration and time tracking")
        print("  • Meeting participants tracking")
        print("  • Task comments system")
        print("  • User activity logging")
        print("  • API usage tracking")
        print("  • Meeting templates")
        print("  • Performance indexes for faster queries")
        
        print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error updating schema: {e}")
        logger.error(f"Schema update error: {e}")

if __name__ == "__main__":
    main()
