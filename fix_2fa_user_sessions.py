"""
Fix 2FA User Sessions Table
============================
This script fixes the user_sessions table to use firebase_uid instead of internal UUID.
This is critical for the 2FA system to work correctly.

Run this script to fix the 2FA persistence issue.
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


def fix_user_sessions_table():
    """Fix user_sessions table to use firebase_uid"""
    
    logger.info("=" * 60)
    logger.info("🔧 FIXING USER_SESSIONS TABLE FOR 2FA")
    logger.info("=" * 60)
    
    try:
        # Read the migration SQL
        migration_file = Path(__file__).parent / 'migrations' / 'fix_user_sessions_firebase_uid.sql'
        
        if not migration_file.exists():
            logger.error(f"❌ Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        logger.info("📄 Executing migration SQL...")
        
        # Execute the migration
        rds_db.execute_query(sql)
        
        logger.info("✅ user_sessions table fixed successfully!")
        logger.info("")
        logger.info("The table now uses firebase_uid instead of internal UUID.")
        logger.info("2FA settings will now persist correctly across page refreshes.")
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ MIGRATION COMPLETE")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing user_sessions table: {e}")
        logger.error("", exc_info=True)
        return False


if __name__ == '__main__':
    success = fix_user_sessions_table()
    sys.exit(0 if success else 1)
