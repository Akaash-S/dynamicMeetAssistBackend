#!/usr/bin/env python3
"""
Test script for OAuth login flow
Tests both new user registration and existing user login scenarios
"""

import requests
import json
import uuid
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if your backend runs on different port
TEST_EMAIL = "test.oauth@example.com"
TEST_NAME = "OAuth Test User"

def test_oauth_flow():
    """Test the complete OAuth flow"""
    print("🧪 Testing OAuth Login Flow")
    print("=" * 50)
    
    # Test data
    firebase_uid = f"firebase_test_{uuid.uuid4().hex[:8]}"
    google_oauth_id = f"google_test_{uuid.uuid4().hex[:8]}"
    
    test_user_data = {
        "firebase_uid": firebase_uid,
        "google_oauth_id": google_oauth_id,
        "email": TEST_EMAIL,
        "name": TEST_NAME,
        "auth_provider": "google_oauth",
        "google_calendar_enabled": True
    }
    
    print(f"📧 Test Email: {TEST_EMAIL}")
    print(f"🔑 Firebase UID: {firebase_uid}")
    print(f"🔑 Google OAuth ID: {google_oauth_id}")
    print()
    
    # Test 1: New User Registration
    print("🔄 Test 1: New User Registration")
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/verify",
            json=test_user_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 201 and result.get('success'):
            print("✅ New user registration: SUCCESS")
            user_id = result['user']['id']
        else:
            print("❌ New user registration: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ New user registration error: {e}")
        return False
    
    print()
    
    # Test 2: Existing User Login (same data)
    print("🔄 Test 2: Existing User Login")
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/verify",
            json=test_user_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200 and result.get('success') and not result.get('is_new_user'):
            print("✅ Existing user login: SUCCESS")
        else:
            print("❌ Existing user login: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Existing user login error: {e}")
        return False
    
    print()
    
    # Test 3: User Lookup by Firebase UID
    print("🔄 Test 3: User Lookup by Firebase UID")
    try:
        response = requests.get(
            f"{BASE_URL}/api/auth/user/{firebase_uid}",
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200 and result.get('success'):
            print("✅ User lookup by Firebase UID: SUCCESS")
        else:
            print("❌ User lookup by Firebase UID: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ User lookup error: {e}")
        return False
    
    print()
    
    # Test 4: User Lookup by Email
    print("🔄 Test 4: User Lookup by Email")
    try:
        response = requests.get(
            f"{BASE_URL}/api/auth/user/{TEST_EMAIL}",
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200 and result.get('success'):
            print("✅ User lookup by Email: SUCCESS")
        else:
            print("❌ User lookup by Email: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ User lookup by email error: {e}")
        return False
    
    print()
    
    # Test 5: Google OAuth Endpoint
    print("🔄 Test 5: Google OAuth Endpoint")
    oauth_data = {
        "access_token": "test_access_token",
        "email": TEST_EMAIL,
        "name": TEST_NAME,
        "google_oauth_id": google_oauth_id,
        "google_calendar_enabled": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/google-oauth",
            json=oauth_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200 and result.get('success'):
            print("✅ Google OAuth endpoint: SUCCESS")
        else:
            print("❌ Google OAuth endpoint: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Google OAuth endpoint error: {e}")
        return False
    
    print()
    print("🎉 All OAuth tests passed!")
    return True

def cleanup_test_user():
    """Clean up test user (optional)"""
    print("🧹 Cleaning up test user...")
    # Note: You might want to add a cleanup endpoint or manually remove test data
    pass

if __name__ == "__main__":
    try:
        success = test_oauth_flow()
        if success:
            print("\n✅ OAuth flow test completed successfully!")
        else:
            print("\n❌ OAuth flow test failed!")
            exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        exit(1)