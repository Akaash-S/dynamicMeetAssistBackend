"""
Add 2FA Settings Columns to Users Table
========================================
Adds user-configurable 2FA settings columns to the users table.
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

from config.aws_rds_database import rds_db
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def add_2fa_settings_columns():
    """Add 2FA settings columns to users table"""
    
    print("\n" + "="*70)
    print("Adding 2FA Settings Columns to Users Table")
    print("="*70 + "\n")
    
    try:
        # Check if columns already exist
        check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name IN ('two_factor_inactivity_timeout', 'two_factor_always_required', 'two_factor_require_on_login')
        """
        
        existing_columns = rds_db.execute_query(check_query, fetch_all=True)
        existing_column_names = [col['column_name'] for col in (existing_columns or [])]
        
        print(f"📋 Existing 2FA settings columns: {existing_column_names}")
        
        # Add two_factor_inactivity_timeout if not exists
        if 'two_factor_inactivity_timeout' not in existing_column_names:
            print("\n➕ Adding two_factor_inactivity_timeout column...")
            rds_db.execute_query("""
                ALTER TABLE users 
                ADD COLUMN two_factor_inactivity_timeout INTEGER DEFAULT 600
            """)
            print("   ✅ two_factor_inactivity_timeout column added (default: 600 seconds = 10 minutes)")
        else:
            print("\n✓ two_factor_inactivity_timeout column already exists")
        
        # Add two_factor_always_required if not exists
        if 'two_factor_always_required' not in existing_column_names:
            print("\n➕ Adding two_factor_always_required column...")
            rds_db.execute_query("""
                ALTER TABLE users 
                ADD COLUMN two_factor_always_required BOOLEAN DEFAULT FALSE
            """)
            print("   ✅ two_factor_always_required column added (default: FALSE)")
        else:
            print("\n✓ two_factor_always_required column already exists")
        
        # Add two_factor_require_on_login if not exists
        if 'two_factor_require_on_login' not in existing_column_names:
            print("\n➕ Adding two_factor_require_on_login column...")
            rds_db.execute_query("""
                ALTER TABLE users 
                ADD COLUMN two_factor_require_on_login BOOLEAN DEFAULT TRUE
            """)
            print("   ✅ two_factor_require_on_login column added (default: TRUE)")
        else:
            print("\n✓ two_factor_require_on_login column already exists")
        
        # Update existing users to have default values
        print("\n🔄 Updating existing users with default values...")
        update_query = """
        UPDATE users 
        SET two_factor_inactivity_timeout = COALESCE(two_factor_inactivity_timeout, 600),
            two_factor_always_required = COALESCE(two_factor_always_required, FALSE),
            two_factor_require_on_login = COALESCE(two_factor_require_on_login, TRUE)
        WHERE two_factor_inactivity_timeout IS NULL 
           OR two_factor_always_required IS NULL 
           OR two_factor_require_on_login IS NULL
        """
        rds_db.execute_query(update_query)
        print("   ✅ Existing users updated with default values")
        
        # Verify columns were added
        print("\n🔍 Verifying columns...")
        verify_query = """
        SELECT column_name, data_type, column_default
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name IN ('two_factor_inactivity_timeout', 'two_factor_always_required', 'two_factor_require_on_login')
        ORDER BY column_name
        """
        
        columns = rds_db.execute_query(verify_query, fetch_all=True)
        
        if columns:
            print("\n✅ 2FA Settings Columns:")
            for col in columns:
                print(f"   • {col['column_name']}: {col['data_type']} (default: {col['column_default']})")
        
        # Show sample data
        print("\n📊 Sample user data:")
        sample_query = """
        SELECT 
            firebase_uid,
            email,
            two_factor_enabled,
            two_factor_inactivity_timeout,
            two_factor_always_required,
            two_factor_require_on_login
        FROM users 
        LIMIT 3
        """
        
        sample_users = rds_db.execute_query(sample_query, fetch_all=True)
        
        if sample_users:
            for user in sample_users:
                print(f"\n   User: {user['email']}")
                print(f"   - 2FA Enabled: {user.get('two_factor_enabled', False)}")
                print(f"   - Inactivity Timeout: {user.get('two_factor_inactivity_timeout', 600)}s")
                print(f"   - Always Required: {user.get('two_factor_always_required', False)}")
                print(f"   - Require on Login: {user.get('two_factor_require_on_login', True)}")
        
        print("\n" + "="*70)
        print("✅ 2FA Settings Columns Added Successfully!")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error adding 2FA settings columns: {e}")
        print("="*70 + "\n")
        import traceback
        traceback.print_exc()
        return False


def verify_user_id_column():
    """Verify the users table id column type"""
    
    print("\n" + "="*70)
    print("Verifying Users Table ID Column")
    print("="*70 + "\n")
    
    try:
        # Check id column type
        check_query = """
        SELECT column_name, data_type, udt_name
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'id'
        """
        
        result = rds_db.execute_query(check_query, fetch_one=True)
        
        if result:
            print(f"📋 Users table 'id' column:")
            print(f"   - Column: {result['column_name']}")
            print(f"   - Data Type: {result['data_type']}")
            print(f"   - UDT Name: {result['udt_name']}")
            
            if result['udt_name'] == 'uuid':
                print("\n⚠️  WARNING: 'id' column is UUID type")
                print("   Firebase UIDs are strings, not UUIDs")
                print("   Consider using 'firebase_uid' column for user identification")
            else:
                print(f"\n✅ 'id' column type: {result['data_type']}")
        
        # Check if firebase_uid column exists
        check_firebase_uid = """
        SELECT column_name, data_type
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'firebase_uid'
        """
        
        firebase_result = rds_db.execute_query(check_firebase_uid, fetch_one=True)
        
        if firebase_result:
            print(f"\n✅ 'firebase_uid' column exists: {firebase_result['data_type']}")
            print("   Use 'firebase_uid' for user identification with Firebase")
        else:
            print("\n⚠️  'firebase_uid' column not found")
        
        print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error verifying user id column: {e}")
        print("="*70 + "\n")


if __name__ == "__main__":
    print("\n🚀 Starting 2FA Settings Migration...\n")
    
    # First verify the user id column
    verify_user_id_column()
    
    # Then add 2FA settings columns
    success = add_2fa_settings_columns()
    
    if success:
        print("✅ Migration completed successfully!")
        print("\nYou can now:")
        print("1. Restart the backend: python app.py")
        print("2. Test 2FA settings: Go to Settings → Security → 2FA Settings")
        print("3. Configure inactivity timeout, always require, etc.")
    else:
        print("❌ Migration failed. Please check the errors above.")
        sys.exit(1)
