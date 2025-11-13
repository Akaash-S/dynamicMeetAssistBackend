"""
Automatic AWS Setup Module
Automatically creates RDS tables and S3 buckets on server startup
"""

import os
import logging
from typing import Tuple, Dict

logger = logging.getLogger(__name__)


class AWSAutoSetup:
    """Handles automatic setup of AWS resources"""
    
    def __init__(self):
        self.setup_results = {
            'rds_tables': False,
            's3_bucket': False,
            'redis': False,
            'errors': []
        }
    
    def setup_all(self) -> Dict:
        """Run all setup tasks"""
        logger.info("Starting automatic AWS setup...")
        
        # Setup RDS tables
        self.setup_rds_tables()
        
        # Setup S3 bucket
        self.setup_s3_bucket()
        
        # Check Redis
        self.check_redis()
        
        # Log results
        self._log_results()
        
        return self.setup_results
    
    def setup_rds_tables(self) -> bool:
        """Create RDS tables if they don't exist"""
        try:
            from config.aws_rds_database import rds_db
            
            # Check if RDS is configured
            if not rds_db.connection_pool:
                logger.warning("RDS not configured - skipping table creation")
                self.setup_results['errors'].append("RDS not configured")
                return False
            
            logger.info("Checking RDS tables...")
            
            # Check if tables exist
            tables = rds_db.execute_query(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                """,
                fetch_all=True
            )
            
            existing_tables = [t['table_name'] for t in tables] if tables else []
            
            # Required tables
            required_tables = [
                'users', 'meetings', 'tasks', 'timeline_events',
                'notification_preferences', 'subscriptions', 'data_exports',
                'audit_logs', 'two_factor_attempts'
            ]
            
            missing_tables = [t for t in required_tables if t not in existing_tables]
            
            if not missing_tables:
                logger.info(f"✓ All {len(required_tables)} RDS tables exist")
                self.setup_results['rds_tables'] = True
                return True
            
            logger.info(f"Creating {len(missing_tables)} missing tables...")
            
            # Read and execute schema
            schema_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'migrations', 
                'rds_schema.sql'
            )
            
            if not os.path.exists(schema_path):
                logger.error(f"Schema file not found: {schema_path}")
                self.setup_results['errors'].append("Schema file not found")
                return False
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Execute the entire schema using psycopg2 directly
            # This properly handles multi-line statements, functions, and triggers
            logger.info("Executing schema file...")
            
            try:
                import psycopg2
                
                # Get a raw connection (not from pool)
                conn = psycopg2.connect(
                    host=rds_db.db_host,
                    port=rds_db.db_port,
                    database=rds_db.db_name,
                    user=rds_db.db_user,
                    password=rds_db.db_password,
                    sslmode=rds_db.db_ssl_mode
                )
                
                # Set autocommit to handle CREATE statements properly
                conn.autocommit = True
                cursor = conn.cursor()
                
                try:
                    # Execute the entire schema
                    cursor.execute(schema_sql)
                    logger.info("✓ Schema executed successfully")
                except Exception as e:
                    logger.error(f"Error executing schema: {e}")
                    # Try to continue anyway
                finally:
                    cursor.close()
                    conn.close()
                    
            except Exception as e:
                logger.error(f"Failed to execute schema: {e}")
                return False
            
            # Verify tables were created
            tables_after = rds_db.execute_query(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                """,
                fetch_all=True
            )
            
            existing_after = [t['table_name'] for t in tables_after] if tables_after else []
            still_missing = [t for t in required_tables if t not in existing_after]
            
            if still_missing:
                logger.warning(f"Some tables still missing: {still_missing}")
                self.setup_results['errors'].append(f"Missing tables: {still_missing}")
                self.setup_results['rds_tables'] = False
                return False
            
            logger.info(f"✓ Successfully created {len(missing_tables)} RDS tables")
            self.setup_results['rds_tables'] = True
            return True
            
        except ImportError:
            logger.warning("RDS module not available - skipping")
            self.setup_results['errors'].append("RDS module not available")
            return False
        except Exception as e:
            logger.error(f"Error setting up RDS tables: {e}")
            self.setup_results['errors'].append(f"RDS setup error: {str(e)}")
            return False
    
    def setup_s3_bucket(self) -> bool:
        """Create S3 bucket if it doesn't exist"""
        try:
            from services.aws_s3_service import s3_service
            import boto3
            from botocore.exceptions import ClientError
            
            bucket_name = os.getenv('S3_BUCKET_NAME')
            
            if not bucket_name:
                logger.warning("S3_BUCKET_NAME not configured - skipping bucket creation")
                self.setup_results['errors'].append("S3 not configured")
                return False
            
            logger.info(f"Checking S3 bucket: {bucket_name}")
            
            try:
                # Check if bucket exists
                s3_service.s3_client.head_bucket(Bucket=bucket_name)
                logger.info(f"✓ S3 bucket '{bucket_name}' already exists")
                self.setup_results['s3_bucket'] = True
                return True
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                if error_code == '404':
                    # Bucket doesn't exist, create it
                    logger.info(f"Creating S3 bucket: {bucket_name}")
                    
                    region = os.getenv('AWS_REGION', 'us-east-1')
                    
                    try:
                        if region == 'us-east-1':
                            # us-east-1 doesn't need LocationConstraint
                            s3_service.s3_client.create_bucket(
                                Bucket=bucket_name
                            )
                        else:
                            s3_service.s3_client.create_bucket(
                                Bucket=bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': region
                                }
                            )
                        
                        # Enable versioning (optional)
                        try:
                            s3_service.s3_client.put_bucket_versioning(
                                Bucket=bucket_name,
                                VersioningConfiguration={'Status': 'Enabled'}
                            )
                            logger.info("✓ Enabled bucket versioning")
                        except Exception as ve:
                            logger.warning(f"Could not enable versioning: {ve}")
                        
                        # Enable encryption
                        try:
                            s3_service.s3_client.put_bucket_encryption(
                                Bucket=bucket_name,
                                ServerSideEncryptionConfiguration={
                                    'Rules': [{
                                        'ApplyServerSideEncryptionByDefault': {
                                            'SSEAlgorithm': 'AES256'
                                        }
                                    }]
                                }
                            )
                            logger.info("✓ Enabled bucket encryption")
                        except Exception as ee:
                            logger.warning(f"Could not enable encryption: {ee}")
                        
                        # Block public access
                        try:
                            s3_service.s3_client.put_public_access_block(
                                Bucket=bucket_name,
                                PublicAccessBlockConfiguration={
                                    'BlockPublicAcls': True,
                                    'IgnorePublicAcls': True,
                                    'BlockPublicPolicy': True,
                                    'RestrictPublicBuckets': True
                                }
                            )
                            logger.info("✓ Blocked public access")
                        except Exception as pe:
                            logger.warning(f"Could not block public access: {pe}")
                        
                        # Create folder structure
                        audio_prefix = os.getenv('S3_AUDIO_PREFIX', 'audio/')
                        export_prefix = os.getenv('S3_EXPORT_PREFIX', 'exports/')
                        
                        for prefix in [audio_prefix, export_prefix]:
                            try:
                                s3_service.s3_client.put_object(
                                    Bucket=bucket_name,
                                    Key=prefix,
                                    Body=b''
                                )
                            except Exception:
                                pass  # Folders are optional
                        
                        logger.info(f"✓ Successfully created S3 bucket: {bucket_name}")
                        self.setup_results['s3_bucket'] = True
                        return True
                        
                    except ClientError as ce:
                        logger.error(f"Error creating S3 bucket: {ce}")
                        self.setup_results['errors'].append(f"S3 creation error: {str(ce)}")
                        return False
                
                elif error_code == '403':
                    logger.error(f"Access denied to bucket '{bucket_name}' - check IAM permissions")
                    self.setup_results['errors'].append("S3 access denied")
                    return False
                else:
                    logger.error(f"Error checking S3 bucket: {e}")
                    self.setup_results['errors'].append(f"S3 error: {str(e)}")
                    return False
                    
        except ImportError:
            logger.warning("S3 module not available - skipping")
            self.setup_results['errors'].append("S3 module not available")
            return False
        except Exception as e:
            logger.error(f"Error setting up S3 bucket: {e}")
            self.setup_results['errors'].append(f"S3 setup error: {str(e)}")
            return False
    
    def check_redis(self) -> bool:
        """Check if Redis is available"""
        try:
            import redis
            
            redis_host = os.getenv('REDIS_HOST', 'redis-14654.c212.ap-south-1-1.ec2.cloud.redislabs.com')
            redis_port = int(os.getenv('REDIS_PORT', 14654))
            
            r = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=os.getenv('REDIS_PASSWORD', None) or None,
                db=int(os.getenv('REDIS_DB', 0)),
                socket_connect_timeout=2
            )
            
            r.ping()
            logger.info("✓ Redis connection successful")
            self.setup_results['redis'] = True
            return True
            
        except ImportError:
            logger.warning("Redis module not installed")
            logger.warning("Install with: pip install redis")
            self.setup_results['errors'].append("Redis module not installed")
            return False
        except redis.ConnectionError:
            logger.warning(f"Redis not running on {redis_host}:{redis_port}")
            logger.warning("Start Redis with: redis-server")
            logger.warning("Or run: install_redis_windows.bat")
            logger.warning("2FA rate limiting will be disabled")
            self.setup_results['errors'].append(f"Redis not running")
            return False
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            logger.warning("2FA rate limiting will be disabled")
            self.setup_results['errors'].append(f"Redis not available: {str(e)}")
            return False
    
    def _log_results(self):
        """Log setup results"""
        logger.info("\n" + "="*60)
        logger.info("AWS Auto-Setup Results:")
        logger.info("="*60)
        logger.info(f"RDS Tables:  {'✓ Ready' if self.setup_results['rds_tables'] else '✗ Not Ready'}")
        logger.info(f"S3 Bucket:   {'✓ Ready' if self.setup_results['s3_bucket'] else '✗ Not Ready'}")
        logger.info(f"Redis Cache: {'✓ Ready' if self.setup_results['redis'] else '✗ Not Ready'}")
        
        if self.setup_results['errors']:
            logger.warning("\nWarnings/Errors:")
            for error in self.setup_results['errors']:
                logger.warning(f"  - {error}")
        
        logger.info("="*60 + "\n")


# Global instance
auto_setup = AWSAutoSetup()


def run_auto_setup() -> Dict:
    """Run automatic setup and return results"""
    return auto_setup.setup_all()


def get_setup_status() -> Dict:
    """Get current setup status"""
    return auto_setup.setup_results
