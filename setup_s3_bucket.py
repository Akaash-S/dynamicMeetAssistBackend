"""
Setup S3 Bucket for MeetingMind
"""
import os
import sys
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

def setup_s3_bucket():
    print("=" * 60)
    print("S3 BUCKET SETUP")
    print("=" * 60)
    print()
    
    # Get configuration
    bucket_name = os.getenv('S3_BUCKET_NAME', 'meetingmind-storage')
    region = os.getenv('AWS_REGION', 'ap-south-1')
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    print(f"Bucket Name: {bucket_name}")
    print(f"Region: {region}")
    print(f"Access Key: {access_key[:10]}...{access_key[-4:] if access_key else 'Not set'}")
    print()
    
    if not all([access_key, secret_key, bucket_name]):
        print("❌ AWS credentials not configured!")
        print("   Please set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and S3_BUCKET_NAME in .env")
        return False
    
    try:
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        print("✅ S3 client initialized")
        print()
        
        # Check if bucket exists
        print(f"Checking if bucket '{bucket_name}' exists...")
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket '{bucket_name}' already exists!")
            print()
            
            # Test bucket access
            print("Testing bucket access...")
            try:
                # Try to list objects
                response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                print("✅ Bucket is accessible!")
                print(f"   Objects in bucket: {response.get('KeyCount', 0)}")
                print()
                return True
            except ClientError as access_error:
                print(f"❌ Cannot access bucket: {access_error}")
                return False
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == '404':
                print(f"⚠️  Bucket does not exist. Creating...")
                print()
                
                # Create bucket
                try:
                    if region == 'us-east-1':
                        s3_client.create_bucket(Bucket=bucket_name)
                    else:
                        s3_client.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': region}
                        )
                    
                    print(f"✅ Bucket '{bucket_name}' created successfully!")
                    print()
                    
                    # Enable versioning
                    print("Enabling versioning...")
                    try:
                        s3_client.put_bucket_versioning(
                            Bucket=bucket_name,
                            VersioningConfiguration={'Status': 'Enabled'}
                        )
                        print("✅ Versioning enabled")
                    except Exception as ve:
                        print(f"⚠️  Could not enable versioning: {ve}")
                    
                    # Enable encryption
                    print("Enabling encryption...")
                    try:
                        s3_client.put_bucket_encryption(
                            Bucket=bucket_name,
                            ServerSideEncryptionConfiguration={
                                'Rules': [{
                                    'ApplyServerSideEncryptionByDefault': {
                                        'SSEAlgorithm': 'AES256'
                                    }
                                }]
                            }
                        )
                        print("✅ Encryption enabled")
                    except Exception as ee:
                        print(f"⚠️  Could not enable encryption: {ee}")
                    
                    # Set CORS policy
                    print("Setting CORS policy...")
                    try:
                        s3_client.put_bucket_cors(
                            Bucket=bucket_name,
                            CORSConfiguration={
                                'CORSRules': [{
                                    'AllowedHeaders': ['*'],
                                    'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE'],
                                    'AllowedOrigins': ['*'],
                                    'ExposeHeaders': ['ETag'],
                                    'MaxAgeSeconds': 3000
                                }]
                            }
                        )
                        print("✅ CORS policy set")
                    except Exception as ce:
                        print(f"⚠️  Could not set CORS: {ce}")
                    
                    print()
                    print("=" * 60)
                    print("✅ S3 BUCKET SETUP COMPLETE!")
                    print("=" * 60)
                    return True
                    
                except ClientError as create_error:
                    error_code = create_error.response['Error']['Code']
                    error_msg = create_error.response['Error']['Message']
                    
                    print(f"❌ Failed to create bucket!")
                    print(f"   Error Code: {error_code}")
                    print(f"   Message: {error_msg}")
                    print()
                    
                    if error_code == 'AccessDenied':
                        print("💡 Solution:")
                        print("   1. Go to AWS IAM Console")
                        print("   2. Add S3 permissions to your IAM user")
                        print("   3. Or create bucket manually in S3 Console")
                    
                    return False
            else:
                print(f"❌ Error checking bucket: {e}")
                return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    print()
    success = setup_s3_bucket()
    print()
    
    if success:
        print("🎉 S3 bucket is ready to use!")
    else:
        print("❌ S3 bucket setup failed. Check errors above.")
    
    print()
