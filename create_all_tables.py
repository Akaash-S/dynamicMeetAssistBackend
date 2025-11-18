"""
Create all missing tables
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from config.aws_rds_database import rds_db

def create_all_tables():
    print("=" * 60)
    print("CREATING ALL MISSING TABLES")
    print("=" * 60)
    print()
    
    try:
        # Test connection
        test_result = rds_db.execute_query("SELECT 1 as test", fetch_one=True)
        if not test_result:
            print("❌ Database connection failed!")
            return False
        
        print("✅ Database connected!")
        print()
        
        # Create notifications table
        print("Creating notifications table...")
        notifications_query = """
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            data JSONB,
            is_read BOOLEAN DEFAULT FALSE,
            read_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
        CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
        CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);
        """
        rds_db.execute_query(notifications_query)
        print("✅ Notifications table created!")
        
        # Create processing_status table
        print("Creating processing_status table...")
        processing_query = """
        CREATE TABLE IF NOT EXISTS processing_status (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            step VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_processing_status_meeting_id ON processing_status(meeting_id);
        """
        rds_db.execute_query(processing_query)
        print("✅ Processing status table created!")
        
        print()
        print("=" * 60)
        print("✅ ALL TABLES CREATED SUCCESSFULLY!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    create_all_tables()
