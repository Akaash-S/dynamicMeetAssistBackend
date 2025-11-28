"""
Delete User from Database
This script helps you remove a user and all their associated data from the database.
"""

import os
import sys
from dotenv import load_dotenv
from config.aws_rds_database import get_rds_connection

# Load environment variables
load_dotenv()


def delete_user_by_email(email):
    """
    Delete a user and all their associated data by email address.
    
    Args:
        email (str): The email address of the user to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = None
    try:
        conn = get_rds_connection().__enter__()
        cursor = conn.cursor()
        
        # First, check if user exists
        cursor.execute("SELECT id, email, name, firebase_uid FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User with email '{email}' not found in database.")
            return False
        
        user_id = user['id']
        user_name = user['name']
        firebase_uid = user['firebase_uid']
        
        print(f"\n📋 User found:")
        print(f"   ID: {user_id}")
        print(f"   Name: {user_name}")
        print(f"   Email: {email}")
        print(f"   Firebase UID: {firebase_uid}")
        
        # Confirm deletion
        confirm = input(f"\n⚠️  Are you sure you want to delete this user and ALL their data? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Deletion cancelled.")
            return False
        
        print("\n🗑️  Deleting user data...")
        
        # List of tables to delete from (in order)
        tables_to_clean = [
            "notifications",
            "tasks", 
            "meetings",
            "chatbot_conversations",
            "chatbot_sessions",
            "two_factor_auth",
            "user_sessions"
        ]
        
        # Delete from each table
        for table_name in tables_to_clean:
            try:
                cursor.execute(f"DELETE FROM {table_name} WHERE user_id = %s", (user_id,))
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    print(f"   ✓ Deleted {deleted_count} records from {table_name}")
                else:
                    print(f"   ○ No records in {table_name}")
            except Exception as e:
                error_msg = str(e).lower()
                if "does not exist" in error_msg or "relation" in error_msg:
                    print(f"   ○ Table '{table_name}' does not exist (skipping)")
                    # Rollback this failed query and continue
                    conn.rollback()
                else:
                    print(f"   ⚠️  Could not delete from {table_name}: {str(e)[:100]}")
                    conn.rollback()
        
        # Finally, delete the user
        try:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            print(f"   ✓ Deleted user account")
            
            # Commit all successful deletions
            conn.commit()
            
            print(f"\n✅ User '{email}' and all associated data have been successfully deleted!")
            return True
        except Exception as e:
            print(f"   ❌ Error deleting user account: {e}")
            conn.rollback()
            return False
            
    except Exception as e:
        print(f"\n❌ Error deleting user: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def delete_user_by_id(user_id):
    """
    Delete a user and all their associated data by user ID.
    
    Args:
        user_id (str): The ID of the user to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = None
    try:
        conn = get_rds_connection().__enter__()
        cursor = conn.cursor()
        
        # First, check if user exists
        cursor.execute("SELECT id, email, name, firebase_uid FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User with ID '{user_id}' not found in database.")
            return False
        
        email = user['email']
        user_name = user['name']
        firebase_uid = user['firebase_uid']
        
        print(f"\n📋 User found:")
        print(f"   ID: {user_id}")
        print(f"   Name: {user_name}")
        print(f"   Email: {email}")
        print(f"   Firebase UID: {firebase_uid}")
        
        # Confirm deletion
        confirm = input(f"\n⚠️  Are you sure you want to delete this user and ALL their data? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Deletion cancelled.")
            return False
        
        print("\n🗑️  Deleting user data...")
        
        # List of tables to delete from (in order)
        tables_to_clean = [
            "notifications",
            "tasks",
            "meetings",
            "chatbot_conversations",
            "chatbot_sessions",
            "two_factor_auth",
            "user_sessions"
        ]
        
        # Delete from each table
        for table_name in tables_to_clean:
            try:
                cursor.execute(f"DELETE FROM {table_name} WHERE user_id = %s", (user_id,))
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    print(f"   ✓ Deleted {deleted_count} records from {table_name}")
                else:
                    print(f"   ○ No records in {table_name}")
            except Exception as e:
                error_msg = str(e).lower()
                if "does not exist" in error_msg or "relation" in error_msg:
                    print(f"   ○ Table '{table_name}' does not exist (skipping)")
                    # Rollback this failed query and continue
                    conn.rollback()
                else:
                    print(f"   ⚠️  Could not delete from {table_name}: {str(e)[:100]}")
                    conn.rollback()
        
        # Finally, delete the user
        try:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            print(f"   ✓ Deleted user account")
            
            # Commit all successful deletions
            conn.commit()
            
            print(f"\n✅ User '{email}' (ID: {user_id}) and all associated data have been successfully deleted!")
            return True
        except Exception as e:
            print(f"   ❌ Error deleting user account: {e}")
            conn.rollback()
            return False
            
    except Exception as e:
        print(f"\n❌ Error deleting user: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def list_users():
    """List all users in the database"""
    conn = None
    try:
        conn = get_rds_connection().__enter__()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, email, name, firebase_uid, auth_provider, created_at 
            FROM users 
            ORDER BY created_at DESC
        """)
        users = cursor.fetchall()
        
        if not users:
            print("\n📋 No users found in database.")
            return
        
        print(f"\n📋 Found {len(users)} user(s):\n")
        for i, user in enumerate(users, 1):
            print(f"{i}. {user['name']} ({user['email']})")
            print(f"   ID: {user['id']}")
            print(f"   Firebase UID: {user['firebase_uid']}")
            print(f"   Auth Provider: {user['auth_provider']}")
            print(f"   Created: {user['created_at']}")
            print()
            
    except Exception as e:
        print(f"❌ Error listing users: {e}")
    finally:
        if conn:
            conn.close()


def main():
    """Main function to handle user deletion"""
    print("=" * 60)
    print("🗑️  USER DELETION TOOL")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        # Command line argument provided
        identifier = sys.argv[1]
        
        # Check if it's an email or ID
        if '@' in identifier:
            delete_user_by_email(identifier)
        else:
            delete_user_by_id(identifier)
    else:
        # Interactive mode
        print("\nOptions:")
        print("1. List all users")
        print("2. Delete user by email")
        print("3. Delete user by ID")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == '1':
            list_users()
        elif choice == '2':
            email = input("\nEnter user email: ")
            if email:
                delete_user_by_email(email)
            else:
                print("❌ Email cannot be empty")
        elif choice == '3':
            user_id = input("\nEnter user ID: ")
            if user_id:
                delete_user_by_id(user_id)
            else:
                print("❌ User ID cannot be empty")
        elif choice == '4':
            print("👋 Exiting...")
        else:
            print("❌ Invalid choice. Please enter 1-4.")


if __name__ == "__main__":
    main()
