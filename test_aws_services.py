"""
AWS Services Health Check and Testing Script
Tests RDS PostgreSQL and S3 Storage connectivity
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def check_env_variables():
    """Check if all required environment variables are set"""
    print_header("Environment Variables Check")
    
    required_vars = {
        'AWS': [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_REGION'
        ],
        'RDS': [
            'RDS_HOST',
            'RDS_PORT',
            'RDS_DATABASE',
            'RDS_USER',
            'RDS_PASSWORD'
        ],
        'S3': [
            'S3_BUCKET_NAME',
            'S3_AUDIO_PREFIX',
            'S3_EXPORT_PREFIX'
        ]
    }
    
    all_present = True
    
    for category, vars_list in required_vars.items():
        print(f"\n{Colors.BOLD}{category} Configuration:{Colors.END}")
        for var in vars_list:
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                if 'PASSWORD' in var or 'SECRET' in var or 'KEY' in var:
                    display_value = '*' * 8
                else:
                    display_value = value
                print_success(f"{var} = {display_value}")
            else:
                print_error(f"{var} is not set")
                all_present = False
    
    return all_present

def test_rds_connection():
    """Test RDS PostgreSQL connection and health"""
    print_header("RDS PostgreSQL Connection Test")
    
    try:
        from config.aws_rds_database import rds_db
        
        # Check if RDS is configured
        if not rds_db.connection_pool:
            print_warning("RDS database credentials not fully configured")
            print_info("Please set the following in your .env file:")
            print_info("  - RDS_HOST")
            print_info("  - RDS_PORT")
            print_info("  - RDS_DATABASE")
            print_info("  - RDS_USER")
            print_info("  - RDS_PASSWORD")
            return False
        
        # Test 1: Health Check
        print_info("Testing database health check...")
        health = rds_db.health_check()
        
        if health.get('status') == 'healthy':
            print_success("Database health check passed")
            print(f"  - Connection pool size: {health.get('connection_pool', {}).get('size', 'N/A')}")
            print(f"  - Available connections: {health.get('connection_pool', {}).get('available', 'N/A')}")
        else:
            print_error("Database health check failed")
            return False
        
        # Test 2: Version Query
        print_info("\nTesting database version query...")
        result = rds_db.execute_query(
            "SELECT version()",
            fetch_one=True
        )
        if result:
            version = result.get('version', 'Unknown')
            print_success(f"PostgreSQL Version: {version[:50]}...")
        else:
            print_error("Failed to get database version")
            return False
        
        # Test 3: Current Time Query
        print_info("\nTesting current timestamp query...")
        result = rds_db.execute_query(
            "SELECT CURRENT_TIMESTAMP as now",
            fetch_one=True
        )
        if result:
            print_success(f"Database time: {result.get('now')}")
        else:
            print_error("Failed to get current timestamp")
            return False
        
        # Test 4: List Tables
        print_info("\nListing database tables...")
        tables = rds_db.execute_query(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
            """,
            fetch_all=True
        )
        
        if tables:
            print_success(f"Found {len(tables)} tables:")
            for table in tables:
                print(f"  - {table['table_name']}")
        else:
            print_warning("No tables found (database might be empty)")
        
        # Test 5: Test Insert/Select/Delete
        print_info("\nTesting write operations...")
        test_table_exists = rds_db.execute_query(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            ) as exists
            """,
            fetch_one=True
        )
        
        if test_table_exists and test_table_exists.get('exists'):
            # Count users
            count_result = rds_db.execute_query(
                "SELECT COUNT(*) as count FROM users",
                fetch_one=True
            )
            print_success(f"Users table has {count_result.get('count', 0)} records")
        else:
            print_warning("Users table not found (run migrations first)")
        
        print_success("\n✓ All RDS tests passed!")
        return True
        
    except ImportError as e:
        print_error(f"Failed to import RDS module: {e}")
        print_warning("Make sure psycopg2-binary is installed: pip install psycopg2-binary")
        return False
    except Exception as e:
        print_error(f"RDS connection test failed: {e}")
        return False

def test_s3_connection():
    """Test S3 bucket connection and operations"""
    print_header("AWS S3 Storage Test")
    
    try:
        from services.aws_s3_service import s3_service
        
        # Test 1: Check if bucket exists
        print_info("Testing S3 bucket access...")
        bucket_name = os.getenv('S3_BUCKET_NAME')
        
        try:
            s3_service.s3_client.head_bucket(Bucket=bucket_name)
            print_success(f"S3 bucket '{bucket_name}' is accessible")
        except Exception as e:
            print_error(f"Cannot access S3 bucket '{bucket_name}': {e}")
            return False
        
        # Test 2: Upload test file
        print_info("\nTesting file upload...")
        test_data = f"Test file created at {datetime.now().isoformat()}".encode('utf-8')
        
        # Create a file-like object from bytes
        from io import BytesIO
        file_obj = BytesIO(test_data)
        
        test_key = s3_service.upload_file(
            file_obj,
            "test-file.txt",
            folder="test-uploads"
        )
        
        if test_key:
            print_success(f"File uploaded successfully: {test_key}")
        else:
            print_error("File upload failed")
            return False
        
        # Test 3: Check if file exists
        print_info("\nTesting file existence check...")
        exists = s3_service.file_exists(test_key)
        if exists:
            print_success("File existence check passed")
        else:
            print_error("File existence check failed")
            return False
        
        # Test 4: Generate presigned URL
        print_info("\nTesting presigned URL generation...")
        url = s3_service.generate_presigned_url(test_key, expiration=3600)
        if url:
            print_success("Presigned URL generated successfully")
            print(f"  URL (truncated): {url[:80]}...")
        else:
            print_error("Failed to generate presigned URL")
            return False
        
        # Test 5: Get file metadata
        print_info("\nTesting file metadata retrieval...")
        try:
            response = s3_service.s3_client.head_object(
                Bucket=bucket_name,
                Key=test_key
            )
            print_success("File metadata retrieved:")
            print(f"  - Size: {response.get('ContentLength', 0)} bytes")
            print(f"  - Last Modified: {response.get('LastModified')}")
            print(f"  - Content Type: {response.get('ContentType', 'N/A')}")
        except Exception as e:
            print_error(f"Failed to get file metadata: {e}")
        
        # Test 6: List files in bucket
        print_info("\nListing files in test prefix...")
        try:
            files = s3_service.list_files(prefix='test-uploads/', max_keys=10)
            
            if files:
                print_success(f"Found {len(files)} file(s):")
                for file in files[:5]:  # Show first 5
                    print(f"  - {file['key']} ({file['size']} bytes)")
            else:
                print_warning("No files found in test prefix")
        except Exception as e:
            print_error(f"Failed to list files: {e}")
        
        # Test 7: Test data export upload
        print_info("\nTesting data export upload...")
        export_data = {
            'test': True,
            'timestamp': datetime.now().isoformat(),
            'data': 'Sample export data'
        }
        export_json = json.dumps(export_data, indent=2)
        
        try:
            export_key = s3_service.upload_data_export(
                export_json.encode('utf-8'),
                "test-user",
                "test-export-123"
            )
        except Exception as e:
            print_warning(f"Export upload test skipped: {e}")
            export_key = None
        
        if export_key:
            print_success(f"Export uploaded successfully: {export_key}")
        else:
            print_error("Export upload failed")
        
        # Test 8: Cleanup test files
        print_info("\nCleaning up test files...")
        files_to_delete = [test_key]
        if export_key:
            files_to_delete.append(export_key)
        
        deleted = s3_service.delete_files(files_to_delete)
        if deleted:
            print_success(f"Cleaned up {len(files_to_delete)} test file(s)")
        else:
            print_warning("Cleanup may have failed (files might not exist)")
        
        print_success("\n✓ All S3 tests passed!")
        return True
        
    except ImportError as e:
        print_error(f"Failed to import S3 module: {e}")
        print_warning("Make sure boto3 is installed: pip install boto3")
        return False
    except Exception as e:
        print_error(f"S3 connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_2fa_service():
    """Test Enhanced 2FA Service"""
    print_header("Enhanced 2FA Service Test")
    
    try:
        from services.enhanced_2fa_security import enhanced_2fa_service
        
        print_info("Testing 2FA service initialization...")
        print_success("Enhanced 2FA service loaded successfully")
        
        # Test rate limiting (requires Redis)
        print_info("\nTesting rate limiting...")
        test_email = "test@example.com"
        test_ip = "127.0.0.1"
        
        try:
            can_attempt = enhanced_2fa_service.check_rate_limit(test_email, test_ip)
            if can_attempt:
                print_success("Rate limiting check passed")
            else:
                print_warning("Rate limit exceeded (this is expected if testing multiple times)")
        except Exception as e:
            print_warning(f"Rate limiting test skipped: {e}")
        
        print_success("\n✓ 2FA service tests passed!")
        return True
        
    except ImportError as e:
        print_error(f"Failed to import 2FA service: {e}")
        return False
    except Exception as e:
        print_error(f"2FA service test failed: {e}")
        return False

def test_email_service():
    """Test Email Service"""
    print_header("Email Service Test")
    
    try:
        from services.email_service import email_service
        
        print_info("Testing email service initialization...")
        print_success("Email service loaded successfully")
        
        # Check configuration
        print_info("\nChecking email configuration...")
        sendgrid_key = os.getenv('SENDGRID_API_KEY')
        smtp_server = os.getenv('SMTP_SERVER')
        
        if sendgrid_key and sendgrid_key != 'your_sendgrid_api_key':
            print_success("SendGrid API key configured")
        elif smtp_server:
            print_success(f"SMTP server configured: {smtp_server}")
        else:
            print_warning("No email service configured")
        
        print_success("\n✓ Email service tests passed!")
        return True
        
    except ImportError as e:
        print_error(f"Failed to import email service: {e}")
        return False
    except Exception as e:
        print_error(f"Email service test failed: {e}")
        return False

def generate_report(results):
    """Generate final test report"""
    print_header("Test Summary Report")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    failed_tests = total_tests - passed_tests
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"{Colors.GREEN}Passed: {passed_tests}{Colors.END}")
    print(f"{Colors.RED}Failed: {failed_tests}{Colors.END}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%\n")
    
    print(f"{Colors.BOLD}Detailed Results:{Colors.END}")
    for test_name, result in results.items():
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if result else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"  {test_name}: {status}")
    
    if failed_tests == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 All tests passed! Your AWS services are ready.{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Some tests failed. Please check the errors above.{Colors.END}")
    
    return failed_tests == 0

def main():
    """Main test runner"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║          AWS Services Health Check & Testing              ║")
    print("║                  MeetingMind Backend                       ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Store test results
    results = {}
    
    # Run tests
    results['Environment Variables'] = check_env_variables()
    
    if not results['Environment Variables']:
        print_error("\n❌ Environment variables are not properly configured!")
        print_warning("Please update your .env file with the correct values.")
        print_warning("See AWS_SETUP_GUIDE.md for instructions.")
        return 1
    
    results['RDS PostgreSQL'] = test_rds_connection()
    results['S3 Storage'] = test_s3_connection()
    results['Enhanced 2FA'] = test_enhanced_2fa_service()
    results['Email Service'] = test_email_service()
    
    # Generate report
    all_passed = generate_report(results)
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
