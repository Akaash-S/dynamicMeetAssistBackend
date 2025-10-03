#!/usr/bin/env python3
"""
Simple test script to verify health endpoint works
"""
import requests
import json

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        # Test health endpoint
        response = requests.get('http://localhost:5000/api/health')
        print(f"Health endpoint status: {response.status_code}")
        print(f"Health endpoint response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Health endpoint is working correctly")
        else:
            print("❌ Health endpoint returned error")
            
    except Exception as e:
        print(f"❌ Error testing health endpoint: {e}")

def test_notifications_endpoint():
    """Test the notifications endpoint with a test Firebase UID"""
    try:
        # Test with a dummy Firebase UID
        test_uid = "test_firebase_uid_123"
        response = requests.get(f'http://localhost:5000/api/auth/user/{test_uid}/notifications')
        print(f"Notifications endpoint status: {response.status_code}")
        print(f"Notifications endpoint response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Notifications endpoint is working correctly")
        else:
            print("❌ Notifications endpoint returned error")
            
    except Exception as e:
        print(f"❌ Error testing notifications endpoint: {e}")

if __name__ == "__main__":
    print("🧪 Testing backend endpoints...")
    test_health_endpoint()
    print()
    test_notifications_endpoint()
