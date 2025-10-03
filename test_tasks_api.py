#!/usr/bin/env python3
"""
Test script for the tasks API endpoint
"""

import requests
import json
from datetime import datetime

def test_tasks_api():
    """Test the /api/tasks endpoint"""
    
    # Test different scenarios
    test_cases = [
        {
            'name': 'Valid user_id',
            'params': {'user_id': 'test_user_123'},
            'expected_status': 200
        },
        {
            'name': 'Missing user_id',
            'params': {},
            'expected_status': 400
        },
        {
            'name': 'Empty user_id',
            'params': {'user_id': ''},
            'expected_status': 400
        },
        {
            'name': 'Non-existent user_id',
            'params': {'user_id': 'non_existent_user_999'},
            'expected_status': 200  # Should return empty list
        }
    ]
    
    base_url = 'http://localhost:5000/api/tasks'
    
    print("Testing Tasks API Endpoint")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test_case['name']}")
        print(f"   Params: {test_case['params']}")
        
        try:
            response = requests.get(base_url, params=test_case['params'], timeout=10)
            
            print(f"   Status Code: {response.status_code}")
            print(f"   Expected: {test_case['expected_status']}")
            
            if response.status_code == test_case['expected_status']:
                print("   [OK] Status code matches expected")
            else:
                print("   [ERROR] Status code mismatch")
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                print(f"   Response: {json.dumps(response_data, indent=2)}")
            except json.JSONDecodeError:
                print(f"   Response (raw): {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("   [ERROR] Connection Error: Is Flask server running on localhost:5000?")
        except requests.exceptions.Timeout:
            print("   [ERROR] Timeout Error: Request took too long")
        except Exception as e:
            print(f"   [ERROR] Unexpected Error: {e}")
        
        print("-" * 30)
    
    print("\nTest Summary:")
    print("If you see connection errors, start your Flask server with:")
    print("   python start.py")
    print("\nIf you see 500 errors, check the Flask terminal for detailed error logs.")

if __name__ == "__main__":
    test_tasks_api()
