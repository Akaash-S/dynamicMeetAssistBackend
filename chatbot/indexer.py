"""
Data Indexer
============
Indexes user data into vector store for semantic search
"""

from typing import List, Dict
from .vector_store import VectorStore
from .llm import get_llm_service
from config.aws_rds_database import rds_db
import logging

logger = logging.getLogger(__name__)


class DataIndexer:
    """Indexes user data into vector store"""
    
    def __init__(self, user_id: str):
        """
        Initialize data indexer
        
        Args:
            user_id: User ID
        """
        self.user_id = user_id
        self.vector_store = VectorStore(user_id)
        self.llm_service = get_llm_service()
    
    def index_all_user_data(self):
        """Index all user data (tasks, meetings, notifications)"""
        try:
            logger.info(f"Starting full indexing for user {self.user_id}")
            
            # Clear existing data
            self.vector_store.clear_all()
            
            # Index each data type
            self.index_tasks()
            self.index_meetings()
            self.index_notifications()
            
            doc_count = self.vector_store.get_document_count()
            logger.info(f"Indexing complete. Total documents: {doc_count}")
            
        except Exception as e:
            logger.error(f"Error indexing all data: {e}")
            raise e
    
    def index_tasks(self):
        """Index user tasks"""
        try:
            query = """
            SELECT id, title, description, status, priority, deadline, assigned_to, created_at
            FROM tasks
            WHERE user_id = %s
            ORDER BY created_at DESC
            """
            
            tasks = rds_db.execute_query(query, (self.user_id,), fetch_all=True)
            
            if not tasks:
                logger.info("No tasks to index")
                return
            
            documents = []
            metadatas = []
            ids = []
            
            for task in tasks:
                # Build document text
                doc_text = f"Task: {task['title']}"
                if task['description']:
                    doc_text += f"\nDescription: {task['description']}"
                doc_text += f"\nStatus: {task['status']}"
                doc_text += f"\nPriority: {task['priority']}"
                if task['deadline']:
                    doc_text += f"\nDeadline: {task['deadline']}"
                if task['assigned_to']:
                    doc_text += f"\nAssigned to: {task['assigned_to']}"
                
                documents.append(doc_text)
                metadatas.append({
                    'type': 'task',
                    'source_id': task['id'],
                    'title': task['title'],
                    'status': task['status'],
                    'priority': task['priority'],
                    'created_at': task['created_at'].isoformat() if task['created_at'] else None
                })
                ids.append(f"task_{task['id']}")
            
            # Generate embeddings
            embeddings = self.llm_service.generate_embeddings_batch(documents)
            
            # Add to vector store
            self.vector_store.add_documents(documents, metadatas, embeddings, ids)
            
            logger.info(f"Indexed {len(documents)} tasks")
            
        except Exception as e:
            logger.error(f"Error indexing tasks: {e}")
            raise e
    
    def index_meetings(self):
        """Index user meetings with full transcripts and extracted content"""
        try:
            # Get meetings with all relevant data
            meetings_query = """
            SELECT id, title, transcript, summary, status, duration, created_at, updated_at
            FROM meetings
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 100
            """
            
            meetings = rds_db.execute_query(meetings_query, (self.user_id,), fetch_all=True)
            
            if not meetings:
                logger.info("No meetings to index")
                return
            
            documents = []
            metadatas = []
            ids = []
            
            for meeting in meetings:
                # Get timeline entries (extracted content) for this meeting
                timeline_query = """
                SELECT timestamp_minutes, event_type, title, content, participants
                FROM timeline
                WHERE meeting_id = %s
                ORDER BY timestamp_minutes ASC
                """
                timeline_entries = rds_db.execute_query(timeline_query, (meeting['id'],), fetch_all=True)
                
                # Get tasks extracted from this meeting
                tasks_query = """
                SELECT title, description, status, priority, deadline, assigned_to
                FROM tasks
                WHERE meeting_id = %s
                ORDER BY created_at ASC
                """
                meeting_tasks = rds_db.execute_query(tasks_query, (meeting['id'],), fetch_all=True)
                
                # Build comprehensive document text with ALL meeting content
                doc_text = f"Meeting: {meeting['title']}"
                
                if meeting.get('created_at'):
                    doc_text += f"\nDate: {meeting['created_at']}"
                
                if meeting.get('duration'):
                    doc_text += f"\nDuration: {meeting['duration']} minutes"
                
                # Add full summary
                if meeting.get('summary'):
                    summary = meeting['summary']
                    # Parse JSON summary if needed
                    try:
                        import json
                        if isinstance(summary, str):
                            summary_obj = json.loads(summary)
                            if isinstance(summary_obj, dict):
                                doc_text += f"\n\nSummary:"
                                for key, value in summary_obj.items():
                                    doc_text += f"\n{key}: {value}"
                            else:
                                doc_text += f"\n\nSummary: {summary}"
                        else:
                            doc_text += f"\n\nSummary: {summary}"
                    except (json.JSONDecodeError, TypeError):
                        doc_text += f"\n\nSummary: {summary}"
                
                # Add extracted timeline content (key moments, decisions, action items)
                if timeline_entries:
                    doc_text += f"\n\nExtracted Content ({len(timeline_entries)} items):"
                    for entry in timeline_entries:
                        minutes = int(entry['timestamp_minutes']) if entry['timestamp_minutes'] else 0
                        seconds = int((entry['timestamp_minutes'] - minutes) * 60) if entry['timestamp_minutes'] else 0
                        timestamp = f"{minutes:02d}:{seconds:02d}"
                        
                        doc_text += f"\n[{timestamp}] {entry['event_type']}: {entry['title']}"
                        if entry.get('content'):
                            doc_text += f" - {entry['content']}"
                        if entry.get('participants'):
                            participants = ', '.join(entry['participants']) if isinstance(entry['participants'], list) else str(entry['participants'])
                            doc_text += f" (Participants: {participants})"
                
                # Add extracted tasks
                if meeting_tasks:
                    doc_text += f"\n\nExtracted Tasks ({len(meeting_tasks)} items):"
                    for task in meeting_tasks:
                        doc_text += f"\n- {task['title']}"
                        if task.get('description'):
                            doc_text += f": {task['description']}"
                        doc_text += f" [Status: {task['status']}, Priority: {task['priority']}]"
                        if task.get('assigned_to'):
                            doc_text += f" (Assigned to: {task['assigned_to']})"
                        if task.get('deadline'):
                            doc_text += f" (Deadline: {task['deadline']})"
                
                # Add FULL transcript (not truncated) for complete context
                if meeting.get('transcript'):
                    transcript = meeting['transcript']
                    # Include full transcript for comprehensive search
                    # Split into chunks if too large (>10000 chars)
                    if len(transcript) > 10000:
                        doc_text += f"\n\nFull Transcript (Part 1 of 2):\n{transcript[:10000]}"
                        # Create a second document for the rest
                        doc_text_part2 = f"Meeting: {meeting['title']} (Transcript Continuation)"
                        doc_text_part2 += f"\n\nFull Transcript (Part 2 of 2):\n{transcript[10000:]}"
                        
                        documents.append(doc_text_part2)
                        metadatas.append({
                            'type': 'meeting_transcript',
                            'source_id': meeting['id'],
                            'title': f"{meeting['title']} (Transcript Part 2)",
                            'status': meeting['status'],
                            'created_at': meeting['created_at'].isoformat() if meeting['created_at'] else None
                        })
                        ids.append(f"meeting_{meeting['id']}_transcript_2")
                    else:
                        doc_text += f"\n\nFull Transcript:\n{transcript}"
                
                doc_text += f"\n\nStatus: {meeting['status']}"
                
                documents.append(doc_text)
                metadatas.append({
                    'type': 'meeting',
                    'source_id': meeting['id'],
                    'title': meeting['title'],
                    'status': meeting['status'],
                    'timeline_count': len(timeline_entries) if timeline_entries else 0,
                    'task_count': len(meeting_tasks) if meeting_tasks else 0,
                    'created_at': meeting['created_at'].isoformat() if meeting['created_at'] else None
                })
                ids.append(f"meeting_{meeting['id']}")
            
            # Generate embeddings
            embeddings = self.llm_service.generate_embeddings_batch(documents)
            
            # Add to vector store
            self.vector_store.add_documents(documents, metadatas, embeddings, ids)
            
            logger.info(f"Indexed {len(documents)} meeting documents (including {len([m for m in metadatas if m['type'] == 'meeting_transcript'])} transcript continuations)")
            
        except Exception as e:
            logger.error(f"Error indexing meetings: {e}")
            raise e
    
    def index_notifications(self):
        """Index user notifications"""
        try:
            query = """
            SELECT id, title, message, type, created_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 50
            """
            
            notifications = rds_db.execute_query(query, (self.user_id,), fetch_all=True)
            
            if not notifications:
                logger.info("No notifications to index")
                return
            
            documents = []
            metadatas = []
            ids = []
            
            for notif in notifications:
                # Build document text
                doc_text = f"Notification: {notif['title']}\n{notif['message']}"
                
                documents.append(doc_text)
                metadatas.append({
                    'type': 'notification',
                    'source_id': notif['id'],
                    'title': notif['title'],
                    'notification_type': notif['type'],
                    'created_at': notif['created_at'].isoformat() if notif['created_at'] else None
                })
                ids.append(f"notification_{notif['id']}")
            
            # Generate embeddings
            embeddings = self.llm_service.generate_embeddings_batch(documents)
            
            # Add to vector store
            self.vector_store.add_documents(documents, metadatas, embeddings, ids)
            
            logger.info(f"Indexed {len(documents)} notifications")
            
        except Exception as e:
            logger.error(f"Error indexing notifications: {e}")
            raise e
    
    def update_task_index(self, task_id: str):
        """
        Update index for a specific task
        
        Args:
            task_id: Task ID
        """
        try:
            query = """
            SELECT id, title, description, status, priority, deadline, assigned_to, created_at
            FROM tasks
            WHERE id = %s AND user_id = %s
            """
            
            result = rds_db.execute_query(query, (task_id, self.user_id), fetch_all=True)
            
            if not result:
                # Task deleted or doesn't exist, remove from index
                self.vector_store.delete_document(f"task_{task_id}")
                return
            
            task = result[0]
            
            # Build document
            doc_text = f"Task: {task['title']}"
            if task['description']:
                doc_text += f"\nDescription: {task['description']}"
            doc_text += f"\nStatus: {task['status']}"
            doc_text += f"\nPriority: {task['priority']}"
            if task['deadline']:
                doc_text += f"\nDeadline: {task['deadline']}"
            if task['assigned_to']:
                doc_text += f"\nAssigned to: {task['assigned_to']}"
            
            metadata = {
                'type': 'task',
                'source_id': task['id'],
                'title': task['title'],
                'status': task['status'],
                'priority': task['priority'],
                'created_at': task['created_at'].isoformat() if task['created_at'] else None
            }
            
            # Generate embedding
            embedding = self.llm_service.generate_embedding(doc_text)
            
            # Update in vector store
            self.vector_store.update_document(
                f"task_{task_id}",
                doc_text,
                metadata,
                embedding
            )
            
            logger.info(f"Updated task index for {task_id}")
            
        except Exception as e:
            logger.error(f"Error updating task index: {e}")
            raise e
