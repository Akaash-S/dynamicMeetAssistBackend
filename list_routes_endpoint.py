"""Add a debug endpoint to list all routes"""
import requests

try:
    response = requests.get('http://localhost:8000/api/health')
    print(f"Server is running: {response.status_code}")
    
    # Try to access admin login
    response = requests.post(
        'http://localhost:8000/api/admin/auth/login',
        json={'email': 'test', 'password': 'test'}
    )
    print(f"\nAdmin login endpoint: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")
