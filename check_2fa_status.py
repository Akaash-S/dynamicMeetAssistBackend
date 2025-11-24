"""
Check 2FA Status for User
==========================
This script checks the current 2FA status and secret for a user.
Use this to debug 2FA issues.

Usage:
    python check_2fa_status.py your-email@example.com
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


def check_2fa_status(email: str):
    """Check 2FA status for a specific user"""
    
    logger.info("=" * 60)
    logger.info("🔍 CHECKING 2FA STATUS")
    logger.info("=" * 60)
    logger.info(f"📧 Email: {email}")
    logger.info("")
    
    try:
        # Get user info
        user_query = """
        SELECT 
            firebase_uid,
            email,
            name,
            two_factor_enabled,
            two_factor_method,
            two_factor_secret,
            backup_codes,
            created_at,
            updated_at
        FROM users 
        WHERE email = %s
        """
        
        user = rds_db.execute_query(user_query, (email,), fetch_one=True)
        
        if not user:
            logger.error(f"❌ User not found with email: {email}")
            return False
        
        logger.info(f"✅ User found:")
        logger.info(f"   Name: {user['name']}")
        logger.info(f"   Email: {user['email']}")
        logger.info(f"   Firebase UID: {user['firebase_uid']}")
        logger.info("")
        
        logger.info(f"🔐 2FA Status:")
        logger.info(f"   Enabled: {user['two_factor_enabled']}")
        logger.info(f"   Method: {user['two_factor_method']}")
        
        if user['two_factor_secret']:
            secret = user['two_factor_secret']
            logger.info(f"   Secret: {secret[:8]}...{secret[-4:]} (truncated)")
            logger.info(f"   Secret Length: {len(secret)} characters")
        else:
            logger.info(f"   Secret: None")
        
        if user['backup_codes']:
            import json
            try:
                backup_codes = json.loads(user['backup_codes'])
                total_codes = len(backup_codes)
                used_codes = sum(1 for code in backup_codes if code.get('used', False))
                remaining_codes = total_codes - used_codes
                logger.info(f"   Backup Codes: {remaining_codes}/{total_codes} remaining")
            except:
                logger.info(f"   Backup Codes: Error parsing")
        else:
            logger.info(f"   Backup Codes: None")
        
        logger.info("")
        logger.info(f"📅 Timestamps:")
        logger.info(f"   Created: {user['created_at']}")
        logger.info(f"   Updated: {user['updated_at']}")
        logger.info("")
        
        # Check sessions
        sessions_query = """
        SELECT 
            id,
            session_type,
            created_at,
            logged_out_at
        FROM user_sessions
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 5
        """
        
        sessions = rds_db.execute_query(sessions_query, (user['firebase_uid'],), fetch_all=True)
        
        if sessions:
            logger.info(f"📊 Recent Sessions ({len(sessions)}):")
            for session in sessions:
                logger.info(f"   - {session['session_type']}: {session['created_at']}")
        else:
            logger.info(f"📊 No sessions found")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ CHECK COMPLETE")
        logger.info("=" * 60)
        
        # Provide recommendations
        logger.info("")
        logger.info("💡 Recommendations:")
        
        if user['two_factor_enabled'] and not user['two_factor_secret']:
            logger.warning("⚠️  2FA is enabled but no secret found!")
            logger.warning("   Run: python reset_2fa_for_user.py " + email)
        
        if user['two_factor_enabled'] and user['two_factor_secret']:
            logger.info("✅ 2FA is properly configured")
            logger.info("   Test with your authenticator app")
        
        if not user['two_factor_enabled']:
            logger.info("ℹ️  2FA is disabled")
            logger.info("   Enable it in Settings → Security")
        
        logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking 2FA status: {e}")
        logger.error("", exc_info=True)
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("\n" + "=" * 60)
        print("Check 2FA Status for User")
        print("=" * 60)
        print("\nUsage:")
        print("  python check_2fa_status.py <email>")
        print("\nExample:")
        print("  python check_2fa_status.py user@example.com")
        print("\n" + "=" * 60 + "\n")
        sys.exit(1)
    
    email = sys.argv[1]
    success = check_2fa_status(email)
    
    sys.exit(0 if success else 1)
