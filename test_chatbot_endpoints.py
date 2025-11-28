"""
Test Chatbot Endpoints
======================
Simple test script to verify chatbot endpoints are working
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test-user-123"

# Base headers (without Content-Type for GET requests)
base_headers = {
    "X-User-ID": TEST_USER_ID
}

# Headers for POST requests
post_headers = {
    "Content-Type": "application/json",
    "X-User-ID": TEST_USER_ID
}

def test_endpoint(name, method, endpoint, data=None):
    """Test an endpoint and print results"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    print(f"Method: {method}")
    print(f"URL: {BASE_URL}{endpoint}")
    
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", headers=base_headers)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", headers=post_headers, json=data)
        elif method == "DELETE":
            response = requests.delete(f"{BASE_URL}{endpoint}", headers=post_headers, json=data)
        
        print(f"Status: {response.status_code}")
        
        try:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
        except:
            print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ PASSED")
            return True
        else:
            print("❌ FAILED")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CHATBOT ENDPOINTS TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Health Check
    results.append(test_endpoint(
        "Health Check",
        "GET",
        "/api/health"
    ))
    
    # Test 2: Get Sessions
    results.append(test_endpoint(
        "Get Sessions",
        "GET",
        "/api/chatbot/sessions?limit=10"
    ))
    
    # Test 3: Get Suggestions
    results.append(test_endpoint(
        "Get Suggestions",
        "GET",
        "/api/chatbot/suggestions"
    ))
    
    # Test 4: Send Message
    results.append(test_endpoint(
        "Send Message",
        "POST",
        "/api/chatbot/message",
        data={"message": "Hello, this is a test message"}
    ))
    
    # Test 5: Index User Data
    results.append(test_endpoint(
        "Index User Data",
        "POST",
        "/api/chatbot/index"
    ))
    
    # Test 6: Voice Status
    results.append(test_endpoint(
        "Voice Status",
        "GET",
        "/api/chatbot/voice/status"
    ))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
