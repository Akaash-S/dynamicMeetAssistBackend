#!/usr/bin/env python3
"""
Test script to verify Firebase UID handling
"""

import requests
import json

def test_firebase_uid():
    """Test with a real Firebase UID format"""
    
    # Real Firebase UID from your error log
    firebase_uid = "XNecbpHJPvfvYqQ99fDPdngUicU2"
    
    print("Testing Firebase UID Handling")
    print("=" * 40)
    print(f"Firebase UID: {firebase_uid}")
    print(f"UID Length: {len(firebase_uid)}")
    print(f"UID Format: {'Valid Firebase format' if len(firebase_uid) == 28 else 'Invalid format'}")
    
    base_url = 'http://localhost:5000/api/tasks'
    
    try:
        print(f"\nTesting API call with Firebase UID...")
        response = requests.get(base_url, params={'user_id': firebase_uid}, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response: {json.dumps(response_data, indent=2)}")
        except json.JSONDecodeError:
            print(f"Response (raw): {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] Connection Error: Is Flask server running on localhost:5000?")
    except Exception as e:
        print(f"[ERROR] Unexpected Error: {e}")

if __name__ == "__main__":
    test_firebase_uid()
