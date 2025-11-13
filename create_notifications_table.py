"""
Script to create the notifications table in the database
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.aws_rds_database import rds_db

def create_notifications_table():
    """Create notifications table"""
    try:
        print("📊 Creating notifications table...")
        print(f"🔍 Using database: {os.getenv('RDS_DB_NAME', 'meetingmind_db')}")
        print(f"🔍 Host: {os.getenv('RDS_HOST', 'localhost')}")
        
        # Test connection by running a simple query
        try:
            test_result = rds_db.execute_query("SELECT 1 as test", fetch_one=True)
            if test_result:
                print("✅ Database connection successful!")
        except Exception as conn_error:
            print(f"❌ Database connection failed: {conn_error}")
            return False
        
        # Check if table exists
        print("🔍 Checking if notifications table exists...")
        check_table_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'notifications'
        );
        """
        table_exists = rds_db.execute_query(check_table_query, fetch_one=True)
        
        if table_exists and table_exists.get('exists'):
            print("⚠️  Notifications table already exists. Dropping it...")
            rds_db.execute_query("DROP TABLE IF EXISTS notifications CASCADE;")
            print("✅ Old table dropped!")
        
        print("📝 Creating notifications table with all columns...")
        create_table_query = """
        CREATE TABLE notifications (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            data JSONB,
            is_read BOOLEAN DEFAULT FALSE,
            read_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        rds_db.execute_query(create_table_query)
        print("✅ Table created with all columns!")
        
        print("📝 Creating indexes...")
        index_queries = [
            "CREATE INDEX idx_notifications_user_id ON notifications(user_id);",
            "CREATE INDEX idx_notifications_is_read ON notifications(is_read);",
            "CREATE INDEX idx_notifications_created_at ON notifications(created_at);"
        ]
        
        for idx_query in index_queries:
            try:
                rds_db.execute_query(idx_query)
                print(f"  ✅ Index created: {idx_query.split()[2]}")
            except Exception as idx_error:
                print(f"  ⚠️  Index creation warning: {idx_error}")
        
        print("✅ All indexes created!")
        
        # Verify table structure
        print("🔍 Verifying table structure...")
        verify_structure_query = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'notifications'
        ORDER BY ordinal_position;
        """
        columns = rds_db.execute_query(verify_structure_query, fetch_all=True)
        
        if columns:
            print("✅ Table structure verified:")
            for col in columns:
                print(f"  - {col['column_name']}: {col['data_type']}")
        
        # Verify table is empty
        count_query = "SELECT COUNT(*) as count FROM notifications"
        result = rds_db.execute_query(count_query, fetch_one=True)
        print(f"✅ Table ready! Current notification count: {result['count'] if result else 0}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating notifications table: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("NOTIFICATION TABLE SETUP")
    print("=" * 60)
    success = create_notifications_table()
    print("=" * 60)
    if success:
        print("✅ Setup completed successfully!")
    else:
        print("❌ Setup failed! Check the errors above.")
    print("=" * 60)
