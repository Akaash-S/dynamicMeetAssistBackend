"""
Debug AWS Setup - Test and diagnose issues
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("="*60)
print("AWS Setup Debug Tool")
print("="*60)

# Check environment variables
print("\n1. Checking Environment Variables...")
aws_vars = {
    'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
    'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'),
    'AWS_REGION': os.getenv('AWS_REGION'),
    'RDS_HOST': os.getenv('RDS_HOST'),
    'RDS_PORT': os.getenv('RDS_PORT'),
    'RDS_DATABASE': os.getenv('RDS_DATABASE'),
    'RDS_USER': os.getenv('RDS_USER'),
    'RDS_PASSWORD': os.getenv('RDS_PASSWORD'),
    'S3_BUCKET_NAME': os.getenv('S3_BUCKET_NAME'),
}

for key, value in aws_vars.items():
    if value:
        if 'PASSWORD' in key or 'SECRET' in key:
            print(f"✓ {key}: {'*' * 8}")
        else:
            print(f"✓ {key}: {value}")
    else:
        print(f"✗ {key}: NOT SET")

# Test AWS credentials
print("\n2. Testing AWS Credentials...")
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    
    sts = boto3.client('sts',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )
    
    identity = sts.get_caller_identity()
    print(f"✓ AWS Credentials Valid")
    print(f"  Account: {identity['Account']}")
    print(f"  User ARN: {identity['Arn']}")
    
except NoCredentialsError:
    print("✗ AWS credentials not found or invalid")
    sys.exit(1)
except ClientError as e:
    print(f"✗ AWS credentials error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error testing credentials: {e}")
    sys.exit(1)

# Test RDS connection
print("\n3. Testing RDS Connection...")
try:
    import psycopg2
    
    conn = psycopg2.connect(
        host=os.getenv('RDS_HOST'),
        port=os.getenv('RDS_PORT'),
        database=os.getenv('RDS_DATABASE'),
        user=os.getenv('RDS_USER'),
        password=os.getenv('RDS_PASSWORD'),
        connect_timeout=10
    )
    
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"✓ RDS Connection Successful")
    print(f"  PostgreSQL: {version[0][:50]}...")
    
    # Check existing tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()
    
    if tables:
        print(f"  Existing tables ({len(tables)}):")
        for table in tables:
            print(f"    - {table[0]}")
    else:
        print("  No tables found (will be created)")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"✗ RDS Connection Failed: {e}")
    print("  Check:")
    print("    - RDS security group allows your IP")
    print("    - RDS instance is running")
    print("    - Credentials are correct")

# Test S3 access
print("\n4. Testing S3 Access...")
try:
    import boto3
    from botocore.exceptions import ClientError
    
    s3_client = boto3.client('s3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )
    
    bucket_name = os.getenv('S3_BUCKET_NAME')
    
    # Try to access bucket
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✓ S3 Bucket '{bucket_name}' exists and is accessible")
        
        # List objects
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        if 'Contents' in response:
            print(f"  Objects in bucket: {len(response['Contents'])}")
        else:
            print(f"  Bucket is empty")
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == '404':
            print(f"⚠ S3 Bucket '{bucket_name}' does not exist")
            print(f"  Will attempt to create it...")
            
            # Try to create bucket
            try:
                region = os.getenv('AWS_REGION')
                if region == 'us-east-1':
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                print(f"✓ Successfully created bucket '{bucket_name}'")
                
            except ClientError as create_error:
                print(f"✗ Failed to create bucket: {create_error}")
                print(f"  Error code: {create_error.response['Error']['Code']}")
                print(f"  Message: {create_error.response['Error']['Message']}")
                
        elif error_code == '403':
            print(f"✗ Access denied to bucket '{bucket_name}'")
            print("  Check IAM permissions:")
            print("    - s3:ListBucket")
            print("    - s3:GetObject")
            print("    - s3:PutObject")
            print("    - s3:CreateBucket")
        else:
            print(f"✗ S3 Error: {e}")
            
except Exception as e:
    print(f"✗ S3 Test Failed: {e}")

# Test schema file
print("\n5. Checking Schema File...")
schema_path = os.path.join(os.path.dirname(__file__), 'migrations', 'rds_schema.sql')
if os.path.exists(schema_path):
    print(f"✓ Schema file found: {schema_path}")
    with open(schema_path, 'r') as f:
        content = f.read()
        # Count CREATE TABLE statements
        table_count = content.upper().count('CREATE TABLE')
        print(f"  Contains {table_count} CREATE TABLE statements")
else:
    print(f"✗ Schema file not found: {schema_path}")
    print("  This file is required for automatic table creation")

# Test Redis
print("\n6. Testing Redis Connection...")
try:
    import redis
    
    r = redis.Redis(
        host=os.getenv('REDIS_HOST', 'redis-14654.c212.ap-south-1-1.ec2.cloud.redislabs.com'),
        port=int(os.getenv('REDIS_PORT', 14654)),
        password=os.getenv('REDIS_PASSWORD') or None,
        db=int(os.getenv('REDIS_DB', 0)),
        socket_connect_timeout=2
    )
    
    r.ping()
    print(f"✓ Redis connection successful")
    info = r.info('server')
    print(f"  Version: {info.get('redis_version', 'unknown')}")
    
except Exception as e:
    print(f"⚠ Redis not available: {e}")
    print("  2FA rate limiting will be disabled")

# Summary
print("\n" + "="*60)
print("Summary")
print("="*60)
print("\nReady to run auto-setup:")
print("  python initialize.py")
print("\nOr start server with auto-setup:")
print("  python app.py")
print("\n" + "="*60)
