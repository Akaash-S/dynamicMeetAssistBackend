"""
Chatbot Service - Enhanced Version
===================================
Intelligent orchestration layer with RAG, action execution, and multi-turn reasoning
"""

from typing import Optional, Dict, Generator, List, Any
from datetime import datetime
from .llm import get_llm_service
from .vector_store import VectorStore
from .conversation import ConversationManager
from .indexer import DataIndexer
from .actions import ActionExecutor
from config.aws_rds_database import rds_db
import json
import logging

logger = logging.getLogger(__name__)


class ChatbotService:
    """Enhanced chatbot service with intelligent context management and action execution"""
    
    def __init__(self, user_id: str):
        """
        Initialize chatbot service for a user
        
        Args:
            user_id: User ID
        """
        self.user_id = user_id
        self.llm_service = get_llm_service()
        self.vector_store = VectorStore(user_id)
        self.conversation_manager = ConversationManager(user_id)
        self.indexer = DataIndexer(user_id)
        self.action_executor = ActionExecutor(user_id)
        
        logger.info(f"Enhanced chatbot service initialized for user {user_id}")
    
    def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        stream: bool = False
    ) -> Dict:
        """
        Process user message with intelligent context retrieval and action execution
        
        Args:
            message: User message
            session_id: Optional session ID
            stream: Whether to stream response
            
        Returns:
            Dict with response, session_id, sources, and executed actions
        """
        try:
            # Create or validate session
            if not session_id:
                session_id = self.conversation_manager.create_session()
            elif not self.conversation_manager.session_exists(session_id):
                session_id = self.conversation_manager.create_session()
            
            # Add user message to history
            self.conversation_manager.add_message(session_id, 'user', message)
            
            # Analyze user intent
            try:
                intent = self._analyze_intent(message)
                logger.info(f"Detected intent: {intent['type']}")
            except Exception as intent_error:
                logger.error(f"Intent analysis failed: {intent_error}")
                # Use default intent
                intent = {
                    'type': 'general_query',
                    'requires_action': False,
                    'entity_type': None,
                    'action_type': None,
                    'temporal_context': None
                }
            
            # Get relevant context with intelligent retrieval
            try:
                context_data = self._retrieve_context(message, intent)
            except Exception as context_error:
                logger.error(f"Context retrieval failed: {context_error}")
                # Use empty context
                context_data = {
                    'text': "No context available.",
                    'sources': [],
                    'search_results': [],
                    'recent_data': []
                }
            
            # Get conversation history for context
            recent_messages = self.conversation_manager.get_recent_messages(session_id, count=10)
            
            # Check if action execution is needed
            action_result = None
            if intent.get('requires_action', False):
                try:
                    action_result = self._execute_action(intent, message, context_data)
                except Exception as action_error:
                    logger.error(f"Action execution failed: {action_error}")
                    # Continue without action result
                    action_result = {
                        'success': False,
                        'error': str(action_error)
                    }
            
            # Build enhanced system prompt
            system_prompt = self._build_enhanced_prompt(
                context_data,
                recent_messages,
                intent,
                action_result
            )
            
            # Generate response
            if stream:
                return self._generate_streaming_response(
                    message, system_prompt, session_id, context_data['sources'], action_result
                )
            else:
                return self._generate_response(
                    message, system_prompt, session_id, context_data['sources'], action_result
                )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            # Return error response instead of raising
            return {
                'response': "I'm sorry, I encountered an error processing your message. Please try again.",
                'session_id': session_id if session_id else 'error',
                'sources': [],
                'action_result': None,
                'error': str(e)
            }
    
    def _analyze_intent(self, message: str) -> Dict:
        """
        Analyze user intent to determine query type and required actions
        
        Args:
            message: User message
            
        Returns:
            Intent classification with metadata
        """
        message_lower = message.lower()
        
        # Action keywords
        create_keywords = ['create', 'add', 'new', 'make']
        update_keywords = ['update', 'change', 'modify', 'edit', 'mark']
        delete_keywords = ['delete', 'remove', 'cancel']
        list_keywords = ['list', 'show', 'what are', 'tell me about', 'get']
        summary_keywords = ['summary', 'summarize', 'overview', 'recap']
        search_keywords = ['find', 'search', 'look for']
        
        # Entity keywords
        task_keywords = ['task', 'todo', 'assignment']
        meeting_keywords = ['meeting', 'call', 'conference']
        deadline_keywords = ['deadline', 'due', 'overdue']
        
        intent = {
            'type': 'general_query',
            'requires_action': False,
            'entity_type': None,
            'action_type': None,
            'temporal_context': None
        }
        
        # Detect action type
        if any(kw in message_lower for kw in create_keywords):
            intent['action_type'] = 'create'
            intent['requires_action'] = True
        elif any(kw in message_lower for kw in update_keywords):
            intent['action_type'] = 'update'
            intent['requires_action'] = True
        elif any(kw in message_lower for kw in delete_keywords):
            intent['action_type'] = 'delete'
            intent['requires_action'] = True
        elif any(kw in message_lower for kw in list_keywords):
            intent['type'] = 'list_query'
        elif any(kw in message_lower for kw in summary_keywords):
            intent['type'] = 'summary_query'
        elif any(kw in message_lower for kw in search_keywords):
            intent['type'] = 'search_query'
        
        # Detect entity type
        if any(kw in message_lower for kw in task_keywords):
            intent['entity_type'] = 'task'
        elif any(kw in message_lower for kw in meeting_keywords):
            intent['entity_type'] = 'meeting'
        
        # Detect temporal context
        if any(word in message_lower for word in ['today', 'now', 'current']):
            intent['temporal_context'] = 'today'
        elif any(word in message_lower for word in ['tomorrow', 'next']):
            intent['temporal_context'] = 'future'
        elif any(word in message_lower for word in ['yesterday', 'past', 'previous']):
            intent['temporal_context'] = 'past'
        elif any(word in message_lower for word in deadline_keywords):
            intent['temporal_context'] = 'deadline'
        
        return intent
    
    def _retrieve_context(self, message: str, intent: Dict) -> Dict:
        """
        Intelligent context retrieval based on intent
        
        Args:
            message: User message
            intent: Intent classification
            
        Returns:
            Context data with documents and sources
        """
        try:
            # Generate query embedding
            query_embedding = self.llm_service.generate_embedding(message)
            
            # Adjust search parameters based on intent
            top_k = 5
            filter_metadata = {}
            
            if intent['entity_type']:
                filter_metadata['type'] = intent['entity_type']
                top_k = 10  # Get more results for specific entity queries
            
            # Perform semantic search
            search_results = self.vector_store.search(
                query_embedding,
                top_k=top_k,
                filter_metadata=filter_metadata if filter_metadata else None
            )
            
            # Also get recent data for temporal queries
            recent_data = []
            if intent['temporal_context'] in ['today', 'deadline']:
                recent_data = self._get_recent_data(intent['entity_type'])
            
            # Build context
            context_parts = []
            sources = []
            
            # Add search results
            for result in search_results:
                context_parts.append(result['document'])
                sources.append({
                    'type': result['metadata'].get('type'),
                    'title': result['metadata'].get('title'),
                    'id': result['metadata'].get('source_id')
                })
            
            # Add recent data
            for data in recent_data:
                context_parts.append(data['text'])
                sources.append(data['source'])
            
            context_text = "\n\n".join(context_parts) if context_parts else "No relevant information found."
            
            return {
                'text': context_text,
                'sources': sources,
                'search_results': search_results,
                'recent_data': recent_data
            }
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return {
                'text': "Unable to retrieve context.",
                'sources': [],
                'search_results': [],
                'recent_data': []
            }
    
    def _get_recent_data(self, entity_type: Optional[str] = None) -> List[Dict]:
        """
        Get recent data from database for temporal queries
        
        Args:
            entity_type: Optional entity type filter
            
        Returns:
            List of recent data items
        """
        recent_data = []
        
        try:
            if entity_type == 'task' or entity_type is None:
                # Get recent and upcoming tasks
                query = """
                SELECT id, title, description, status, priority, deadline
                FROM tasks
                WHERE user_id = %s AND status != 'completed'
                ORDER BY deadline ASC NULLS LAST
                LIMIT 10
                """
                tasks = rds_db.execute_query(query, (self.user_id,), fetch_all=True)
                
                for task in tasks or []:
                    text = f"Task: {task['title']} (Status: {task['status']}, Priority: {task['priority']})"
                    if task['deadline']:
                        text += f" - Due: {task['deadline']}"
                    if task['description']:
                        text += f"\nDescription: {task['description']}"
                    
                    recent_data.append({
                        'text': text,
                        'source': {
                            'type': 'task',
                            'title': task['title'],
                            'id': task['id']
                        }
                    })
            
            if entity_type == 'meeting' or entity_type is None:
                # Get recent meetings
                query = """
                SELECT id, title, summary, status, created_at
                FROM meetings
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 5
                """
                meetings = rds_db.execute_query(query, (self.user_id,), fetch_all=True)
                
                for meeting in meetings or []:
                    text = f"Meeting: {meeting['title']} (Status: {meeting['status']})"
                    if meeting['summary']:
                        text += f"\nSummary: {meeting['summary']}"
                    
                    recent_data.append({
                        'text': text,
                        'source': {
                            'type': 'meeting',
                            'title': meeting['title'],
                            'id': meeting['id']
                        }
                    })
        
        except Exception as e:
            logger.error(f"Error getting recent data: {e}")
        
        return recent_data
    
    def _execute_action(self, intent: Dict, message: str, context_data: Dict) -> Optional[Dict]:
        """
        Execute action based on intent
        
        Args:
            intent: Intent classification
            message: User message
            context_data: Retrieved context
            
        Returns:
            Action result or None
        """
        try:
            if not intent['requires_action']:
                return None
            
            logger.info(f"Executing action: {intent['action_type']} on {intent['entity_type']}")
            
            # Use LLM to extract action parameters
            action_params = self._extract_action_parameters(message, intent, context_data)
            
            # Execute action
            result = self.action_executor.execute(
                action_type=intent['action_type'],
                entity_type=intent['entity_type'],
                parameters=action_params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_action_parameters(self, message: str, intent: Dict, context_data: Dict) -> Dict:
        """
        Use LLM to extract structured parameters from user message
        
        Args:
            message: User message
            intent: Intent classification
            context_data: Retrieved context
            
        Returns:
            Extracted parameters
        """
        extraction_prompt = f"""Extract structured parameters from the user's message for a {intent['action_type']} action on a {intent['entity_type']}.

User message: "{message}"

Return a JSON object with the following fields (use null for missing values):
- title: string
- description: string
- priority: "low" | "medium" | "high"
- status: string
- deadline: ISO date string
- assigned_to: string

Only return the JSON object, nothing else."""

        try:
            response = self.llm_service.generate(
                extraction_prompt, 
                system_prompt="You are a parameter extraction assistant. Only return valid JSON.",
                use_cache=False  # Don't cache parameter extraction
            )
            
            # Clean response - remove markdown code blocks if present
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            # Parse JSON response
            params = json.loads(response)
            logger.info(f"Extracted parameters: {params}")
            return params
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}, Response was: {response}")
            # Return basic parameters
            return {
                'title': message[:100],
                'description': message
            }
        except Exception as e:
            logger.error(f"Error extracting parameters: {e}")
            # Return basic parameters
            return {
                'title': message[:100],
                'description': message
            }
    
    def _build_enhanced_prompt(
        self,
        context_data: Dict,
        recent_messages: List[Dict],
        intent: Dict,
        action_result: Optional[Dict]
    ) -> str:
        """
        Build enhanced system prompt with rich context
        
        Args:
            context_data: Retrieved context
            recent_messages: Recent conversation
            intent: Intent classification
            action_result: Action execution result
            
        Returns:
            Enhanced system prompt
        """
        prompt = f"""You are an intelligent AI assistant for a meeting and task management application.

CAPABILITIES:
- Answer questions about tasks, meetings, and notifications
- Provide summaries and insights
- Help with planning and organization
- Execute actions when requested (create, update, delete)
- Understand context and follow-up questions

PERSONALITY:
- Professional yet friendly
- Concise and clear
- Proactive in offering help
- Honest about limitations

CURRENT CONTEXT:
{context_data['text']}

CONVERSATION GUIDELINES:
1. Use information from the context above
2. Reference specific data when answering
3. If information is missing, say so clearly
4. Don't make assumptions or speculate
5. For follow-up questions, use conversation history
6. Suggest next steps when appropriate
"""
        
        # Add conversation history
        if recent_messages:
            history_text = "\n".join([
                f"{msg['role'].capitalize()}: {msg['content']}"
                for msg in recent_messages[:-1]
            ])
            prompt += f"\n\nRECENT CONVERSATION:\n{history_text}"
        
        # Add action result
        if action_result:
            if action_result.get('success'):
                prompt += f"\n\nACTION EXECUTED: {intent['action_type']} {intent['entity_type']} - SUCCESS"
                prompt += f"\nResult: {json.dumps(action_result.get('data', {}))}"
                prompt += "\nInform the user about the successful action in a natural way."
            else:
                prompt += f"\n\nACTION FAILED: {action_result.get('error')}"
                prompt += "\nInform the user about the failure and suggest alternatives."
        
        # Add intent-specific guidance
        if intent['type'] == 'summary_query':
            prompt += "\n\nUSER WANTS: A summary or overview. Provide a concise, organized summary."
        elif intent['type'] == 'list_query':
            prompt += "\n\nUSER WANTS: A list of items. Present information in a clear, organized list format."
        elif intent['type'] == 'search_query':
            prompt += "\n\nUSER WANTS: To find specific information. Focus on the most relevant results."
        
        return prompt
    
    def _generate_response(
        self,
        message: str,
        system_prompt: str,
        session_id: str,
        sources: List[Dict],
        action_result: Optional[Dict]
    ) -> Dict:
        """Generate non-streaming response"""
        try:
            response = self.llm_service.generate(message, system_prompt)
            
            # Validate response
            if not response or not response.strip():
                response = "I understand your message, but I'm not sure how to respond. Could you please rephrase your question?"
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            response = "I'm sorry, I'm having trouble processing your request right now. Please try again."
        
        # Add assistant response to history
        metadata = {'sources': sources}
        if action_result:
            metadata['action_executed'] = action_result
        
        self.conversation_manager.add_message(
            session_id,
            'assistant',
            response,
            metadata
        )
        
        return {
            'response': response,
            'session_id': session_id,
            'sources': sources,
            'action_result': action_result
        }
    
    def _generate_streaming_response(
        self,
        message: str,
        system_prompt: str,
        session_id: str,
        sources: List[Dict],
        action_result: Optional[Dict]
    ) -> Dict:
        """Generate streaming response"""
        def response_generator():
            full_response = ""
            try:
                for chunk in self.llm_service.generate_streaming(message, system_prompt):
                    full_response += chunk
                    yield chunk
            except Exception as e:
                logger.error(f"Error in streaming generation: {e}")
                fallback_response = "I'm sorry, I'm having trouble processing your request right now. Please try again."
                full_response = fallback_response
                yield fallback_response
            
            # Save complete response after streaming
            metadata = {'sources': sources}
            if action_result:
                metadata['action_executed'] = action_result
            
            self.conversation_manager.add_message(
                session_id,
                'assistant',
                full_response,
                metadata
            )
        
        return {
            'stream': response_generator(),
            'session_id': session_id,
            'sources': sources,
            'action_result': action_result
        }
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> Dict:
        """
        Get conversation history
        
        Args:
            session_id: Session ID
            limit: Maximum messages to return
            
        Returns:
            Dict with messages and session_id
        """
        try:
            messages = self.conversation_manager.get_history(session_id, limit)
            return {
                'messages': messages,
                'session_id': session_id
            }
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            raise e
    
    def clear_conversation(self, session_id: Optional[str] = None):
        """
        Clear conversation history (keeps session, removes messages)
        
        Args:
            session_id: Optional session ID (if None, creates new session)
        """
        try:
            if session_id:
                self.conversation_manager.clear_session(session_id)
            return {'success': True}
        except Exception as e:
            logger.error(f"Error clearing conversation: {e}")
            raise e
    
    def delete_session(self, session_id: str):
        """
        Delete a conversation session completely
        
        Args:
            session_id: Session ID to delete
        """
        try:
            self.conversation_manager.delete_session(session_id)
            return {'success': True}
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            raise e
    
    def get_sessions(self, limit: int = 10) -> Dict:
        """
        Get user's conversation sessions
        
        Args:
            limit: Maximum sessions to return
            
        Returns:
            Dict with sessions list (empty list if error or no sessions)
        """
        try:
            sessions = self.conversation_manager.get_user_sessions(limit)
            return {'sessions': sessions}
        except Exception as e:
            logger.warning(f"Error getting sessions (returning empty list): {e}")
            # Return empty list instead of raising exception
            return {'sessions': []}
    
    def index_user_data(self):
        """Index all user data into vector store"""
        try:
            self.indexer.index_all_user_data()
            return {'success': True, 'message': 'User data indexed successfully'}
        except Exception as e:
            logger.error(f"Error indexing user data: {e}")
            raise e
    
    def get_smart_suggestions(self) -> Dict:
        """
        Get smart suggestions based on user's current context
        
        Returns:
            Dict with suggestions
        """
        try:
            suggestions = []
            
            # Get overdue tasks
            query = """
            SELECT COUNT(*) as count FROM tasks
            WHERE user_id = %s AND status != 'completed' 
            AND deadline < NOW()
            """
            result = rds_db.execute_query(query, (self.user_id,), fetch_all=True)
            overdue_count = result[0]['count'] if result else 0
            
            if overdue_count > 0:
                suggestions.append({
                    'type': 'overdue_tasks',
                    'message': f'You have {overdue_count} overdue task(s)',
                    'action': 'Show me my overdue tasks'
                })
            
            # Get upcoming deadlines
            query = """
            SELECT COUNT(*) as count FROM tasks
            WHERE user_id = %s AND status != 'completed'
            AND deadline BETWEEN NOW() AND NOW() + INTERVAL '3 days'
            """
            result = rds_db.execute_query(query, (self.user_id,), fetch_all=True)
            upcoming_count = result[0]['count'] if result else 0
            
            if upcoming_count > 0:
                suggestions.append({
                    'type': 'upcoming_deadlines',
                    'message': f'{upcoming_count} task(s) due in the next 3 days',
                    'action': 'Show me upcoming deadlines'
                })
            
            # Get pending tasks
            query = """
            SELECT COUNT(*) as count FROM tasks
            WHERE user_id = %s AND status = 'pending'
            """
            result = rds_db.execute_query(query, (self.user_id,), fetch_all=True)
            pending_count = result[0]['count'] if result else 0
            
            if pending_count > 5:
                suggestions.append({
                    'type': 'many_pending',
                    'message': f'You have {pending_count} pending tasks',
                    'action': 'Help me prioritize my tasks'
                })
            
            return {
                'success': True,
                'suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return {
                'success': False,
                'suggestions': []
            }
