"""
Simple Embeddings Service
==========================
Provides basic text embeddings without TensorFlow dependencies
"""

import hashlib
import re
from typing import List
import logging

logger = logging.getLogger(__name__)


class SimpleEmbeddings:
    """Simple embedding service using TF-IDF-like approach"""
    
    def __init__(self):
        """Initialize simple embeddings"""
        self.dimension = 384  # Match sentence-transformers dimension
        logger.info("Simple embeddings service initialized")
    
    def encode(self, text: str) -> List[float]:
        """
        Generate simple embedding for text
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        # Normalize text
        text = text.lower().strip()
        
        # Extract features
        features = []
        
        # 1. Character-level features (first 32 chars)
        char_features = []
        for i, char in enumerate(text[:32]):
            char_features.append(ord(char) / 255.0)
        
        # Pad to 32
        while len(char_features) < 32:
            char_features.append(0.0)
        
        features.extend(char_features)
        
        # 2. Word-level features
        words = re.findall(r'\w+', text)
        word_count = len(words)
        avg_word_length = sum(len(word) for word in words) / max(word_count, 1)
        
        features.extend([
            word_count / 100.0,  # Normalize word count
            avg_word_length / 20.0,  # Normalize avg word length
            len(text) / 1000.0,  # Normalize text length
        ])
        
        # 3. Hash-based features for semantic similarity
        hash_features = []
        for i in range(0, min(len(text), 100), 4):
            chunk = text[i:i+4]
            hash_val = hashlib.md5(chunk.encode()).hexdigest()
            hash_features.append(int(hash_val[:2], 16) / 255.0)
        
        # Pad hash features to 100
        while len(hash_features) < 100:
            hash_features.append(0.0)
        
        features.extend(hash_features[:100])
        
        # 4. Keyword-based features
        keywords = [
            'task', 'meeting', 'deadline', 'priority', 'status', 'complete',
            'pending', 'high', 'medium', 'low', 'urgent', 'today', 'tomorrow',
            'week', 'month', 'schedule', 'calendar', 'notification', 'reminder'
        ]
        
        keyword_features = []
        for keyword in keywords:
            keyword_features.append(1.0 if keyword in text else 0.0)
        
        features.extend(keyword_features)
        
        # 5. Statistical features
        vowels = sum(1 for char in text if char in 'aeiou')
        consonants = sum(1 for char in text if char.isalpha() and char not in 'aeiou')
        digits = sum(1 for char in text if char.isdigit())
        
        features.extend([
            vowels / max(len(text), 1),
            consonants / max(len(text), 1),
            digits / max(len(text), 1),
        ])
        
        # Pad or truncate to exact dimension
        if len(features) > self.dimension:
            features = features[:self.dimension]
        else:
            while len(features) < self.dimension:
                features.append(0.0)
        
        return features