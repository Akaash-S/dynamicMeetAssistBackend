"""
Simple RDS Connection Test
Tests direct connection to RDS without using the connection pool
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from backend/.env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

print(f"📁 Loading .env from: {env_path}")
print(f"   File exists: {env_path.exists()}")

def test_direct_connection():
    """Test direct connection to RDS"""
    print("\n" + "="*70)
    print("  RDS DIRECT CONNECTION TEST")
    print("="*70)
    
    # Get credentials
    host = os.getenv('RDS_HOST')
    port = os.getenv('RDS_PORT', '5432')
    database = os.getenv('RDS_DATABASE')
    user = os.getenv('RDS_USER')
    password = os.getenv('RDS_PASSWORD')
    
    # Check if credentials are configured
    print("\n📋 Configuration:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Database: {database}")
    print(f"   User: {user}")
    print(f"   Password: {'*' * len(password) if password else 'NOT SET'}")
    
    if not all([host, database, user, password]):
        print("\n❌ Missing required credentials in .env file")
        print("\nRequired environment variables:")
        print("  - RDS_HOST")
        print("  - RDS_DATABASE")
        print("  - RDS_USER")
        print("  - RDS_PASSWORD")
        return False
    
    # Test connection
    print("\n🔍 Testing connection...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=10,
            sslmode='prefer'
        )
        
        print("✅ Connection successful!")
        
        # Test query
        print("\n🔍 Testing query...")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ PostgreSQL version: {version[:50]}...")
        
        # Check tables
        print("\n🔍 Checking tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("⚠️  No tables found in database")
            print("   You may need to run: python backend/initialize.py")
        
        # Check users table
        print("\n🔍 Checking users table...")
        try:
            cursor.execute("SELECT COUNT(*) FROM users;")
            user_count = cursor.fetchone()[0]
            print(f"✅ Users table exists with {user_count} users")
        except psycopg2.Error as e:
            print(f"⚠️  Users table check failed: {e}")
            print("   You may need to initialize the database")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        print("\nYour RDS connection is working correctly!")
        print("If diagnose_auth_issue.py still fails, try:")
        print("  1. Restart your terminal/IDE")
        print("  2. Run: python backend/initialize.py")
        print("  3. Check for any firewall/antivirus blocking connections")
        print("="*70 + "\n")
        
        return True
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        print(f"\n❌ Connection failed: {error_msg}")
        
        print("\n🔍 Troubleshooting:")
        
        if "could not connect to server" in error_msg.lower():
            print("  ❌ Cannot reach RDS server")
            print("     → Check if RDS instance is running in AWS Console")
            print("     → Verify RDS_HOST is correct")
            print("     → Check security group allows inbound on port 5432")
            print("     → Verify your IP is whitelisted in security group")
            
        elif "password authentication failed" in error_msg.lower():
            print("  ❌ Authentication failed")
            print("     → Check RDS_USER is correct")
            print("     → Check RDS_PASSWORD is correct")
            print("     → Verify user has access to the database")
            
        elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
            print("  ❌ Database does not exist")
            print("     → Check RDS_DATABASE name is correct")
            print("     → Create database if it doesn't exist")
            
        elif "timeout" in error_msg.lower():
            print("  ❌ Connection timeout")
            print("     → Check network connectivity")
            print("     → Verify security group rules")
            print("     → Check if VPN is required")
            
        else:
            print("  ❌ Unknown error")
            print("     → Check all credentials in .env file")
            print("     → Verify RDS instance is publicly accessible (if needed)")
            print("     → Check AWS RDS logs for more details")
        
        print("\n" + "="*70 + "\n")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print(f"   Error type: {type(e).__name__}")
        print("\n" + "="*70 + "\n")
        return False

if __name__ == "__main__":
    success = test_direct_connection()
    sys.exit(0 if success else 1)
