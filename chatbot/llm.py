"""
LLM Service using Groq API
===========================
Handles text generation and embeddings using Groq's llama-3.3-70b-versatile
"""

import os
import warnings
from typing import Generator, List, Optional
from groq import Groq
import logging

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')
warnings.filterwarnings('ignore', category=FutureWarning, module='tensorflow')

# Use simple embeddings to avoid TensorFlow conflicts
try:
    from .simple_embeddings import SimpleEmbeddings
    SIMPLE_EMBEDDINGS_AVAILABLE = True
except ImportError:
    SIMPLE_EMBEDDINGS_AVAILABLE = False

logger = logging.getLogger(__name__)


class LLMService:
    """Enhanced service for LLM operations using Groq API with caching and optimization"""
    
    def __init__(self):
        """Initialize Groq client and embedding model"""
        # Try primary API key first, then fallback to secondary
        api_key = os.getenv('GROQ_API_KEY') or os.getenv('GROQ_API_KEY_TWO')
        if not api_key:
            raise ValueError("GROQ_API_KEY or GROQ_API_KEY_TWO environment variable is required")
        
        try:
            self.client = Groq(api_key=api_key)
            logger.info(f"Groq client initialized successfully with model: {os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')}")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise ValueError(f"Failed to initialize Groq client: {e}")
        
        self.model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
        self.temperature = float(os.getenv('GROQ_TEMPERATURE', '0.7'))  # Lower for more consistent responses
        self.max_tokens = int(os.getenv('GROQ_MAX_TOKENS', '2048'))  # Increased for better responses
        
        # Response cache for identical queries (simple in-memory cache)
        self._response_cache = {}
        self._cache_max_size = 100
        
        # Initialize simple embedding model
        self.embedding_model = None
        if SIMPLE_EMBEDDINGS_AVAILABLE:
            try:
                logger.info("Loading simple embeddings model")
                self.embedding_model = SimpleEmbeddings()
                logger.info("LLM Service initialized successfully with simple embeddings")
            except Exception as e:
                logger.warning(f"Failed to load simple embeddings: {e}")
                logger.warning("Continuing without embeddings")
                self.embedding_model = None
        else:
            logger.warning("Simple embeddings not available. Continuing without embeddings")
    
    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True
    ) -> str:
        """
        Generate text using Groq LLM with optional caching
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            use_cache: Whether to use response cache
            
        Returns:
            Generated text
        """
        try:
            # Check cache for identical queries
            cache_key = None
            if use_cache:
                cache_key = f"{prompt}:{system_prompt}"
                if cache_key in self._response_cache:
                    logger.info("Returning cached response")
                    return self._response_cache[cache_key]
            
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            logger.debug(f"Generating response with model: {self.model}, temp: {temperature or self.temperature}")
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_completion_tokens=max_tokens or self.max_tokens,
                top_p=0.95,  # Slightly lower for more focused responses
                stream=False,
                stop=None
            )
            
            response = completion.choices[0].message.content
            
            if not response or not response.strip():
                logger.warning("Groq returned empty response")
                raise ValueError("Empty response from Groq API")
            
            logger.info(f"Generated response: {len(response)} characters")
            
            # Cache response
            if use_cache and cache_key:
                if len(self._response_cache) >= self._cache_max_size:
                    # Remove oldest entry
                    self._response_cache.pop(next(iter(self._response_cache)))
                self._response_cache[cache_key] = response
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating text with Groq: {e}", exc_info=True)
            # Provide more specific error message
            if "rate_limit" in str(e).lower():
                raise ValueError("Groq API rate limit exceeded. Please try again in a moment.")
            elif "api_key" in str(e).lower() or "authentication" in str(e).lower():
                raise ValueError("Groq API authentication failed. Please check your API key.")
            elif "model" in str(e).lower():
                raise ValueError(f"Groq model '{self.model}' not available. Please check model name.")
            else:
                raise ValueError(f"Groq API error: {str(e)}")
    
    def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Generator[str, None, None]:
        """
        Generate text with streaming using Groq LLM
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Yields:
            Text chunks as they are generated
        """
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_completion_tokens=max_tokens or self.max_tokens,
                top_p=1,
                stream=True,
                stop=None
            )
            
            for chunk in completion:
                content = chunk.choices[0].delta.content or ""
                if content:
                    yield content
                    
        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            raise e
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using sentence-transformers
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        if not self.embedding_model:
            # Fallback: return a simple hash-based embedding
            import hashlib
            hash_obj = hashlib.md5(text.encode())
            hash_hex = hash_obj.hexdigest()
            # Convert hex to list of floats (simple fallback)
            embedding = [float(int(hash_hex[i:i+2], 16)) / 255.0 for i in range(0, min(len(hash_hex), 32), 2)]
            # Pad to 384 dimensions to match all-MiniLM-L6-v2
            while len(embedding) < 384:
                embedding.extend(embedding[:min(384-len(embedding), len(embedding))])
            return embedding[:384]
        
        try:
            embedding = self.embedding_model.encode(text)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Fallback to hash-based embedding
            import hashlib
            hash_obj = hashlib.md5(text.encode())
            hash_hex = hash_obj.hexdigest()
            embedding = [float(int(hash_hex[i:i+2], 16)) / 255.0 for i in range(0, min(len(hash_hex), 32), 2)]
            while len(embedding) < 384:
                embedding.extend(embedding[:min(384-len(embedding), len(embedding))])
            return embedding[:384]
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.embedding_model:
            # Fallback: generate embeddings individually
            return [self.generate_embedding(text) for text in texts]
        
        try:
            embeddings = [self.embedding_model.encode(text) for text in texts]
            return embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            # Fallback: generate embeddings individually
            return [self.generate_embedding(text) for text in texts]


# Global instance
_llm_service = None


def get_llm_service() -> LLMService:
    """Get or create global LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
