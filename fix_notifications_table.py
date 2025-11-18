"""
Fix notifications table by adding missing columns
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from config.aws_rds_database import rds_db

def fix_notifications_table():
    print("=" * 60)
    print("FIXING NOTIFICATIONS TABLE")
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
        
        # Check if table exists
        check_table = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'notifications'
        );
        """
        table_exists = rds_db.execute_query(check_table, fetch_one=True)
        
        if table_exists and table_exists.get('exists'):
            print("📋 Notifications table exists. Checking columns...")
            
            # Get existing columns
            get_columns = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'notifications';
            """
            columns = rds_db.execute_query(get_columns, fetch_all=True)
            existing_columns = [col.get('column_name') for col in columns] if columns else []
            print(f"   Existing columns: {', '.join(existing_columns)}")
            print()
            
            # Add missing columns
            columns_to_add = []
            
            if 'is_read' not in existing_columns:
                columns_to_add.append(("is_read", "ALTER TABLE notifications ADD COLUMN is_read BOOLEAN DEFAULT FALSE;"))
            
            if 'read_at' not in existing_columns:
                columns_to_add.append(("read_at", "ALTER TABLE notifications ADD COLUMN read_at TIMESTAMP;"))
            
            if 'data' not in existing_columns:
                columns_to_add.append(("data", "ALTER TABLE notifications ADD COLUMN data JSONB;"))
            
            if columns_to_add:
                for col_name, query in columns_to_add:
                    print(f"Adding column: {col_name}...")
                    rds_db.execute_query(query)
                    print(f"✅ Column {col_name} added!")
            else:
                print("✅ All required columns already exist!")
            
            # Create indexes
            print()
            print("Creating indexes...")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);",
                "CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);"
            ]
            
            for idx_query in indexes:
                rds_db.execute_query(idx_query)
            
            print("✅ Indexes created!")
            
        else:
            print("📋 Notifications table doesn't exist. Creating it...")
            create_query = """
            CREATE TABLE notifications (
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
            
            CREATE INDEX idx_notifications_user_id ON notifications(user_id);
            CREATE INDEX idx_notifications_is_read ON notifications(is_read);
            CREATE INDEX idx_notifications_created_at ON notifications(created_at);
            """
            rds_db.execute_query(create_query)
            print("✅ Notifications table created!")
        
        print()
        print("=" * 60)
        print("✅ NOTIFICATIONS TABLE FIXED SUCCESSFULLY!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    fix_notifications_table()
