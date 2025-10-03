from supabase import create_client, Client
import os
from typing import Optional

class StorageService:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
        
        self.client: Client = create_client(self.url, self.key)
        self.bucket_name = 'meeting-audio'
    
    def upload_file(self, file_path: str, file_data: bytes, content_type: str = 'audio/mpeg') -> Optional[str]:
        """Upload file to Supabase storage"""
        try:
            # Upload file to storage
            result = self.client.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_data,
                file_options={
                    'content-type': content_type,
                    'cache-control': '3600'
                }
            )
            
            if result.status_code == 200:
                # Get public URL
                public_url = self.client.storage.from_(self.bucket_name).get_public_url(file_path)
                return public_url
            else:
                print(f"Upload failed: {result}")
                return None
                
        except Exception as e:
            print(f"Error uploading file: {e}")
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
