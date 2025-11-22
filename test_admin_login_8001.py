import requests

response = requests.post(
    'http://localhost:8001/api/admin/auth/login',
    json={'email': 'admin@example.com', 'password': 'admin123'}
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
