"""
Initialize Chatbot Database Tables
===================================
Creates the necessary database tables for chatbot functionality
"""

import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from config.aws_rds_database import rds_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_chatbot_tables():
    """Create chatbot tables"""
    
    # Read SQL file
    with open('migrations/create_chatbot_tables.sql', 'r') as f:
        sql = f.read()
    
    try:
        # Execute SQL
        rds_db.execute_query(sql)
        logger.info("✓ Chatbot tables created successfully")
        
        # Verify tables
        verify_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('chatbot_sessions', 'chatbot_messages')
        """
        
        result = rds_db.execute_query(verify_query, fetch_all=True)
        if result:
            logger.info(f"✓ Verified tables: {[row['table_name'] for row in result]}")
        else:
            logger.warning("⚠ No chatbot tables found")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error creating chatbot tables: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Chatbot Database Initialization")
    print("=" * 60 + "\n")
    
    success = init_chatbot_tables()
    
    if success:
        print("\n✓ Chatbot database initialized successfully!")
        print("\nNext steps:")
        print("1. Add environment variables to .env:")
        print("   - GROQ_API_KEY")
        print("   - GROQ_API_KEY_TWO (for voice)")
        print("   - ELEVENLABS_API_KEY (optional, for TTS)")
        print("2. Run: python -m chatbot.service to test")
        print("3. Start the server: python app.py")
    else:
        print("\n✗ Failed to initialize chatbot database")
        print("Please check the error messages above")
    
    print("\n" + "=" * 60 + "\n")
