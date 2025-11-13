"""
Check why RDS connection pool is not initializing
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("\n" + "="*70)
print("Checking RDS Initialization")
print("="*70)

# Check environment variables
print("\n1. Environment Variables:")
env_vars = {
    'RDS_HOST': os.getenv('RDS_HOST'),
    'RDS_PORT': os.getenv('RDS_PORT', '5432'),
    'RDS_DATABASE': os.getenv('RDS_DATABASE'),
    'RDS_USER': os.getenv('RDS_USER'),
    'RDS_PASSWORD': os.getenv('RDS_PASSWORD'),
}

for key, value in env_vars.items():
    if value:
        if 'PASSWORD' in key:
            print(f"  ✅ {key}: {'*' * len(value)}")
        else:
            print(f"  ✅ {key}: {value}")
    else:
        print(f"  ❌ {key}: NOT SET")

all_set = all(env_vars.values())
print(f"\n  All variables set: {'✅ YES' if all_set else '❌ NO'}")

if not all_set:
    print("\n❌ Missing environment variables!")
    print("   The connection pool cannot initialize without all credentials.")
    exit(1)

# Try to import and check rds_db
print("\n2. Importing RDS Database:")
try:
    from config.aws_rds_database import rds_db
    print("  ✅ Import successful")
    
    print("\n3. Connection Pool Status:")
    if rds_db.connection_pool:
        print("  ✅ Connection pool initialized")
        
        # Try health check
        print("\n4. Health Check:")
        health = rds_db.health_check()
        print(f"  Status: {health['status']}")
        if health['status'] == 'healthy':
            print(f"  ✅ Database: {health['database']['name']}")
            print(f"  ✅ Host: {health['database']['host']}")
        else:
            print(f"  ❌ Error: {health.get('error')}")
    else:
        print("  ❌ Connection pool NOT initialized")
        print("\n  Possible reasons:")
        print("    1. Environment variables not loaded before import")
        print("    2. Connection failed during initialization")
        print("    3. Credentials are incorrect")
        
        # Try to initialize manually
        print("\n5. Attempting Manual Initialization:")
        try:
            rds_db._initialize_pool()
            if rds_db.connection_pool:
                print("  ✅ Manual initialization successful!")
            else:
                print("  ❌ Manual initialization failed")
        except Exception as e:
            print(f"  ❌ Error: {e}")

except Exception as e:
    print(f"  ❌ Import failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
