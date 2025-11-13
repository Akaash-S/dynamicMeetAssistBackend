"""
Verify Migration Status
Checks if the application is ready to use AWS RDS and S3
"""

import os
from dotenv import load_dotenv

load_dotenv()

def check_env_vars():
    """Check if required environment variables are set"""
    print("\n" + "="*70)
    print("Checking Environment Variables")
    print("="*70)
    
    required_vars = {
        'RDS': ['RDS_HOST', 'RDS_PORT', 'RDS_DATABASE', 'RDS_USER', 'RDS_PASSWORD'],
        'S3': ['S3_BUCKET_NAME', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION'],
        'Redis': ['REDIS_HOST', 'REDIS_PORT']
    }
    
    all_good = True
    
    for category, vars_list in required_vars.items():
        print(f"\n{category} Configuration:")
        for var in vars_list:
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                if 'PASSWORD' in var or 'SECRET' in var or 'KEY' in var:
                    display_value = value[:4] + '***' + value[-4:] if len(value) > 8 else '***'
                else:
                    display_value = value
                print(f"  ✅ {var}: {display_value}")
            else:
                print(f"  ❌ {var}: NOT SET")
                all_good = False
    
    return all_good


def check_rds_connection():
    """Check RDS database connection"""
    print("\n" + "="*70)
    print("Checking RDS Database Connection")
    print("="*70)
    
    try:
        from config.aws_rds_database import rds_db
        
        health = rds_db.health_check()
        
        if health['status'] == 'healthy':
            print("\n✅ RDS Connection: SUCCESS")
            print(f"   Host: {health['database']['host']}")
            print(f"   Database: {health['database']['name']}")
            print(f"   Port: {health['database']['port']}")
            return True
        else:
            print("\n❌ RDS Connection: FAILED")
            print(f"   Error: {health.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ RDS Connection: ERROR")
        print(f"   {e}")
        return False


def check_s3_connection():
    """Check S3 connection"""
    print("\n" + "="*70)
    print("Checking S3 Connection")
    print("="*70)
    
    try:
        from services.aws_s3_service import s3_service
        
        if s3_service.s3_client:
            # Try to list buckets
            try:
                buckets = s3_service.s3_client.list_buckets()
                print("\n✅ S3 Connection: SUCCESS")
                print(f"   Bucket: {s3_service.s3_bucket_name}")
                print(f"   Region: {s3_service.aws_region}")
                print(f"   Total buckets: {len(buckets['Buckets'])}")
                return True
            except Exception as e:
                print("\n⚠️  S3 Connection: PARTIAL")
                print(f"   Client initialized but cannot list buckets")
                print(f"   Error: {e}")
                return False
        else:
            print("\n❌ S3 Connection: FAILED")
            print("   S3 client not initialized")
            return False
            
    except Exception as e:
        print(f"\n❌ S3 Connection: ERROR")
        print(f"   {e}")
        return False


def check_redis_connection():
    """Check Redis connection"""
    print("\n" + "="*70)
    print("Checking Redis Connection")
    print("="*70)
    
    try:
        import redis
        
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD', '')
        
        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password if redis_password else None,
            decode_responses=True
        )
        
        # Test connection
        r.ping()
        
        print("\n✅ Redis Connection: SUCCESS")
        print(f"   Host: {redis_host}")
        print(f"   Port: {redis_port}")
        return True
        
    except Exception as e:
        print(f"\n⚠️  Redis Connection: FAILED")
        print(f"   Error: {e}")
        print("   Note: Redis is optional for 2FA rate limiting")
        return False


def check_totp_blueprint():
    """Check if TOTP blueprint is registered"""
    print("\n" + "="*70)
    print("Checking TOTP Blueprint Registration")
    print("="*70)
    
    try:
        app_path = os.path.join(os.path.dirname(__file__), 'app.py')
        with open(app_path, 'r') as f:
            content = f.read()
        
        if 'totp_auth_bp' in content and 'from routes.totp_auth import totp_auth_bp' in content:
            print("\n✅ TOTP Blueprint: REGISTERED")
            return True
        else:
            print("\n❌ TOTP Blueprint: NOT REGISTERED")
            print("   Run: python register_totp_blueprint.py")
            return False
            
    except Exception as e:
        print(f"\n❌ TOTP Blueprint: ERROR")
        print(f"   {e}")
        return False


def main():
    print("\n🔍 Migration Verification")
    print("="*70)
    
    results = {
        'Environment Variables': check_env_vars(),
        'RDS Connection': check_rds_connection(),
        'S3 Connection': check_s3_connection(),
        'Redis Connection': check_redis_connection(),
        'TOTP Blueprint': check_totp_blueprint()
    }
    
    print("\n" + "="*70)
    print("Verification Summary")
    print("="*70)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check}")
    
    all_passed = all(results.values())
    redis_optional = not results['Redis Connection']
    
    if all_passed:
        print("\n🎉 All checks passed! Your application is ready to use AWS RDS and S3.")
        print("\nNext steps:")
        print("  1. Run: python fix_rds_schema.py (to fix database schema)")
        print("  2. Run: python app.py (to start the server)")
    elif redis_optional and all(v for k, v in results.items() if k != 'Redis Connection'):
        print("\n✅ Core checks passed! Redis is optional.")
        print("\nNext steps:")
        print("  1. Run: python fix_rds_schema.py (to fix database schema)")
        print("  2. Run: python app.py (to start the server)")
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  • RDS: Check security group, credentials, and instance status")
        print("  • S3: Check IAM permissions and bucket existence")
        print("  • Redis: Install Redis or use cloud Redis")
        print("  • TOTP: Run python register_totp_blueprint.py")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
