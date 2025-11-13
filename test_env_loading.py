"""
Test Environment Variable Loading
Verifies that .env file is loaded correctly
"""

import os
from dotenv import load_dotenv
from pathlib import Path

print("\n" + "="*70)
print("  ENVIRONMENT VARIABLE LOADING TEST")
print("="*70)

# Test 1: Load from current directory
print("\n[Test 1] Loading from current directory...")
load_dotenv()
print(f"   RDS_HOST: {os.getenv('RDS_HOST', 'NOT SET')}")

# Test 2: Load from explicit path
print("\n[Test 2] Loading from explicit path...")
env_path = Path(__file__).parent / '.env'
print(f"   .env path: {env_path}")
print(f"   File exists: {env_path.exists()}")

load_dotenv(dotenv_path=env_path, override=True)
print(f"   RDS_HOST: {os.getenv('RDS_HOST', 'NOT SET')}")
print(f"   RDS_DATABASE: {os.getenv('RDS_DATABASE', 'NOT SET')}")
print(f"   RDS_USER: {os.getenv('RDS_USER', 'NOT SET')}")
print(f"   RDS_PASSWORD: {'*' * len(os.getenv('RDS_PASSWORD', '')) if os.getenv('RDS_PASSWORD') else 'NOT SET'}")

# Test 3: Check all required variables
print("\n[Test 3] Checking required RDS variables...")
required_vars = ['RDS_HOST', 'RDS_DATABASE', 'RDS_USER', 'RDS_PASSWORD']
all_set = True

for var in required_vars:
    value = os.getenv(var)
    if value:
        display_value = '*' * 10 if 'PASSWORD' in var else value
        print(f"   ✅ {var}: {display_value}")
    else:
        print(f"   ❌ {var}: NOT SET")
        all_set = False

print("\n" + "="*70)
if all_set:
    print("✅ ALL REQUIRED VARIABLES ARE SET")
    print("\nYou can now run:")
    print("  python backend/test_rds_connection.py")
    print("  python backend/diagnose_auth_issue.py")
else:
    print("❌ SOME VARIABLES ARE MISSING")
    print("\nPlease check your backend/.env file")
print("="*70 + "\n")
