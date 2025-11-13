"""
Comprehensive Endpoint Testing Script
Tests all backend endpoints to verify functionality
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Base URL
BASE_URL = "http://localhost:8000"

# Test results storage
test_results = []

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def test_endpoint(
    method: str,
    endpoint: str,
    data: Dict = None,
    headers: Dict = None,
    description: str = ""
) -> Tuple[bool, str, Dict]:
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            return False, f"Unknown method: {method}", {}
        
        success = response.status_code < 400
        
        try:
            response_data = response.json()
        except:
            response_data = {"text": response.text[:200]}
        
        return success, f"Status {response.status_code}", response_data
        
    except requests.exceptions.ConnectionError:
        return False, "Connection refused - Server not running?", {}
    except requests.exceptions.Timeout:
        return False, "Request timeout", {}
    except Exception as e:
        return False, f"Error: {str(e)}", {}

def run_tests():
    """Run all endpoint tests"""
    
    print_header("Backend Endpoint Testing")
    print(f"Testing server at: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Test data
    test_user_id = "test-user-123"
    test_email = "test@example.com"
    
    # ========================================
    # Health & Status Endpoints
    # ========================================
    print_header("Health & Status Endpoints")
    
    tests = [
        ("GET", "/", None, "Root endpoint"),
        ("GET", "/api/health", None, "Simple health check"),
        ("GET", "/api/health/detailed", None, "Detailed health check"),
    ]
    
    for method, endpoint, data, desc in tests:
        success, message, response = test_endpoint(method, endpoint, data, description=desc)
        test_results.append({
            'endpoint': endpoint,
            'method': method,
            'description': desc,
            'success': success,
            'message': message
        })
        
        if success:
            print_success(f"{method} {endpoint} - {desc}")
        else:
            print_error(f"{method} {endpoint} - {desc}: {message}")
    
    # ========================================
    # Authentication Endpoints
    # ========================================
    print_header("Authentication Endpoints")
    
    tests = [
        ("POST", "/api/auth/verify", {
            "email": test_email,
            "name": "Test User",
            "firebase_uid": test_user_id,
            "auth_provider": "firebase"
        }, "Verify/create user (Firebase)"),
        
        ("POST", "/api/auth/verify", {
            "email": "google@example.com",
            "name": "Google User",
            "firebase_uid": "google-test-123",
            "auth_provider": "google_oauth"
        }, "Verify/create user (Google OAuth)"),
    ]
    
    for method, endpoint, data, desc in tests:
        success, message, response = test_endpoint(method, endpoint, data, description=desc)
        test_results.append({
            'endpoint': endpoint,
            'method': method,
            'description': desc,
            'success': success,
            'message': message
        })
        
        if success:
            print_success(f"{method} {endpoint} - {desc}")
        else:
            print_error(f"{method} {endpoint} - {desc}: {message}")
    
    # ========================================
    # Meeting Endpoints
    # ========================================
    print_header("Meeting Endpoints")
    
    headers = {"X-User-ID": test_user_id}
    
    tests = [
        ("GET", "/api/meetings/test", None, "Test meetings blueprint"),
        
        ("GET", "/api/meetings/debug", None, "Debug meetings endpoint"),
        
        ("GET", "/api/meetings", None, "Get all meetings"),
        
        ("GET", "/api/meetings/stats", None, "Get meeting statistics"),
        
        ("GET", "/api/meetings/routes", None, "List meeting routes"),
    ]
    
    for method, endpoint, data, desc in tests:
        success, message, response = test_endpoint(method, endpoint, data, headers, desc)
        test_results.append({
            'endpoint': endpoint,
            'method': method,
            'description': desc,
            'success': success,
            'message': message
        })
        
        if success:
            print_success(f"{method} {endpoint} - {desc}")
        else:
            print_error(f"{method} {endpoint} - {desc}: {message}")
    
    # ========================================
    # Task Endpoints
    # ========================================
    print_header("Task Endpoints")
    
    tests = [
        ("GET", "/api/tasks", None, "Get all tasks"),
        
        ("GET", "/api/tasks/stats", None, "Get task statistics"),
        
        ("GET", "/api/tasks/upcoming", None, "Get upcoming tasks"),
    ]
    
    for method, endpoint, data, desc in tests:
        success, message, response = test_endpoint(method, endpoint, data, headers, desc)
        test_results.append({
            'endpoint': endpoint,
            'method': method,
            'description': desc,
            'success': success,
            'message': message
        })
        
        if success:
            print_success(f"{method} {endpoint} - {desc}")
        else:
            print_error(f"{method} {endpoint} - {desc}: {message}")
    
    # ========================================
    # Upload Endpoints
    # ========================================
    print_header("Upload Endpoints")
    
    tests = [
        ("GET", "/api/upload/meetings", None, "List recent meetings"),
    ]
    
    for method, endpoint, data, desc in tests:
        success, message, response = test_endpoint(method, endpoint, data, headers, desc)
        test_results.append({
            'endpoint': endpoint,
            'method': method,
            'description': desc,
            'success': success,
            'message': message
        })
        
        if success:
            print_success(f"{method} {endpoint} - {desc}")
        else:
            print_error(f"{method} {endpoint} - {desc}: {message}")
    
    print_info("Note: File upload tests require actual file data")
    print_warning("Skipping POST /api/upload/audio (requires multipart/form-data)")
    
    # ========================================
    # Admin Endpoints
    # ========================================
    print_header("Admin Endpoints")
    
    tests = [
        ("POST", "/api/admin/auth/login", {
            "email": "admin@dynamicmeetingassistant.com",
            "password": "admin123"
        }, "Admin login"),
        
        ("GET", "/api/admin/users", None, "Get all users (admin)"),
        
        ("GET", "/api/admin/issues", None, "Get all issues (admin)"),
        
        ("GET", "/api/admin/payments", None, "Get all payments (admin)"),
    ]
    
    for method, endpoint, data, desc in tests:
        success, message, response = test_endpoint(method, endpoint, data, description=desc)
        test_results.append({
            'endpoint': endpoint,
            'method': method,
            'description': desc,
            'success': success,
            'message': message
        })
        
        if success:
            print_success(f"{method} {endpoint} - {desc}")
        else:
            print_error(f"{method} {endpoint} - {desc}: {message}")
    
    # ========================================
    # 2FA Endpoints (if registered)
    # ========================================
    print_header("Two-Factor Authentication Endpoints")
    
    print_info("Note: 2FA endpoints may not be registered in app.py")
    print_warning("Skipping 2FA tests (check if blueprint is registered)")
    
    # ========================================
    # Data Export Endpoints (if registered)
    # ========================================
    print_header("Data Export Endpoints")
    
    print_info("Note: Data export endpoints may not be registered in app.py")
    print_warning("Skipping data export tests (check if blueprint is registered)")
    
    # ========================================
    # Google Calendar Endpoints
    # ========================================
    print_header("Google Calendar Endpoints")
    
    tests = [
        ("GET", "/api/calendar/test", None, "Test calendar access"),
    ]
    
    for method, endpoint, data, desc in tests:
        success, message, response = test_endpoint(method, endpoint, data, headers, desc)
        test_results.append({
            'endpoint': endpoint,
            'method': method,
            'description': desc,
            'success': success,
            'message': message
        })
        
        if success:
            print_success(f"{method} {endpoint} - {desc}")
        else:
            print_error(f"{method} {endpoint} - {desc}: {message}")

def print_summary():
    """Print test summary"""
    print_header("Test Summary")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r['success'])
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"{Colors.GREEN}Passed: {passed_tests}{Colors.END}")
    print(f"{Colors.RED}Failed: {failed_tests}{Colors.END}")
    print(f"Success Rate: {success_rate:.1f}%\n")
    
    # Group by status
    if failed_tests > 0:
        print(f"{Colors.BOLD}Failed Endpoints:{Colors.END}")
        for result in test_results:
            if not result['success']:
                print(f"  {Colors.RED}✗{Colors.END} {result['method']} {result['endpoint']}")
                print(f"    {result['description']}")
                print(f"    Error: {result['message']}")
    
    # Recommendations
    print(f"\n{Colors.BOLD}Recommendations:{Colors.END}")
    
    if failed_tests == total_tests:
        print_error("Server is not running or not accessible")
        print_info("Start the server with: start_backend.bat")
    elif failed_tests > 0:
        print_warning(f"{failed_tests} endpoints need attention")
        print_info("These endpoints may need migration to RDS/S3")
        print_info("Run: analyze_migration.bat")
    else:
        print_success("All endpoints are working!")
        print_info("Backend is fully functional")
    
    print(f"\n{Colors.BOLD}Next Steps:{Colors.END}")
    if failed_tests > 0:
        print("1. Check which endpoints failed")
        print("2. Run: analyze_migration.bat")
        print("3. Migrate endpoints to RDS/S3")
        print("4. Run this test again")
    else:
        print("1. ✓ All endpoints working")
        print("2. Test with frontend application")
        print("3. Deploy to production")

def main():
    """Main test runner"""
    try:
        # Check if server is running
        print_info("Checking if server is running...")
        try:
            response = requests.get(f"{BASE_URL}/api/health", timeout=2)
            print_success("Server is running!")
        except:
            print_error("Server is not running!")
            print_info("Start the server with: start_backend.bat")
            print_info("Or run: cd backend && python app.py")
            return
        
        # Run all tests
        run_tests()
        
        # Print summary
        print_summary()
        
        # Save results to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_tests': len(test_results),
                'passed': sum(1 for r in test_results if r['success']),
                'failed': sum(1 for r in test_results if not r['success']),
                'results': test_results
            }, f, indent=2)
        
        print(f"\n{Colors.BLUE}Results saved to: {filename}{Colors.END}")
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Testing interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
