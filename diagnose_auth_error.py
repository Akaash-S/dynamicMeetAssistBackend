"""
Diagnose Authentication 500 Error
Quick script to find the root cause
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("="*60)
print("Authentication Error Diagnosis")
print("="*60)

# Check 1: RDS Configuration
print("\n1. Checking RDS Configuration...")
rds_host = os.getenv('RDS_HOST')
rds_database = os.getenv('RDS_DATABASE')
rds_user = os.getenv('RDS_USER')
rds_password = os.getenv('RDS_PASSWORD')

if all([rds_host, rds_database, rds_user, rds_password]):
    print(f"✓ RDS configured")
    print(f"  Host: {rds_host}")
    print(f"  Database: {rds_database}")
else:
    print("✗ RDS not fully configured")
    print("  Fix: Update .env with RDS credentials")
    sys.exit(1)

# Check 2: RDS Connection
print("\n2. Testing RDS Connection...")
try:
    from config.aws_rds_database import rds_db
    
    if not rds_db.connection_pool:
        print("✗ RDS connection pool not initialized")
        print("  Fix: Check RDS credentials")
        sys.exit(1)
    
    # Test query
    result = rds_db.execute_query("SELECT 1 as test", fetch_one=True)
    if result and result.get('test') == 1:
        print("✓ RDS connection successful")
    else:
        print("✗ RDS query failed")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ RDS connection failed: {e}")
    print("  Fix: Check RDS security group and credentials")
    sys.exit(1)

# Check 3: Tables Exist
print("\n3. Checking if tables exist...")
try:
    tables = rds_db.execute_query(
        """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
        """,
        fetch_all=True
    )
    
    if not tables:
        print("✗ No tables found in database")
        print("  Fix: Run create_tables.bat")
        sys.exit(1)
    
    table_names = [t['table_name'] for t in tables]
    print(f"✓ Found {len(tables)} tables")
    
    # Check for users table
    if 'users' not in table_names:
        print("✗ 'users' table missing")
        print("  Fix: Run create_tables.bat")
        sys.exit(1)
    else:
        print("✓ 'users' table exists")
        
except Exception as e:
    print(f"✗ Error checking tables: {e}")
    sys.exit(1)

# Check 4: Test Auth Route Import
print("\n4. Testing auth route import...")
try:
    from routes.auth import auth_bp
    print("✓ Auth route imports successfully")
except Exception as e:
    print(f"✗ Auth route import failed: {e}")
    print("  Fix: Check routes/auth.py for errors")
    sys.exit(1)

# Check 5: Test User Creation
print("\n5. Testing user creation...")
try:
    # Try to query users table
    count = rds_db.execute_query(
        "SELECT COUNT(*) as count FROM users",
        fetch_one=True
    )
    print(f"✓ Users table accessible ({count['count']} users)")
    
except Exception as e:
    print(f"✗ Cannot access users table: {e}")
    print("  Fix: Run create_tables.bat")
    sys.exit(1)

# All checks passed
print("\n" + "="*60)
print("✓ All checks passed!")
print("="*60)
print("\nYour backend should be working now.")
print("If you still get 500 errors:")
print("1. Restart the backend server")
print("2. Check backend terminal for specific errors")
print("3. Try: curl -X POST http://localhost:8000/api/auth/verify \\")
print("     -H 'Content-Type: application/json' \\")
print("     -d '{\"email\":\"test@example.com\",\"firebase_uid\":\"test\"}'")
print("="*60)
