"""
Add is_read column to notifications table
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from config.aws_rds_database import rds_db

def add_is_read_column():
    print("=" * 60)
    print("ADDING is_read COLUMN TO NOTIFICATIONS TABLE")
    print("=" * 60)
    print()
    
    try:
        # Add is_read column if it doesn't exist
        print("Adding is_read column...")
        add_column_query = """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'notifications' AND column_name = 'is_read'
            ) THEN
                ALTER TABLE notifications ADD COLUMN is_read BOOLEAN DEFAULT FALSE;
                RAISE NOTICE 'Column is_read added successfully';
            ELSE
                RAISE NOTICE 'Column is_read already exists';
            END IF;
        END $$;
        """
        rds_db.execute_query(add_column_query)
        print("✅ is_read column added!")
        
        # Add read_at column if it doesn't exist
        print("Adding read_at column...")
        add_read_at_query = """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'notifications' AND column_name = 'read_at'
            ) THEN
                ALTER TABLE notifications ADD COLUMN read_at TIMESTAMP;
                RAISE NOTICE 'Column read_at added successfully';
            ELSE
                RAISE NOTICE 'Column read_at already exists';
            END IF;
        END $$;
        """
        rds_db.execute_query(add_read_at_query)
        print("✅ read_at column added!")
        
        # Add data column if it doesn't exist
        print("Adding data column...")
        add_data_query = """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'notifications' AND column_name = 'data'
            ) THEN
                ALTER TABLE notifications ADD COLUMN data JSONB;
                RAISE NOTICE 'Column data added successfully';
            ELSE
                RAISE NOTICE 'Column data already exists';
            END IF;
        END $$;
        """
        rds_db.execute_query(add_data_query)
        print("✅ data column added!")
        
        # Create indexes
        print()
        print("Creating indexes...")
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);",
            "CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);"
        ]
        
        for idx_query in index_queries:
            rds_db.execute_query(idx_query)
        
        print("✅ Indexes created!")
        
        print()
        print("=" * 60)
        print("✅ NOTIFICATIONS TABLE UPDATED SUCCESSFULLY!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    add_is_read_column()
