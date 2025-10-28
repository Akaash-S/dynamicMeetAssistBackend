from supabase import create_client, Client
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class StorageService:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        self.client: Client = None
        self.bucket_name = 'meeting-audio'
        
        if not self.url or not self.key:
            print("⚠️ SUPABASE_URL and SUPABASE_KEY environment variables are required")
            print(f"⚠️ SUPABASE_URL present: {bool(self.url)}")
            print(f"⚠️ SUPABASE_KEY present: {bool(self.key)}")
            return
        
        try:
            print(f"🔄 Initializing Supabase client with URL: {self.url}")
            self.client = create_client(self.url, self.key)
            print(f"✅ Supabase client initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Supabase client: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            if "getaddrinfo failed" in str(e):
                print("🌐 DNS resolution failed - check internet connection and Supabase URL")
            self.client = None
    
    def test_connection(self) -> bool:
        """Test if Supabase connection is working"""
        if not self.client:
            print("❌ Supabase client not initialized for connection test")
            return False
        
        try:
            # Try to list buckets to test connection
            buckets = self.client.storage.list_buckets()
            print(f"✅ Supabase connection test successful - found {len(buckets)} buckets")
            return True
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Supabase connection test failed: {e}")
            if "getaddrinfo failed" in error_msg:
                print("🌐 DNS resolution issue - server may be unreachable")
            elif "ConnectionError" in error_msg or "timeout" in error_msg.lower():
                print("🌐 Network connectivity issue")
            return False
    
    def upload_file(self, file_path: str, file_data: bytes, content_type: str = 'audio/mpeg') -> Optional[str]:
        """Upload file to Supabase storage"""
        if not self.client:
            print("❌ Supabase client not initialized - cannot upload file")
            return None
        
        try:
            print(f"🔄 Attempting to upload to Supabase: {file_path}")
            
            # Upload file to storage
            result = self.client.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_data,
                file_options={
                    'content-type': content_type,
                    'cache-control': '3600'
                }
            )
            
            print(f"📤 Upload result: {result}")
            
            if result.status_code == 200:
                # Get public URL
                public_url = self.client.storage.from_(self.bucket_name).get_public_url(file_path)
                print(f"✅ File uploaded successfully: {public_url}")
                return public_url
            else:
                print(f"❌ Upload failed with status: {result.status_code}, response: {result}")
                return None
                
        except Exception as e:
            print(f"❌ Error uploading file to Supabase: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            # Check if it's a network connectivity issue
            if "getaddrinfo failed" in str(e) or "ConnectionError" in str(type(e).__name__):
                print("🌐 Network connectivity issue detected - Supabase server may be unreachable")
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from Supabase storage"""
        try:
            result = self.client.storage.from_(self.bucket_name).remove([file_path])
            return result.status_code == 200
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
    
    def get_file_url(self, file_path: str) -> Optional[str]:
        """Get public URL for a file"""
        try:
            return self.client.storage.from_(self.bucket_name).get_public_url(file_path)
        except Exception as e:
            print(f"Error getting file URL: {e}")
            return None
    
    def create_bucket_if_not_exists(self):
        """Create the bucket if it doesn't exist"""
        try:
            # List buckets to check if our bucket exists
            buckets = self.client.storage.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]
            
            if self.bucket_name not in bucket_names:
                # Create bucket
                self.client.storage.create_bucket(
                    self.bucket_name,
                    options={
                        'public': True,
                        'file_size_limit': 104857600,  # 100MB
                        'allowed_mime_types': ['audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/m4a']
                    }
                )
                print(f"✅ Created bucket: {self.bucket_name}")
            else:
                print(f"✅ Bucket {self.bucket_name} already exists")
                
        except Exception as e:
            print(f"❌ Error with bucket operations: {e}")

# Global storage instance
storage = StorageService()
