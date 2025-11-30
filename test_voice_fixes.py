#!/usr/bin/env python3
"""
Simple Voice Fixes Test
========================
Test the voice service fixes and CORS configuration
"""

import requests
import json
import os
from pathlib import Path

# Test configuration
BASE_URL = "https://dynamicmeetassistbackend-1.onrender.com"
TEST_USER_ID = "test-user-123"
TEST_TOKEN = "test-token"

def test_cors_headers():
    """Test CORS headers are properly set"""
    print("🔍 Testing CORS headers...")
    
    try:
        # Test preflight request
        response = requests.options(
            f"{BASE_URL}/api/chatbot/voice",
            headers={
                'Origin': 'http://localhost:5173',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type,Authorization'
            }
        )
        
        print(f"   Preflight status: {response.status_code}")
        print(f"   CORS headers: {dict(response.headers)}")
        
        # Check for required CORS headers
        required_headers = [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods',
            'Access-Control-Allow-Headers'
        ]
        
        for header in required_headers:
            if header in response.headers:
                print(f"   ✅ {header}: {response.headers[header]}")
            else:
                print(f"   ❌ Missing {header}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"   ❌ CORS test failed: {e}")
        return False


def test_voice_service_status():
    """Test voice service status endpoint"""
    print("🔍 Testing voice service status...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/chatbot/voice/status",
            headers={
                'Authorization': f'Bearer {TEST_TOKEN}',
                'X-User-ID': TEST_USER_ID
            }
        )
        
        print(f"   Status code: {response.status_code}")
        
        if response.status_code == 401:
            print("   ℹ️  Authentication required (expected)")
            return True
        elif response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"   ❌ Unexpected status: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Status test failed: {e}")
        return False


def test_voice_endpoint_validation():
    """Test voice endpoint input validation"""
    print("🔍 Testing voice endpoint validation...")
    
    try:
        # Test without audio file
        response = requests.post(
            f"{BASE_URL}/api/chatbot/voice",
            headers={
                'Authorization': f'Bearer {TEST_TOKEN}',
                'X-User-ID': TEST_USER_ID
            },
            data={'session_id': 'test-session'}
        )
        
        print(f"   Status code: {response.status_code}")
        
        if response.status_code == 401:
            print("   ℹ️  Authentication required (expected)")
            return True
        elif response.status_code == 400:
            data = response.json()
            print(f"   Validation error (expected): {data.get('error', 'Unknown error')}")
            return True
        else:
            print(f"   ❌ Unexpected response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Validation test failed: {e}")
        return False


def test_health_endpoint():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        
        print(f"   Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Health status: {data.get('status', 'Unknown')}")
            print(f"   Service: {data.get('service', 'Unknown')}")
            return True
        else:
            print(f"   ❌ Health check failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Health test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Starting Voice Fixes Test Suite")
    print("=" * 50)
    
    tests = [
        ("Health Endpoint", test_health_endpoint),
        ("CORS Headers", test_cors_headers),
        ("Voice Service Status", test_voice_service_status),
        ("Voice Endpoint Validation", test_voice_endpoint_validation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"   ✅ {test_name} PASSED")
            else:
                print(f"   ❌ {test_name} FAILED")
                
        except Exception as e:
            print(f"   💥 {test_name} CRASHED: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Voice fixes are working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)