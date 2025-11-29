"""
Test Groq API Keys
==================
Simple script to verify Groq API keys are working
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_groq_api():
    """Test Groq API connection"""
    print("="*60)
    print("GROQ API KEY TEST")
    print("="*60)
    print()
    
    # Check if API keys are set
    api_key_1 = os.getenv('GROQ_API_KEY')
    api_key_2 = os.getenv('GROQ_API_KEY_TWO')
    
    print("1. Checking environment variables...")
    print(f"   GROQ_API_KEY: {'✅ Set' if api_key_1 else '❌ Not set'}")
    print(f"   GROQ_API_KEY_TWO: {'✅ Set' if api_key_2 else '❌ Not set'}")
    print()
    
    if not api_key_1 and not api_key_2:
        print("❌ ERROR: No Groq API keys found!")
        print("   Please set GROQ_API_KEY or GROQ_API_KEY_TWO in backend/.env")
        return False
    
    # Test primary key
    if api_key_1:
        print("2. Testing GROQ_API_KEY...")
        try:
            from groq import Groq
            client = Groq(api_key=api_key_1)
            
            # Test with a simple completion
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "user", "content": "Say 'Hello' in one word"}
                ],
                max_tokens=10
            )
            
            response = completion.choices[0].message.content
            print(f"   Response: {response}")
            print("   ✅ GROQ_API_KEY is working!")
            print()
            
        except Exception as e:
            print(f"   ❌ GROQ_API_KEY failed: {e}")
            print()
    
    # Test secondary key
    if api_key_2:
        print("3. Testing GROQ_API_KEY_TWO...")
        try:
            from groq import Groq
            client = Groq(api_key=api_key_2)
            
            # Test with a simple completion
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "user", "content": "Say 'Hello' in one word"}
                ],
                max_tokens=10
            )
            
            response = completion.choices[0].message.content
            print(f"   Response: {response}")
            print("   ✅ GROQ_API_KEY_TWO is working!")
            print()
            
        except Exception as e:
            print(f"   ❌ GROQ_API_KEY_TWO failed: {e}")
            print()
    
    # Test LLM Service
    print("4. Testing LLM Service...")
    try:
        sys.path.insert(0, '.')
        from chatbot.llm import get_llm_service
        
        llm_service = get_llm_service()
        print("   ✅ LLM Service initialized successfully")
        
        # Test generation
        response = llm_service.generate(
            "Say 'Hello' in one word",
            system_prompt="You are a helpful assistant."
        )
        print(f"   Response: {response}")
        print("   ✅ LLM Service is working!")
        print()
        
    except Exception as e:
        print(f"   ❌ LLM Service failed: {e}")
        print()
        return False
    
    print("="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    return True

if __name__ == "__main__":
    try:
        success = test_groq_api()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
