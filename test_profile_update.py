#!/usr/bin/env python3
"""
Test script to verify profile update functionality
"""

import requests
import json

def test_profile_update():
    base_url = "http://localhost:5000"
    
    # Test data
    test_firebase_uid = "test_user_123"
    
    print("[TEST] Testing Profile Update Flow...")
    
    # Step 1: Create a test user
    print("\n1. Creating test user...")
    create_response = requests.post(f"{base_url}/api/auth/verify", json={
        "firebase_uid": test_firebase_uid,
        "email": "test@example.com",
        "name": "Original Name"
    })
    
    print(f"   Status: {create_response.status_code}")
    if create_response.status_code == 200:
        user_data = create_response.json()
        print(f"   Created user: {user_data['user']['name']}")
    else:
        print(f"   Error: {create_response.text}")
        return
    
    # Step 2: Update the user's name
    print("\n2. Updating user name...")
    update_response = requests.put(f"{base_url}/api/auth/user/{test_firebase_uid}", json={
        "name": "Updated Name"
    })
    
    print(f"   Status: {update_response.status_code}")
    if update_response.status_code == 200:
        updated_data = update_response.json()
        print(f"   Updated user: {updated_data['user']['name']}")
    else:
        print(f"   Error: {update_response.text}")
        return
    
    # Step 3: Verify the update by fetching user data
    print("\n3. Verifying update...")
    get_response = requests.get(f"{base_url}/api/auth/user/{test_firebase_uid}")
    
    print(f"   Status: {get_response.status_code}")
    if get_response.status_code == 200:
        fetched_data = get_response.json()
        print(f"   Fetched user: {fetched_data['user']['name']}")
        
        if fetched_data['user']['name'] == "Updated Name":
            print("   [SUCCESS] Profile update successful!")
        else:
            print("   [FAILED] Profile update failed - name not updated")
    else:
        print(f"   Error: {get_response.text}")
    
    # Step 4: Clean up - delete test user
    print("\n4. Cleaning up...")
    delete_response = requests.delete(f"{base_url}/api/auth/user/{test_firebase_uid}", json={
        "confirmation": "DELETE_MY_ACCOUNT"
    })
    
    print(f"   Cleanup status: {delete_response.status_code}")
    
    print("\n[DONE] Test completed!")

if __name__ == "__main__":
    test_profile_update()
