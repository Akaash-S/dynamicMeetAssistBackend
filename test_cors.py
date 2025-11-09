#!/usr/bin/env python3
"""
Test script to verify CORS configuration for localhost
"""
import requests
import json

def test_cors_headers():
    """Test CORS headers for localhost origins"""
    
    # Test URLs
    base_url = "http://localhost:8000"
    test_origins = [
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080"
    ]
    
    print("🧪 Testing CORS Configuration for Localhost Origins")
    print("=" * 60)
    
    for origin in test_origins:
        try:
            # Test OPTIONS preflight request
            headers = {
                'Origin': origin,
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = requests.options(f"{base_url}/api/health", headers=headers, timeout=5)
            
            # Check CORS headers
            cors_origin = response.headers.get('Access-Control-Allow-Origin', 'NOT_SET')
            cors_methods = response.headers.get('Access-Control-Allow-Methods', 'NOT_SET')
            cors_headers = response.headers.get('Access-Control-Allow-Headers', 'NOT_SET')
            
            print(f"✅ {origin}")
            print(f"   Status: {response.status_code}")
            print(f"   Allow-Origin: {cors_origin}")
            print(f"   Allow-Methods: {cors_methods}")
            print(f"   Allow-Headers: {cors_headers}")
            
            # Verify CORS is working
            if cors_origin == origin or cors_origin == '*':
                print(f"   ✅ CORS working for {origin}")
            else:
                print(f"   ❌ CORS NOT working for {origin}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {origin} - Backend not running on localhost:5000")
        except Exception as e:
            print(f"❌ {origin} - Error: {e}")
        
        print()
    
    print("=" * 60)
    print("🎯 CORS Test Complete")
    print("\nTo start the backend for testing:")
    print("cd backend && python app.py")

if __name__ == "__main__":
    test_cors_headers()
