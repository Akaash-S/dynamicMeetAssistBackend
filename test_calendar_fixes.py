#!/usr/bin/env python3
"""
Calendar Fixes Test
===================
Test the calendar token refresh and error handling fixes
"""

import requests
import json

# Test configuration
BASE_URL = "https://dynamicmeetassistbackend-1.onrender.com"
TEST_USER_ID = "6f9015e7-f4c1-4353-ac33-3aeb727158e7"

def test_calendar_token_expiration():
    """Test calendar token expiration handling"""
    print("🔍 Testing calendar token expiration handling...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/calendar/test",
            params={'user_id': TEST_USER_ID},
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"   Status code: {response.status_code}")
        
        if response.status_code == 401:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            # Check for expected fields
            expected_fields = ['success', 'error', 'error_code', 'action_required']
            missing_fields = [field for field in expected_fields if field not in data]
            
            if not missing_fields:
                print("   ✅ All expected fields present")
                
                if data.get('error_code') == 'TOKEN_EXPIRED':
                    print("   ✅ Correct error code: TOKEN_EXPIRED")
                else:
                    print(f"   ❌ Unexpected error code: {data.get('error_code')}")
                
                if data.get('action_required') == 'reconnect_google_account':
                    print("   ✅ Correct action required: reconnect_google_account")
                else:
                    print(f"   ❌ Unexpected action: {data.get('action_required')}")
                
                if 'reconnect your Google account' in data.get('error', ''):
                    print("   ✅ User-friendly error message")
                else:
                    print("   ❌ Error message not user-friendly")
                
                return True
            else:
                print(f"   ❌ Missing fields: {missing_fields}")
                return False
        else:
            print(f"   ❌ Unexpected status code. Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False


def test_calendar_disconnect():
    """Test calendar disconnect functionality"""
    print("🔍 Testing calendar disconnect...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/calendar/disconnect",
            params={'user_id': TEST_USER_ID},
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"   Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            if data.get('success'):
                print("   ✅ Calendar disconnect successful")
                return True
            else:
                print(f"   ❌ Disconnect failed: {data.get('error')}")
                return False
        else:
            print(f"   ❌ Unexpected status: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
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
            return True
        else:
            print(f"   ❌ Health check failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Health test failed: {e}")
        return False


def main():
    """Run all calendar tests"""
    print("🚀 Starting Calendar Fixes Test Suite")
    print("=" * 50)
    
    tests = [
        ("Health Endpoint", test_health_endpoint),
        ("Calendar Token Expiration", test_calendar_token_expiration),
        ("Calendar Disconnect", test_calendar_disconnect),
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
    print("📊 Calendar Test Results Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All calendar tests passed! Token expiration is handled correctly.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)