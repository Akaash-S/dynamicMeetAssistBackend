"""
Fix Chatbot Tables - Change user_id from UUID to VARCHAR
==========================================================
This script fixes the chatbot tables to use VARCHAR for user_id
instead of UUID, since Firebase UIDs are not in UUID format.
"""

import sys
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
load_dotenv()

from config.aws_rds_database import rds_db

def fix_chatbot_tables():
    """Fix chatbot tables to use VARCHAR for user_id"""
    print("="*60)
    print("FIXING CHATBOT TABLES")
    print("="*60)
    print()
    
    try:
        # Check current schema
        print("1. Checking current schema...")
        check_query = """
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns 
        WHERE table_name = 'chatbot_sessions' 
        AND column_name = 'user_id'
        """
        result = rds_db.execute_query(check_query, fetch_all=True)
        
        if result:
            current_type = result[0]['data_type']
            print(f"   Current user_id type: {current_type}")
            
            if current_type == 'character varying':
                print("   ✅ user_id is already VARCHAR")
                print()
                return True
        else:
            print("   ⚠️  chatbot_sessions table not found")
            print()
            return False
        
        # Drop foreign key constraint
        print("2. Dropping foreign key constraint...")
        drop_fk_query = """
        ALTER TABLE chatbot_sessions 
        DROP CONSTRAINT IF EXISTS chatbot_sessions_user_id_fkey
        """
        rds_db.execute_query(drop_fk_query)
        print("   ✅ Foreign key constraint dropped")
        print()
        
        # Change column type
        print("3. Changing user_id column type to VARCHAR...")
        alter_query = """
        ALTER TABLE chatbot_sessions 
        ALTER COLUMN user_id TYPE VARCHAR(255)
        """
        rds_db.execute_query(alter_query)
        print("   ✅ Column type changed to VARCHAR(255)")
        print()
        
        # Add indexes
        print("4. Adding indexes for performance...")
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_chatbot_sessions_user_id ON chatbot_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_chatbot_messages_session_id ON chatbot_messages(session_id)"
        ]
        
        for query in index_queries:
            rds_db.execute_query(query)
        print("   ✅ Indexes created")
        print()
        
        # Verify changes
        print("5. Verifying changes...")
        result = rds_db.execute_query(check_query, fetch_all=True)
        
        if result:
            new_type = result[0]['data_type']
            max_length = result[0]['character_maximum_length']
            print(f"   New user_id type: {new_type}({max_length})")
            
            if new_type == 'character varying':
                print("   ✅ Migration successful!")
                print()
                print("="*60)
                print("✅ CHATBOT TABLES FIXED!")
                print("="*60)
                return True
            else:
                print("   ❌ Migration failed - type not changed")
                return False
        else:
            print("   ❌ Could not verify changes")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check database connection")
        print("2. Verify RDS credentials in .env")
        print("3. Ensure you have ALTER TABLE permissions")
        return False

if __name__ == "__main__":
    print("\n⚠️  WARNING: This will modify your database schema!")
    print("   Make sure you have a backup before proceeding.")
    print()
    
    response = input("Do you want to continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        success = fix_chatbot_tables()
        sys.exit(0 if success else 1)
    else:
        print("\n❌ Migration cancelled")
        sys.exit(1)
