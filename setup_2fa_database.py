"""
Setup 2FA Database Tables
Run this script to create the user_sessions table
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from config.aws_rds_database import rds_db
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 70)
print("Enhanced 2FA System - Database Setup")
print("=" * 70)
print()

# Read SQL migration file
migration_file = os.path.join(os.path.dirname(__file__), 'migrations', 'add_user_sessions_table.sql')

try:
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    print("Step 1: Creating user_sessions table...")
    
    # Execute migration
    rds_db.execute_query(sql)
    
    print("✅ user_sessions table created successfully!")
    print()
    
    # Verify table was created
    print("Step 2: Verifying table...")
    verify_query = """
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'user_sessions'
    ORDER BY ordinal_position
    """
    
    columns = rds_db.execute_query(verify_query, fetch_all=True)
    
    if columns:
        print("✅ Table verified! Columns:")
        for col in columns:
            print(f"   - {col['column_name']}: {col['data_type']}")
    else:
        print("⚠️  Could not verify table (but it may still exist)")
    
    print()
    
    # Check 2FA columns in users table
    print("Step 3: Checking 2FA columns in users table...")
    users_query = """
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'users' 
    AND column_name LIKE 'two_factor%'
    """
    
    two_fa_columns = rds_db.execute_query(users_query, fetch_all=True)
    
    if two_fa_columns:
        print("✅ 2FA columns found:")
        for col in two_fa_columns:
            print(f"   - {col['column_name']}")
    else:
        print("⚠️  No 2FA columns found in users table")
        print("   You may need to add them manually:")
        print("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS two_factor_method VARCHAR(50);
        ALTER TABLE users ADD COLUMN IF NOT EXISTS two_factor_secret TEXT;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS backup_codes JSONB;
        """)
    
    print()
    print("=" * 70)
    print("✅ 2FA Database Setup Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Restart backend: python backend/app.py")
    print("2. Test 2FA endpoints")
    print("3. Build frontend components")
    print()
    
except FileNotFoundError:
    print(f"❌ Migration file not found: {migration_file}")
    print("   Make sure the file exists at backend/migrations/add_user_sessions_table.sql")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Error during setup: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
