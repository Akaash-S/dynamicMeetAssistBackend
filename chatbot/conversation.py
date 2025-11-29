"""
Conversation Manager
====================
Manages conversation sessions and message history
"""

import uuid
from datetime import datetime
from typing import List, Dict, Optional
from config.aws_rds_database import rds_db
import logging

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation sessions and history"""
    
    def __init__(self, user_id: str):
        """
        Initialize conversation manager for a user
        
        Args:
            user_id: User ID
        """
        self.user_id = user_id
    
    def create_session(self) -> str:
        """
        Create new conversation session
        
        Returns:
            Session ID
        """
        try:
            session_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO chatbot_sessions (id, user_id, created_at, updated_at, message_count, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            rds_db.execute_query(query, (
                session_id,
                self.user_id,
                datetime.utcnow(),
                datetime.utcnow(),
                0,
                True
            ))
            
            logger.info(f"Created session {session_id} for user {self.user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise e
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add message to conversation history
        
        Args:
            session_id: Session ID
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional metadata
        """
        try:
            import json
            
            message_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO chatbot_messages (id, session_id, role, content, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            rds_db.execute_query(query, (
                message_id,
                session_id,
                role,
                content,
                json.dumps(metadata) if metadata else None,
                datetime.utcnow()
            ))
            
            # Update session
            update_query = """
            UPDATE chatbot_sessions 
            SET message_count = message_count + 1, updated_at = %s
            WHERE id = %s
            """
            rds_db.execute_query(update_query, (datetime.utcnow(), session_id))
            
            logger.info(f"Added {role} message to session {session_id}")
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise e
    
    def get_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get conversation history
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            
        Returns:
            List of messages
        """
        try:
            query = """
            SELECT id, role, content, metadata, created_at
            FROM chatbot_messages
            WHERE session_id = %s
            ORDER BY created_at ASC
            LIMIT %s
            """
            
            results = rds_db.execute_query(query, (session_id, limit), fetch_all=True)
            
            messages = []
            if results:
                import json
                for row in results:
                    messages.append({
                        'id': row['id'],
                        'role': row['role'],
                        'content': row['content'],
                        'metadata': row['metadata'] if row['metadata'] else {},
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None
                    })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            raise e
    
    def get_recent_messages(
        self,
        session_id: str,
        count: int = 10
    ) -> List[Dict]:
        """
        Get recent messages for context
        
        Args:
            session_id: Session ID
            count: Number of recent messages
            
        Returns:
            List of recent messages
        """
        try:
            query = """
            SELECT role, content
            FROM chatbot_messages
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """
            
            results = rds_db.execute_query(query, (session_id, count), fetch_all=True)
            
            # Reverse to get chronological order
            messages = []
            if results:
                for row in reversed(results):
                    messages.append({
                        'role': row['role'],
                        'content': row['content']
                    })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            return []
    
    def clear_session(self, session_id: str):
        """
        Clear conversation history for a session
        
        Args:
            session_id: Session ID
        """
        try:
            # Check if tables exist first
            try:
                # Delete messages
                delete_messages = "DELETE FROM chatbot_messages WHERE session_id = %s"
                rds_db.execute_query(delete_messages, (session_id,), fetch_one=False)
                
                # Update session
                update_session = """
                UPDATE chatbot_sessions 
                SET message_count = 0, updated_at = %s
                WHERE id = %s
                """
                rds_db.execute_query(update_session, (datetime.utcnow(), session_id), fetch_one=False)
                
                logger.info(f"Cleared session {session_id}")
                
            except Exception as table_error:
                # If tables don't exist, that's okay - nothing to clear
                if 'does not exist' in str(table_error).lower():
                    logger.info(f"Chatbot tables don't exist yet - nothing to clear")
                else:
                    raise table_error
            
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
            # Don't raise - just log the error and continue
            # This prevents 500 errors when clearing non-existent sessions
    
    def get_user_sessions(self, limit: int = 10) -> List[Dict]:
        """
        Get user's conversation sessions
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of sessions (empty list if table doesn't exist or no sessions)
        """
        try:
            query = """
            SELECT id, created_at, updated_at, message_count, is_active
            FROM chatbot_sessions
            WHERE user_id = %s
            ORDER BY updated_at DESC
            LIMIT %s
            """
            
            results = rds_db.execute_query(query, (self.user_id, limit), fetch_all=True)
            
            sessions = []
            if results:
                for row in results:
                    sessions.append({
                        'id': row['id'],
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                        'message_count': row['message_count'],
                        'is_active': row['is_active']
                    })
            
            return sessions
            
        except Exception as e:
            error_msg = str(e).lower()
            # If table doesn't exist, return empty list instead of error
            if 'does not exist' in error_msg or 'relation' in error_msg:
                logger.info(f"Chatbot sessions table does not exist yet, returning empty list")
                return []
            # For other errors, log and return empty list
            logger.error(f"Error getting user sessions: {e}")
            return []
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if session exists and belongs to user
        
        Args:
            session_id: Session ID
            
        Returns:
            True if session exists
        """
        try:
            query = """
            SELECT id FROM chatbot_sessions
            WHERE id = %s AND user_id = %s
            """
            
            result = rds_db.execute_query(query, (session_id, self.user_id), fetch_all=True)
            return len(result) > 0 if result else False
            
        except Exception as e:
            logger.error(f"Error checking session: {e}")
            return False
