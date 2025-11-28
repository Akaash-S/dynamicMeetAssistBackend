"""
Chatbot Test Script
===================
Quick test to verify chatbot functionality
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_llm_service():
    """Test LLM service"""
    print("\n" + "=" * 60)
    print("Testing LLM Service (Groq)")
    print("=" * 60)
    
    try:
        from chatbot.llm import get_llm_service
        
        llm = get_llm_service()
        print("✓ LLM service initialized")
        
        # Test generation
        print("\nTesting text generation...")
        response = llm.generate("Say hello in one sentence")
        print(f"✓ Response: {response}")
        
        # Test embedding
        print("\nTesting embedding generation...")
        embedding = llm.generate_embedding("test text")
        print(f"✓ Embedding generated: {len(embedding)} dimensions")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_vector_store():
    """Test vector store"""
    print("\n" + "=" * 60)
    print("Testing Vector Store (ChromaDB)")
    print("=" * 60)
    
    try:
        from chatbot.vector_store import VectorStore
        from chatbot.llm import get_llm_service
        
        import uuid
        test_user_id = str(uuid.uuid4())
        store = VectorStore(test_user_id)
        print("✓ Vector store initialized")
        
        # Test adding documents
        llm = get_llm_service()
        docs = ["Test document 1", "Test document 2"]
        embeddings = llm.generate_embeddings_batch(docs)
        metadatas = [
            {"type": "test", "title": "Doc 1"},
            {"type": "test", "title": "Doc 2"}
        ]
        
        store.add_documents(docs, metadatas, embeddings)
        print(f"✓ Added {len(docs)} documents")
        
        # Test search
        query_emb = llm.generate_embedding("test")
        results = store.search(query_emb, top_k=2)
        print(f"✓ Search returned {len(results)} results")
        
        # Cleanup
        store.clear_all()
        print("✓ Cleaned up test data")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_voice_service():
    """Test voice service"""
    print("\n" + "=" * 60)
    print("Testing Voice AI Service")
    print("=" * 60)
    
    try:
        from chatbot.voice import get_voice_service
        
        voice = get_voice_service()
        print("✓ Voice service initialized")
        
        if voice.tts_enabled:
            print("✓ Text-to-speech enabled (ElevenLabs)")
        else:
            print("⚠ Text-to-speech disabled (no ElevenLabs API key)")
        
        print(f"✓ Transcription model: {voice.transcription_model}")
        print(f"✓ Max audio size: {voice.max_audio_size / (1024*1024):.0f}MB")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_database():
    """Test database connection"""
    print("\n" + "=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    
    try:
        from config.aws_rds_database import rds_db
        
        # Test connection
        result = rds_db.execute_query("SELECT 1 as test")
        print("✓ Database connection successful")
        
        # Check chatbot tables
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('chatbot_sessions', 'chatbot_messages')
        """
        
        try:
            tables = rds_db.execute_query(tables_query, fetch_all=True)
            if tables and isinstance(tables, list):
                table_names = [row['table_name'] for row in tables]
            else:
                table_names = []
        except Exception as e:
            print(f"Error checking tables: {e}")
            table_names = []
        
        if 'chatbot_sessions' in table_names:
            print("✓ chatbot_sessions table exists")
        else:
            print("✗ chatbot_sessions table missing - run init_chatbot_db.py")
            return False
        
        if 'chatbot_messages' in table_names:
            print("✓ chatbot_messages table exists")
        else:
            print("✗ chatbot_messages table missing - run init_chatbot_db.py")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_full_flow():
    """Test complete chatbot flow"""
    print("\n" + "=" * 60)
    print("Testing Complete Chatbot Flow")
    print("=" * 60)
    
    try:
        from chatbot.service import ChatbotService
        from config.aws_rds_database import rds_db
        
        import uuid
        test_user_id = str(uuid.uuid4())
        
        # Create a test user first
        create_user_query = """
        INSERT INTO users (id, email, name, firebase_uid, auth_provider)
        VALUES (%s, %s, %s, %s, %s)
        """
        rds_db.execute_query(create_user_query, (
            test_user_id,
            'test@example.com',
            'Test User',
            f'firebase_test_{test_user_id}',
            'firebase'
        ))
        
        chatbot = ChatbotService(test_user_id)
        print("✓ Chatbot service initialized")
        
        # Test message processing
        print("\nSending test message...")
        result = chatbot.process_message(
            message="Hello, this is a test message",
            stream=False
        )
        
        print(f"✓ Response received: {result['response'][:100]}...")
        print(f"✓ Session ID: {result['session_id']}")
        print(f"✓ Sources: {len(result['sources'])} items")
        
        # Test history
        print("\nTesting conversation history...")
        history = chatbot.get_conversation_history(result['session_id'])
        print(f"✓ History retrieved: {len(history['messages'])} messages")
        
        # Cleanup
        chatbot.clear_conversation(result['session_id'])
        print("✓ Cleaned up test session")
        
        # Clean up test user
        delete_user_query = "DELETE FROM users WHERE id = %s"
        rds_db.execute_query(delete_user_query, (test_user_id,))
        print("✓ Cleaned up test user")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_environment():
    """Check environment variables"""
    print("\n" + "=" * 60)
    print("Checking Environment Variables")
    print("=" * 60)
    
    required_vars = {
        'GROQ_API_KEY': 'Groq API key for LLM',
        'RDS_HOST': 'Database connection string'
    }
    
    optional_vars = {
        'GROQ_API_KEY_TWO': 'Groq API key for voice (can use same as GROQ_API_KEY)',
        'ELEVENLABS_API_KEY': 'ElevenLabs API key for TTS (optional)',
        'VECTOR_STORE_PATH': 'Vector store path (defaults to ./data/vectors)',
        'EMBEDDING_MODEL': 'Embedding model (defaults to all-MiniLM-L6-v2)'
    }
    
    all_good = True
    
    print("\nRequired:")
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {desc}")
        else:
            print(f"✗ {var}: {desc} - MISSING!")
            all_good = False
    
    print("\nOptional:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {desc}")
        else:
            print(f"⚠ {var}: {desc} - Not set (using defaults)")
    
    return all_good


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("CHATBOT SYSTEM TEST")
    print("=" * 60)
    
    # Check environment
    if not check_environment():
        print("\n✗ Environment check failed. Please set required variables in .env")
        sys.exit(1)
    
    # Run tests
    tests = [
        ("Database", test_database),
        ("LLM Service", test_llm_service),
        ("Vector Store", test_vector_store),
        ("Voice Service", test_voice_service),
        ("Full Flow", test_full_flow)
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n✗ {name} test crashed: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! Chatbot is ready to use.")
        print("\nNext steps:")
        print("1. Start the server: python app.py")
        print("2. Test the API: curl http://localhost:5000/api/chatbot/message")
        print("3. Index your data: POST /api/chatbot/index")
    else:
        print("\n⚠ Some tests failed. Please fix the issues above.")
    
    print("\n" + "=" * 60 + "\n")
    
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
