"""
AWS S3 Service for File Storage
Handles all file uploads, downloads, and management in S3
"""

import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import logging
import mimetypes
from typing import Optional, Dict, BinaryIO
import uuid

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self):
        self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.s3_bucket_name = os.getenv('S3_BUCKET_NAME')
        
        if not all([self.aws_access_key_id, self.aws_secret_access_key, self.s3_bucket_name]):
            logger.warning("AWS S3 credentials not fully configured. File storage will be limited.")
            self.s3_client = None
            self.s3_resource = None
        else:
            # Initialize S3 client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
            
            # Initialize S3 resource
            self.s3_resource = boto3.resource(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
    
    def upload_file(
        self,
        file_obj: BinaryIO,
        file_name: str,
        folder: str = 'uploads',
        content_type: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Upload a file to S3
        
        Args:
            file_obj: File object to upload
            file_name: Name of the file
            folder: Folder/prefix in S3 bucket
            content_type: MIME type of the file
            metadata: Additional metadata
        
        Returns:
            S3 key of uploaded file or None if failed
        """
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return None
        
        try:
            # Generate unique file key
            file_extension = os.path.splitext(file_name)[1]
            unique_id = str(uuid.uuid4())
            s3_key = f"{folder}/{unique_id}{file_extension}"
            
            # Determine content type
            if not content_type:
                content_type, _ = mimetypes.guess_type(file_name)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            # Prepare extra args
            extra_args = {
                'ContentType': content_type,
                'Metadata': metadata or {}
            }
            
            # Upload file
            self.s3_client.upload_fileobj(
                file_obj,
                self.s3_bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"File uploaded successfully: {s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return None
    
    def upload_file_from_path(
        self,
        file_path: str,
        folder: str = 'uploads',
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """Upload a file from local path to S3"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return None
        
        try:
            file_name = os.path.basename(file_path)
            
            with open(file_path, 'rb') as file_obj:
                return self.upload_file(file_obj, file_name, folder, metadata=metadata)
        except Exception as e:
            logger.error(f"Error uploading file from path: {e}")
            return None
    
    def download_file(
        self,
        s3_key: str,
        local_path: str
    ) -> bool:
        """
        Download a file from S3 to local path
        
        Args:
            s3_key: S3 key of the file
            local_path: Local path to save the file
        
        Returns:
            True if successful, False otherwise
        """
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False
        
        try:
            self.s3_client.download_file(
                self.s3_bucket_name,
                s3_key,
                local_path
            )
            logger.info(f"File downloaded successfully: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return False
    
    def get_file_object(self, s3_key: str) -> Optional[bytes]:
        """Get file content as bytes"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return None
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket_name,
                Key=s3_key
            )
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Error getting file object from S3: {e}")
            return None
    
    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        http_method: str = 'GET'
    ) -> Optional[str]:
        """
        Generate a presigned URL for temporary access
        
        Args:
            s3_key: S3 key of the file
            expiration: URL expiration time in seconds (default 1 hour)
            http_method: HTTP method (GET, PUT, etc.)
        
        Returns:
            Presigned URL or None if failed
        """
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return None
        
        try:
            if http_method == 'GET':
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.s3_bucket_name,
                        'Key': s3_key
                    },
                    ExpiresIn=expiration
                )
            elif http_method == 'PUT':
                url = self.s3_client.generate_presigned_url(
                    'put_object',
                    Params={
                        'Bucket': self.s3_bucket_name,
                        'Key': s3_key
                    },
                    ExpiresIn=expiration
                )
            else:
                logger.error(f"Unsupported HTTP method: {http_method}")
                return None
            
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
    
    def delete_file(self, s3_key: str) -> bool:
        """Delete a file from S3"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False
        
        try:
            self.s3_client.delete_object(
                Bucket=self.s3_bucket_name,
                Key=s3_key
            )
            logger.info(f"File deleted successfully: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
    
    def delete_files(self, s3_keys: list) -> bool:
        """Delete multiple files from S3"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False
        
        try:
            objects = [{'Key': key} for key in s3_keys]
            self.s3_client.delete_objects(
                Bucket=self.s3_bucket_name,
                Delete={'Objects': objects}
            )
            logger.info(f"Deleted {len(s3_keys)} files successfully")
            return True
        except ClientError as e:
            logger.error(f"Error deleting files from S3: {e}")
            return False
    
    def list_files(
        self,
        prefix: str = '',
        max_keys: int = 1000
    ) -> list:
        """List files in S3 bucket with given prefix"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            if 'Contents' not in response:
                return []
            
            files = []
            for obj in response['Contents']:
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })
            
            return files
        except ClientError as e:
            logger.error(f"Error listing files from S3: {e}")
            return []
    
    def file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False
        
        try:
            self.s3_client.head_object(
                Bucket=self.s3_bucket_name,
                Key=s3_key
            )
            return True
        except ClientError:
            return False
    
    def get_file_metadata(self, s3_key: str) -> Optional[Dict]:
        """Get file metadata from S3"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return None
        
        try:
            response = self.s3_client.head_object(
                Bucket=self.s3_bucket_name,
                Key=s3_key
            )
            
            return {
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {}),
                'etag': response.get('ETag')
            }
        except ClientError as e:
            logger.error(f"Error getting file metadata: {e}")
            return None
    
    def copy_file(
        self,
        source_key: str,
        destination_key: str
    ) -> bool:
        """Copy a file within S3"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False
        
        try:
            copy_source = {
                'Bucket': self.s3_bucket_name,
                'Key': source_key
            }
            
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.s3_bucket_name,
                Key=destination_key
            )
            
            logger.info(f"File copied: {source_key} -> {destination_key}")
            return True
        except ClientError as e:
            logger.error(f"Error copying file in S3: {e}")
            return False
    
    def upload_data_export(
        self,
        export_data: bytes,
        user_id: str,
        export_id: str
    ) -> Optional[str]:
        """Upload data export to S3"""
        try:
            s3_key = f"exports/{user_id}/{export_id}.json"
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket_name,
                Key=s3_key,
                Body=export_data,
                ContentType='application/json',
                Metadata={
                    'user_id': user_id,
                    'export_id': export_id,
                    'created_at': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Data export uploaded: {s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"Error uploading data export: {e}")
            return None
    
    def cleanup_old_exports(self, days: int = 7) -> int:
        """Delete exports older than specified days"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return 0
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            files = self.list_files(prefix='exports/')
            
            old_files = [
                f['key'] for f in files
                if f['last_modified'].replace(tzinfo=None) < cutoff_date
            ]
            
            if old_files:
                self.delete_files(old_files)
                logger.info(f"Cleaned up {len(old_files)} old exports")
                return len(old_files)
            
            return 0
        except Exception as e:
            logger.error(f"Error cleaning up old exports: {e}")
            return 0


# Global S3 service instance
s3_service = S3Service()
