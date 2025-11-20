"""
Test the verify endpoint fix
"""
import requests
import json

def test_verify_endpoint():
    """Test the /api/auth/verify endpoint"""
    print("=" * 60)
    print("TESTING /api/auth/verify ENDPOINT")
    print("=" * 60)
    print()
    
    url = "http://localhost:8000/api/auth/verify"
    
    # Test data matching the logs
    test_data = {
        'firebase_uid': 'J7fvTOk5c9Og0JMrWndY1RczaUE3',
        'email': 'projectsofakaashofficials321@gmail.com',
        'name': 'Akaash S',
        'auth_provider': 'google_oauth',
        'google_calendar_enabled': True
    }
    
    print(f"📤 Sending POST request to: {url}")
    print(f"📦 Data: {json.dumps(test_data, indent=2)}")
    print()
    
    try:
        response = requests.post(url, json=test_data, timeout=10)
        
        print(f"📥 Response Status: {response.status_code}")
        print(f"📥 Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            print("✅ SUCCESS! User verified/updated")
            print(f"📄 Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ ERROR! Status code: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ CONNECTION ERROR: {e}")
        print("   Make sure the backend server is running on port 8000")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        print(traceback.format_exc())
    
    print()
    print("=" * 60)

if __name__ == '__main__':
    test_verify_endpoint()
