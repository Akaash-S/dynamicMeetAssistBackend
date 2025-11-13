"""
Complete RDS Database Reset
Drops all tables and creates fresh schema with UUID support
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from config.aws_rds_database import rds_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_connection():
    """Check RDS connection"""
    print("\n" + "="*70)
    print("Checking RDS Connection")
    print("="*70)
    
    health = rds_db.health_check()
    
    if health['status'] != 'healthy':
        print("\n❌ RDS Connection Failed!")
        print(f"   Error: {health.get('error', 'Unknown error')}")
        print("\n📋 Troubleshooting:")
        print("   1. Check RDS instance is running in AWS Console")
        print("   2. Verify security group allows your IP on port 5432")
        print("   3. Confirm RDS credentials in .env are correct")
        print("   4. Check RDS endpoint is correct")
        return False
    
    print(f"\n✅ RDS Connection Successful!")
    print(f"   Host: {health['database']['host']}")
    print(f"   Database: {health['database']['name']}")
    print(f"   Port: {health['database']['port']}")
    return True


def drop_all_tables():
    """Drop all existing tables in correct order"""
    print("\n" + "="*70)
    print("Dropping All Existing Tables")
    print("="*70)
    
    # Drop in reverse order of dependencies
    drop_queries = [
        "DROP TABLE IF EXISTS admin_logs CASCADE;",
        "DROP TABLE IF EXISTS admin_notifications CASCADE;",
        "DROP TABLE IF EXISTS admin_payments CASCADE;",
        "DROP TABLE IF EXISTS admin_issues CASCADE;",
        "DROP TABLE IF EXISTS notifications CASCADE;",
        "DROP TABLE IF EXISTS processing_status CASCADE;",
        "DROP TABLE IF EXISTS tasks CASCADE;",
        "DROP TABLE IF EXISTS timeline CASCADE;",
        "DROP TABLE IF EXISTS meetings CASCADE;",
        "DROP TABLE IF EXISTS users CASCADE;",
    ]
    
    try:
        for query in drop_queries:
            table_name = query.split("IF EXISTS ")[1].split(" ")[0].replace(";", "")
            try:
                rds_db.execute_query(query)
                print(f"  ✅ Dropped: {table_name}")
            except Exception as e:
                print(f"  ⚠️  {table_name}: {str(e)[:50]}")
        
        print("\n✅ All tables dropped successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        print(f"\n❌ Error: {e}")
        return False


def create_fresh_tables():
    """Create all tables with fresh UUID schema"""
    print("\n" + "="*70)
    print("Creating Fresh Database Schema")
    print("="*70)
    
    try:
        # 1. Extensions
        print("\n📝 Creating extensions...")
        rds_db.execute_query("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        print("  ✅ pgcrypto extension")
        
        # 2. Users table with 2FA support
        print("\n📝 Creating users table...")
        create_users = """
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            firebase_uid VARCHAR(255) UNIQUE,
            google_oauth_id VARCHAR(255) UNIQUE,
            email VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            auth_provider VARCHAR(50) DEFAULT 'firebase',
            google_access_token TEXT,
            google_refresh_token TEXT,
            google_token_expires_at TIMESTAMP,
            email_notifications BOOLEAN DEFAULT TRUE,
            in_app_notifications BOOLEAN DEFAULT TRUE,
            google_calendar_enabled BOOLEAN DEFAULT FALSE,
            role VARCHAR(50) DEFAULT 'user',
            password_hash VARCHAR(255),
            last_login_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            two_factor_enabled BOOLEAN DEFAULT FALSE,
            two_factor_method VARCHAR(50),
            two_factor_secret TEXT,
            backup_codes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT users_auth_check CHECK (
                (firebase_uid IS NOT NULL) OR 
                (google_oauth_id IS NOT NULL) OR 
                (password_hash IS NOT NULL)
            )
        );
        """
        rds_db.execute_query(create_users)
        print("  ✅ users table (with 2FA columns)")
        
        # 3. Meetings table
        print("\n📝 Creating meetings table...")
        create_meetings = """
        CREATE TABLE meetings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            audio_url TEXT,
            transcript TEXT,
            summary TEXT,
            status VARCHAR(50) DEFAULT 'processing',
            file_size BIGINT,
            duration INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        rds_db.execute_query(create_meetings)
        print("  ✅ meetings table")
        
        # 4. Timeline table
        print("\n📝 Creating timeline table...")
        create_timeline = """
        CREATE TABLE timeline (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
            timestamp_minutes DECIMAL(10,2) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            content TEXT,
            participants TEXT[],
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        rds_db.execute_query(create_timeline)
        print("  ✅ timeline table")
        
        # 5. Tasks table
        print("\n📝 Creating tasks table...")
        create_tasks = """
        CREATE TABLE tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            assigned_to VARCHAR(255),
            deadline TIMESTAMP,
            priority VARCHAR(20) DEFAULT 'medium',
            status VARCHAR(20) DEFAULT 'pending',
            calendar_event_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        rds_db.execute_query(create_tasks)
        print("  ✅ tasks table")
        
        # 6. Processing status table
        print("\n📝 Creating processing_status table...")
        create_processing = """
        CREATE TABLE processing_status (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
            step VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL,
            progress INTEGER DEFAULT 0,
            error_message TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        );
        """
        rds_db.execute_query(create_processing)
        print("  ✅ processing_status table")
        
        # 7. Notifications table
        print("\n📝 Creating notifications table...")
        create_notifications = """
        CREATE TABLE notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            email_sent BOOLEAN DEFAULT FALSE,
            email_sent_at TIMESTAMP,
            read_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        rds_db.execute_query(create_notifications)
        print("  ✅ notifications table")
        
        # 8. Admin tables
        print("\n📝 Creating admin tables...")
        
        create_admin_issues = """
        CREATE TABLE admin_issues (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(50) DEFAULT 'open',
            priority VARCHAR(20) DEFAULT 'medium',
            category VARCHAR(100),
            assigned_to VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            resolved_by VARCHAR(255)
        );
        """
        rds_db.execute_query(create_admin_issues)
        print("  ✅ admin_issues table")
        
        create_admin_payments = """
        CREATE TABLE admin_payments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            amount DECIMAL(10,2) NOT NULL,
            currency VARCHAR(3) DEFAULT 'USD',
            status VARCHAR(50) DEFAULT 'pending',
            payment_method VARCHAR(50),
            transaction_id VARCHAR(255),
            stripe_payment_intent_id VARCHAR(255),
            description VARCHAR(255),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        rds_db.execute_query(create_admin_payments)
        print("  ✅ admin_payments table")
        
        create_admin_notifications = """
        CREATE TABLE admin_notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            message TEXT NOT NULL,
            type VARCHAR(50) DEFAULT 'system',
            priority VARCHAR(20) DEFAULT 'normal',
            target_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            is_read BOOLEAN DEFAULT FALSE,
            created_by VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        rds_db.execute_query(create_admin_notifications)
        print("  ✅ admin_notifications table")
        
        create_admin_logs = """
        CREATE TABLE admin_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            admin_email VARCHAR(255) NOT NULL,
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50),
            resource_id VARCHAR(255),
            details TEXT,
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        rds_db.execute_query(create_admin_logs)
        print("  ✅ admin_logs table")
        
        print("\n✅ All tables created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        print(f"\n❌ Error: {e}")
        return False


def verify_schema():
    """Verify all tables were created correctly"""
    print("\n" + "="*70)
    print("Verifying Database Schema")
    print("="*70)
    
    try:
        # Check all tables exist
        check_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
        """
        
        tables = rds_db.execute_query(check_query, fetch_all=True)
        
        expected_tables = [
            'admin_issues', 'admin_logs', 'admin_notifications', 'admin_payments',
            'meetings', 'notifications', 'processing_status', 'tasks', 
            'timeline', 'users'
        ]
        
        found_tables = [t['table_name'] for t in tables]
        
        print(f"\n📊 Found {len(found_tables)} tables:")
        for table in found_tables:
            status = "✅" if table in expected_tables else "⚠️"
            print(f"  {status} {table}")
        
        missing = set(expected_tables) - set(found_tables)
        if missing:
            print(f"\n⚠️  Missing tables: {', '.join(missing)}")
            return False
        
        print("\n✅ All expected tables exist!")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying schema: {e}")
        print(f"\n❌ Error: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("🔄 RDS Database Complete Reset")
    print("="*70)
    print("\n⚠️  WARNING: This will DELETE ALL DATA in your RDS database!")
    print("   • All existing tables will be dropped")
    print("   • Fresh tables will be created with UUID schema")
    print("   • 2FA columns will be added to users table")
    print("   • All admin tables will be created")
    
    # Check connection first
    if not check_connection():
        return False
    
    # Ask for confirmation
    print("\n" + "="*70)
    response = input("\n⚠️  Type 'DELETE ALL DATA' to continue: ")
    
    if response != 'DELETE ALL DATA':
        print("\n❌ Operation cancelled.")
        return False
    
    # Drop all tables
    if not drop_all_tables():
        print("\n❌ Failed to drop tables")
        return False
    
    # Create fresh tables
    if not create_fresh_tables():
        print("\n❌ Failed to create tables")
        return False
    
    # Verify schema
    if not verify_schema():
        print("\n⚠️  Schema verification failed")
        return False
    
    # Success!
    print("\n" + "="*70)
    print("✅ RDS Database Reset Complete!")
    print("="*70)
    print("\n🎉 Your RDS database is now ready with:")
    print("   • All tables using UUID primary keys")
    print("   • Proper foreign key relationships")
    print("   • 2FA support in users table")
    print("   • All admin tables")
    print("\n📋 Next steps:")
    print("   1. Start your application: python app.py")
    print("   2. Test health endpoint: curl http://localhost:8000/api/health")
    print("   3. Create your first user through the app")
    print("\n" + "="*70)
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
