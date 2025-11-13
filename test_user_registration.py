"""
Test User Registration in RDS
Verifies that new users can register in empty RDS database
"""

from config.aws_rds_database import rds_db
import uuid
from datetime import datetime


def test_registration():
    """Test creating a new user in RDS"""
    
    print("\n" + "="*70)
    print("Testing User Registration in RDS")
    print("="*70)
    
    # Check RDS connection
    health = rds_db.health_check()
    if health['status'] != 'healthy':
        print("\n❌ RDS connection failed!")
        print(f"   Error: {health.get('error')}")
        return False
    
    print(f"\n✅ RDS Connected: {health['database']['host']}")
    
    # Test user data
    test_user = {
        'id': str(uuid.uuid4()),
        'email': 'test@example.com',
        'name': 'Test User',
        'firebase_uid': 'test_' + str(uuid.uuid4())[:8],
        'auth_provider': 'google_oauth',
        'role': 'user'
    }
    
    print(f"\n📝 Creating test user: {test_user['email']}")
    
    try:
        # Insert test user
        insert_query = """
        INSERT INTO users (id, firebase_uid, email, name, auth_provider, role, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        rds_db.execute_query(insert_query, (
            test_user['id'],
            test_user['firebase_uid'],
            test_user['email'],
            test_user['name'],
            test_user['auth_provider'],
            test_user['role'],
            True,
            datetime.utcnow(),
            datetime.utcnow()
        ))
        
        print("  ✅ User created successfully!")
        
        # Verify user exists
        verify_query = "SELECT * FROM users WHERE email = %s"
        result = rds_db.execute_query(verify_query, (test_user['email'],), fetch_one=True)
        
        if result:
            print(f"  ✅ User verified in database")
            print(f"     ID: {result['id']}")
            print(f"     Email: {result['email']}")
            print(f"     Name: {result['name']}")
            
            # Clean up test user
            delete_query = "DELETE FROM users WHERE email = %s"
            rds_db.execute_query(delete_query, (test_user['email'],))
            print(f"  ✅ Test user cleaned up")
            
            return True
        else:
            print("  ❌ User not found after creation")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def check_users_table():
    """Check current users in database"""
    
    print("\n" + "="*70)
    print("Current Users in RDS")
    print("="*70)
    
    try:
        query = "SELECT id, email, name, auth_provider, created_at FROM users ORDER BY created_at DESC LIMIT 10"
        users = rds_db.execute_query(query, fetch_all=True)
        
        if users:
            print(f"\n📊 Found {len(users)} users:")
            for user in users:
                print(f"  • {user['email']} ({user['name']}) - {user['auth_provider']}")
        else:
            print("\n📊 No users found (database is empty)")
            print("   Users need to register again after migration")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n🔧 RDS User Registration Test")
    
    # Check existing users
    check_users_table()
    
    # Test registration
    if test_registration():
        print("\n" + "="*70)
        print("✅ User Registration Test: PASSED")
        print("="*70)
        print("\n✅ RDS is ready for user registration!")
        print("\nNext steps:")
        print("  1. Users can register via frontend")
        print("  2. Login with Google will create new users")
        print("  3. All data starts fresh in RDS")
    else:
        print("\n" + "="*70)
        print("❌ User Registration Test: FAILED")
        print("="*70)
        print("\nPlease check:")
        print("  1. RDS connection")
        print("  2. Users table exists")
        print("  3. Credentials are correct")
