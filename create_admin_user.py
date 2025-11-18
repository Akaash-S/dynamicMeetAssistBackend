"""
Create Admin User in RDS Database
==================================
This script creates an admin user with hashed password in the users table.
"""
import os
import sys
import bcrypt
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from config.aws_rds_database import rds_db

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_admin_user():
    """Create admin user in database"""
    print("=" * 60)
    print("CREATING ADMIN USER")
    print("=" * 60)
    print()
    
    # Admin credentials
    admin_email = "akaash.meetingmind@admin.com"
    admin_password = "MeetingMind@Ak-25"
    admin_name = "Akaash Admin"
    
    print(f"📧 Email: {admin_email}")
    print(f"👤 Name: {admin_name}")
    print(f"🔐 Password: {'*' * len(admin_password)}")
    print()
    
    try:
        # Test database connection
        print("🔍 Testing database connection...")
        test_result = rds_db.execute_query("SELECT 1 as test", fetch_one=True)
        if not test_result:
            print("❌ Database connection failed!")
            return False
        print("✅ Database connected!")
        print()
        
        # Check if admin already exists
        print("🔍 Checking if admin user already exists...")
        check_query = "SELECT * FROM users WHERE email = %s"
        existing_user = rds_db.execute_query(check_query, (admin_email,), fetch_all=True)
        
        if existing_user:
            print("⚠️  Admin user already exists!")
            print()
            
            # Ask if user wants to update password
            response = input("Do you want to update the password? (yes/no): ").lower()
            if response != 'yes':
                print("❌ Operation cancelled.")
                return False
            
            # Hash new password
            print()
            print("🔐 Hashing password...")
            password_hash = hash_password(admin_password)
            print("✅ Password hashed!")
            
            # Update existing user
            print()
            print("📝 Updating admin user...")
            update_query = """
            UPDATE users 
            SET password_hash = %s, 
                name = %s,
                role = 'admin',
                updated_at = %s
            WHERE email = %s
            """
            
            rds_db.execute_query(update_query, (
                password_hash,
                admin_name,
                datetime.utcnow(),
                admin_email
            ))
            
            print("✅ Admin user updated successfully!")
            print()
            print("=" * 60)
            print("ADMIN CREDENTIALS")
            print("=" * 60)
            print(f"Email: {admin_email}")
            print(f"Password: {admin_password}")
            print("=" * 60)
            
        else:
            print("✅ No existing admin user found.")
            print()
            
            # Hash password
            print("🔐 Hashing password...")
            password_hash = hash_password(admin_password)
            print("✅ Password hashed!")
            
            # Create new admin user
            print()
            print("📝 Creating admin user...")
            admin_id = str(uuid.uuid4())
            
            insert_query = """
            INSERT INTO users (
                id, 
                email, 
                name, 
                password_hash, 
                role, 
                auth_provider,
                email_notifications,
                in_app_notifications,
                created_at, 
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            rds_db.execute_query(insert_query, (
                admin_id,
                admin_email,
                admin_name,
                password_hash,
                'admin',
                'email',
                True,
                True,
                datetime.utcnow(),
                datetime.utcnow()
            ))
            
            print("✅ Admin user created successfully!")
            print()
            print("=" * 60)
            print("ADMIN CREDENTIALS")
            print("=" * 60)
            print(f"ID: {admin_id}")
            print(f"Email: {admin_email}")
            print(f"Password: {admin_password}")
            print(f"Role: admin")
            print("=" * 60)
        
        print()
        print("🎉 Admin user is ready!")
        print()
        print("You can now login to the admin dashboard with:")
        print(f"  Email: {admin_email}")
        print(f"  Password: {admin_password}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    print()
    success = create_admin_user()
    print()
    
    if success:
        print("✅ Setup completed successfully!")
    else:
        print("❌ Setup failed! Check the errors above.")
    
    print()
