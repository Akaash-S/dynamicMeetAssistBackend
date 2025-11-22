"""Create admin user in database"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.aws_rds_database import rds_db
from config.auth_config import AuthConfig
import uuid
from datetime import datetime

email = AuthConfig.DEFAULT_ADMIN_EMAIL
name = AuthConfig.DEFAULT_ADMIN_NAME

print(f"Creating admin user: {email}")

# Check if user exists
user_query = "SELECT * FROM users WHERE email = %s"
user = rds_db.execute_query(user_query, (email,), fetch_one=True)

if user:
    print(f"User already exists: {user}")
    print(f"Role: {user.get('role')}")
else:
    # Create admin user
    user_id = str(uuid.uuid4())
    create_query = """
    INSERT INTO users (id, email, name, role, auth_provider, is_active, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    rds_db.execute_query(create_query, (
        user_id, email, name, 'admin', 'admin_email', True, datetime.utcnow(), datetime.utcnow()
    ))
    print(f"Admin user created successfully!")
    print(f"Email: {email}")
    print(f"Password: {AuthConfig.DEFAULT_ADMIN_PASSWORD}")
