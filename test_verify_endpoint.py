"""
Test the verify endpoint to diagnose the 500 error
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from config.aws_rds_database import rds_db

def test_database_connection():
    """Test basic database connectivity"""
    print("=" * 60)
    print("TESTING DATABASE CONNECTION")
    print("=" * 60)
    print()
    
    try:
        # Test basic query
        result = rds_db.execute_query("SELECT 1 as test", fetch_one=True)
        if result:
            print("✅ Database connection successful!")
            print(f"   Result: {result}")
        else:
            print("❌ Database connection failed - no result")
            return False
        
        # Check if users table exists
        check_table = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'users'
        );
        """
        table_exists = rds_db.execute_query(check_table, fetch_one=True)
        if table_exists and table_exists.get('exists'):
            print("✅ Users table exists")
        else:
            print("❌ Users table does not exist!")
            return False
        
        # Check users table structure
        get_columns = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'users'
        ORDER BY ordinal_position;
        """
        columns = rds_db.execute_query(get_columns, fetch_all=True)
        print(f"\n📋 Users table columns ({len(columns)} total):")
        for col in columns:
            print(f"   - {col['column_name']}: {col['data_type']}")
        
        # Test a simple user lookup
        print("\n🔍 Testing user lookup...")
        test_query = "SELECT * FROM users LIMIT 1"
        test_user = rds_db.execute_query(test_query, fetch_one=True)
        if test_user:
            print(f"✅ Found test user: {test_user.get('email')}")
        else:
            print("ℹ️  No users in database yet (this is OK for new installations)")
        
        print("\n" + "=" * 60)
        print("✅ ALL DATABASE TESTS PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    test_database_connection()
