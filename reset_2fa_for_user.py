"""
Reset 2FA for User
===================
This script disables 2FA for a specific user account.
Use this when you've lost access to your authenticator app.

Usage:
    python reset_2fa_for_user.py your-email@example.com
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from config.aws_rds_database import rds_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reset_2fa_for_user(email: str):
    """Reset 2FA for a specific user"""
    
    logger.info("=" * 60)
    logger.info("🔧 RESETTING 2FA FOR USER")
    logger.info("=" * 60)
    logger.info(f"📧 Email: {email}")
    logger.info("")
    
    try:
        # Check if user exists
        user_query = """
        SELECT 
            firebase_uid,
            email,
            name,
            two_factor_enabled,
            two_factor_method
        FROM users 
        WHERE email = %s
        """
        
        user = rds_db.execute_query(user_query, (email,), fetch_one=True)
        
        if not user:
            logger.error(f"❌ User not found with email: {email}")
            logger.error("   Please check the email address and try again.")
            return False
        
        logger.info(f"✅ User found:")
        logger.info(f"   Name: {user['name']}")
        logger.info(f"   Email: {user['email']}")
        logger.info(f"   Firebase UID: {user['firebase_uid']}")
        logger.info(f"   2FA Enabled: {user['two_factor_enabled']}")
        logger.info(f"   2FA Method: {user['two_factor_method']}")
        logger.info("")
        
        if not user['two_factor_enabled']:
            logger.info("ℹ️  2FA is already disabled for this user.")
            logger.info("   No action needed.")
            return True
        
        # Disable 2FA
        logger.info("🔄 Disabling 2FA...")
        
        reset_query = """
        UPDATE users 
        SET 
            two_factor_enabled = false,
            two_factor_method = NULL,
            two_factor_secret = NULL,
            backup_codes = NULL,
            updated_at = NOW()
        WHERE email = %s
        """
        
        rds_db.execute_query(reset_query, (email,))
        
        logger.info("✅ 2FA disabled successfully!")
        logger.info("")
        
        # Also clear any active sessions to force re-login
        logger.info("🔄 Clearing active sessions...")
        
        clear_sessions_query = """
        DELETE FROM user_sessions 
        WHERE user_id = %s
        """
        
        rds_db.execute_query(clear_sessions_query, (user['firebase_uid'],))
        
        logger.info("✅ Sessions cleared!")
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 2FA RESET COMPLETE")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Login to your account")
        logger.info("2. Go to Settings → Security")
        logger.info("3. Enable 2FA again with a new QR code")
        logger.info("4. Save the backup codes this time!")
        logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error resetting 2FA: {e}")
        logger.error("", exc_info=True)
        return False


def reset_all_2fa():
    """Reset 2FA for ALL users (use with caution!)"""
    
    logger.info("=" * 60)
    logger.info("⚠️  RESETTING 2FA FOR ALL USERS")
    logger.info("=" * 60)
    logger.info("")
    
    # Ask for confirmation
    confirm = input("Are you sure you want to disable 2FA for ALL users? (yes/no): ")
    if confirm.lower() != 'yes':
        logger.info("❌ Operation cancelled.")
        return False
    
    try:
        # Get count of users with 2FA enabled
        count_query = "SELECT COUNT(*) as count FROM users WHERE two_factor_enabled = true"
        result = rds_db.execute_query(count_query, fetch_one=True)
        count = result['count'] if result else 0
        
        logger.info(f"📊 Found {count} users with 2FA enabled")
        logger.info("")
        
        if count == 0:
            logger.info("ℹ️  No users have 2FA enabled.")
            return True
        
        # Disable 2FA for all users
        logger.info("🔄 Disabling 2FA for all users...")
        
        reset_query = """
        UPDATE users 
        SET 
            two_factor_enabled = false,
            two_factor_method = NULL,
            two_factor_secret = NULL,
            backup_codes = NULL,
            updated_at = NOW()
        WHERE two_factor_enabled = true
        """
        
        rows_updated = rds_db.execute_query(reset_query)
        
        logger.info(f"✅ 2FA disabled for {rows_updated} users!")
        logger.info("")
        
        # Clear all sessions
        logger.info("🔄 Clearing all sessions...")
        
        clear_sessions_query = "DELETE FROM user_sessions"
        sessions_deleted = rds_db.execute_query(clear_sessions_query)
        
        logger.info(f"✅ {sessions_deleted} sessions cleared!")
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ BULK 2FA RESET COMPLETE")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error resetting 2FA: {e}")
        logger.error("", exc_info=True)
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("\n" + "=" * 60)
        print("Reset 2FA for User")
        print("=" * 60)
        print("\nUsage:")
        print("  python reset_2fa_for_user.py <email>")
        print("  python reset_2fa_for_user.py --all")
        print("\nExamples:")
        print("  python reset_2fa_for_user.py user@example.com")
        print("  python reset_2fa_for_user.py --all  (resets for ALL users)")
        print("\n" + "=" * 60 + "\n")
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        success = reset_all_2fa()
    else:
        email = sys.argv[1]
        success = reset_2fa_for_user(email)
    
    sys.exit(0 if success else 1)
