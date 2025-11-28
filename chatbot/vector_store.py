"""
Vector Store using ChromaDB
============================
Manages embeddings and semantic search for user data
"""

import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector store for semantic search using ChromaDB"""
    
    def __init__(self, user_id: str):
        """
        Initialize vector store for a specific user
        
        Args:
            user_id: User ID for data isolation
        """
        self.user_id = user_id
        
        # Initialize ChromaDB client
        vector_store_path = os.getenv('VECTOR_STORE_PATH', './data/vectors')
        os.makedirs(vector_store_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=vector_store_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create or get user-specific collection
        collection_name = f"user_{user_id.replace('-', '_')}"
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"user_id": user_id}
        )
        
        logger.info(f"Vector store initialized for user {user_id}")
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict],
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None
    ):
        """
        Add documents with embeddings to vector store
        
        Args:
            documents: List of document texts
            metadatas: List of metadata dicts
            embeddings: List of embedding vectors
            ids: Optional list of document IDs
        """
        try:
            if not ids:
                ids = [f"{self.user_id}_{i}" for i in range(len(documents))]
            
            # Add user_id to all metadata
            for metadata in metadatas:
                metadata['user_id'] = self.user_id
            
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise e
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Semantic search for relevant documents
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            List of search results with documents and metadata
        """
        try:
            # Always filter by user_id
            where_filter = {"user_id": self.user_id}
            if filter_metadata:
                where_filter.update(filter_metadata)
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'document': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else None,
                        'id': results['ids'][0][i] if results['ids'] else None
                    })
            
            logger.info(f"Search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise e
    
    def update_document(
        self,
        doc_id: str,
        document: str,
        metadata: Dict,
        embedding: List[float]
    ):
        """
        Update existing document
        
        Args:
            doc_id: Document ID
            document: Updated document text
            metadata: Updated metadata
            embedding: Updated embedding
        """
        try:
            metadata['user_id'] = self.user_id
            
            self.collection.update(
                ids=[doc_id],
                documents=[document],
                metadatas=[metadata],
                embeddings=[embedding]
            )
            
            logger.info(f"Updated document {doc_id}")
            
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise e
    
    def delete_document(self, doc_id: str):
        """
        Delete document from vector store
        
        Args:
            doc_id: Document ID to delete
        """
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document {doc_id}")
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise e
    
    def get_document_count(self) -> int:
        """Get total number of documents in collection"""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            return 0
    
    def clear_all(self):
        """Clear all documents from user's collection"""
        try:
            # Delete the collection and recreate it
            collection_name = self.collection.name
            self.client.delete_collection(name=collection_name)
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"user_id": self.user_id}
            )
            logger.info(f"Cleared all documents for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error clearing documents: {e}")
            raise e
