"""
Test Authentication Flow
Simulates the frontend authentication process to verify backend is working correctly
"""

import requests
import json
from datetime import datetime

# Backend URL
BASE_URL = "http://localhost:8000"

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_health():
    """Test if backend is running"""
    print_header("1. Testing Backend Health")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("   Please start the backend server:")
        print("   cd backend && python app.py")
        return False

def test_user_verification():
    """Test user verification endpoint"""
    print_header("2. Testing User Verification")
    
    # Simulate a Google Sign-In user
    test_user = {
        "firebase_uid": "test_firebase_uid_123",
        "email": "test@example.com",
        "name": "Test User",
        "auth_provider": "google_oauth",
        "google_calendar_enabled": True
    }
    
    try:
        print(f"📤 Sending verification request for: {test_user['email']}")
        response = requests.post(
            f"{BASE_URL}/api/auth/verify",
            json=test_user,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ User verification successful")
            print(f"   User ID: {data['user']['id']}")
            print(f"   Email: {data['user']['email']}")
            print(f"   Is New User: {data.get('is_new_user', False)}")
            return data['user']
        else:
            print(f"❌ Verification failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_get_user(user_id):
    """Test getting user data"""
    print_header("3. Testing Get User")
    
    try:
        print(f"📤 Fetching user data for ID: {user_id}")
        response = requests.get(
            f"{BASE_URL}/api/auth/user/{user_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ User data retrieved successfully")
            print(f"   Email: {data['user']['email']}")
            print(f"   Name: {data['user']['name']}")
            print(f"   Source: {data.get('source', 'unknown')}")
            return True
        else:
            print(f"❌ Failed to get user: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_get_meetings(user_id):
    """Test getting meetings for user"""
    print_header("4. Testing Get Meetings")
    
    try:
        print(f"📤 Fetching meetings for user: {user_id}")
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"user_id": user_id},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            meeting_count = len(data.get('meetings', []))
            print(f"✅ Meetings retrieved successfully")
            print(f"   Count: {meeting_count} meetings")
            if meeting_count == 0:
                print("   (This is normal for a new user)")
            return True
        else:
            print(f"❌ Failed to get meetings: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_get_tasks(user_id):
    """Test getting tasks for user"""
    print_header("5. Testing Get Tasks")
    
    try:
        print(f"📤 Fetching tasks for user: {user_id}")
        response = requests.get(
            f"{BASE_URL}/api/tasks",
            params={"user_id": user_id},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            task_count = len(data.get('tasks', []))
            print(f"✅ Tasks retrieved successfully")
            print(f"   Count: {task_count} tasks")
            if task_count == 0:
                print("   (This is normal for a new user)")
            return True
        else:
            print(f"❌ Failed to get tasks: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    print("\n🔍 AUTHENTICATION FLOW TEST")
    print("="*60)
    print("This test simulates the frontend authentication process")
    print("="*60)
    
    results = {
        "health": False,
        "verification": False,
        "get_user": False,
        "get_meetings": False,
        "get_tasks": False
    }
    
    # Test 1: Backend health
    results["health"] = test_health()
    if not results["health"]:
        print("\n❌ Backend is not running. Please start it first.")
        return
    
    # Test 2: User verification
    user = test_user_verification()
    if user:
        results["verification"] = True
        user_id = user['id']
        
        # Test 3: Get user
        results["get_user"] = test_get_user(user_id)
        
        # Test 4: Get meetings
        results["get_meetings"] = test_get_meetings(user_id)
        
        # Test 5: Get tasks
        results["get_tasks"] = test_get_tasks(user_id)
    
    # Summary
    print_header("TEST SUMMARY")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    print(f"\nResults: {passed_tests}/{total_tests} tests passed\n")
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {test_name.replace('_', ' ').title()}")
    
    print("\n" + "="*60)
    
    if passed_tests == total_tests:
        print("✅ ALL TESTS PASSED!")
        print("\nThe authentication flow is working correctly.")
        print("You can now test with the frontend application.")
    else:
        print("⚠️ SOME TESTS FAILED")
        print("\nPlease check:")
        print("1. Backend server is running (python backend/app.py)")
        print("2. Database connection is working")
        print("3. Check backend logs for errors")
        print("\nFor detailed troubleshooting, see:")
        print("  - GOOGLE_AUTH_FIX_GUIDE.md")
        print("  - Run: python backend/diagnose_auth_issue.py")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
