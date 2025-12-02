"""
AWS RDS Database Configuration
PostgreSQL database connection for production
"""

import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import logging
from contextlib import contextmanager
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class RDSDatabase:
    def __init__(self):
        self.db_host = os.getenv('RDS_HOST')
        self.db_port = os.getenv('RDS_PORT', '5432')
        self.db_name = os.getenv('RDS_DATABASE') or os.getenv('RDS_DB_NAME')
        self.db_user = os.getenv('RDS_USER')
        self.db_password = os.getenv('RDS_PASSWORD')
        self.db_ssl_mode = os.getenv('RDS_SSL_MODE', 'prefer')
        
        # Debug: Print what we loaded
        logger.info(f"🔍 RDS Config: host={self.db_host}, port={self.db_port}, db={self.db_name}, user={self.db_user}")
        
        # Connection pool settings
        self.min_connections = int(os.getenv('DB_POOL_MIN', '2'))
        self.max_connections = int(os.getenv('DB_POOL_MAX', '10'))
        
        self.connection_pool = None
        
        # Common connection kwargs so we reuse identical keepalive settings everywhere
        self._connection_kwargs = dict(
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            user=self.db_user,
            password=self.db_password,
            sslmode=self.db_ssl_mode,
            cursor_factory=RealDictCursor,
            connect_timeout=10,
            keepalives=1,           # Enable TCP keepalives
            keepalives_idle=60,     # Send probe after 60 seconds of idle time
            keepalives_interval=20, # Interval between probes is 20 seconds
            keepalives_count=5      # Number of failed probes before dropping connection
        )
        
        if all([self.db_host, self.db_name, self.db_user, self.db_password]):
            try:
                self._initialize_pool()
            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                # Don't raise - allow app to start but connection will fail on use
        else:
            logger.warning("⚠️  RDS database credentials not fully configured")
            logger.warning("   Missing one or more of: RDS_HOST, RDS_DATABASE, RDS_USER, RDS_PASSWORD")
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        try:
            logger.info(f"Initializing RDS connection pool to {self.db_host}:{self.db_port}/{self.db_name}")
            # TCP Keepalives prevent idle connections from being closed by network timeouts
            # This is critical for Render backend to prevent "SSL SYSCALL error: EOF detected"
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                self.min_connections,
                self.max_connections,
                **self._connection_kwargs
            )
            logger.info("✅ RDS connection pool initialized successfully")
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            logger.error(f"❌ RDS connection failed: {error_msg}")
            
            # Provide helpful error messages
            if "could not connect to server" in error_msg.lower():
                logger.error("   → Check if RDS instance is running and accessible")
                logger.error("   → Verify security group allows inbound traffic on port 5432")
            elif "password authentication failed" in error_msg.lower():
                logger.error("   → Check RDS_USER and RDS_PASSWORD in .env file")
            elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
                logger.error("   → Check RDS_DATABASE name in .env file")
            elif "timeout" in error_msg.lower():
                logger.error("   → Connection timeout - check network connectivity")
            
            self.connection_pool = None
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error initializing RDS connection pool: {e}")
            self.connection_pool = None
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        if not self.connection_pool:
            # Try to initialize if not already done
            logger.warning("Connection pool not initialized, attempting to initialize now...")
            self._initialize_pool()
            
        if not self.connection_pool:
            raise Exception("Database connection pool not initialized. Check RDS credentials in .env file.")
        
        conn = None
        try:
            conn = self.connection_pool.getconn()
            
            # Replace closed/broken connections
            if getattr(conn, 'closed', 0):
                logger.warning("Connection from pool was closed. Replacing with a new connection...")
                try:
                    conn.close()
                except Exception:
                    pass
                conn = psycopg2.connect(**self._connection_kwargs)
            
            yield conn
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, commit=False):
        """Get a cursor with automatic connection management"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = None, fetch_one=False, fetch_all=False):
        """Execute a query and return results (with automatic retry on closed connections)"""
        # Ensure pool is initialized
        if not self.connection_pool:
            logger.warning("Connection pool not initialized in execute_query, attempting to initialize...")
            self._initialize_pool()
        
        def _run_query():
            with self.get_cursor(commit=not (fetch_one or fetch_all)) as cursor:
                cursor.execute(query, params)
                
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    return cursor.rowcount
        
        try:
            return _run_query()
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            msg = str(e).lower()
            if any(keyword in msg for keyword in ['server closed the connection', 'connection already closed', 'closed the connection unexpectedly']):
                logger.warning("Database connection closed detected. Reinitializing pool and retrying...")
                try:
                    if self.connection_pool:
                        self.connection_pool.closeall()
                except Exception:
                    pass
                self._initialize_pool()
                return _run_query()
            logger.error(f"Operational/Interface error executing query: {e}")
            raise
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def execute_many(self, query: str, params_list: list):
        """Execute a query with multiple parameter sets"""
        try:
            with self.get_cursor(commit=True) as cursor:
                cursor.executemany(query, params_list)
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error executing batch query: {e}")
            raise
    
    def health_check(self):
        """Check database health and connection pool status"""
        try:
            if not self.connection_pool:
                return {
                    'status': 'unhealthy',
                    'error': 'Connection pool not initialized',
                    'configured': False
                }
            
            # Test a simple query
            result = self.execute_query("SELECT 1 as test", fetch_one=True)
            
            if result and result.get('test') == 1:
                # Get pool statistics
                pool_size = self.connection_pool._maxconn if hasattr(self.connection_pool, '_maxconn') else self.max_connections
                
                return {
                    'status': 'healthy',
                    'configured': True,
                    'connection_pool': {
                        'size': pool_size,
                        'min': self.min_connections,
                        'max': self.max_connections
                    },
                    'database': {
                        'host': self.db_host,
                        'port': self.db_port,
                        'name': self.db_name
                    }
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': 'Query test failed',
                    'configured': True
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'configured': True
            }
    
    def test_connection(self):
        """Test database connection (for compatibility with auth routes)"""
        try:
            # Simple query via connection directly to catch closed connections
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def close_all_connections(self):
        """Close all connections in the pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("All RDS connections closed")


# Global RDS database instance (lazy initialization)
_rds_db_instance = None

def get_rds_db():
    """Get or create the global RDS database instance"""
    global _rds_db_instance
    if _rds_db_instance is None:
        _rds_db_instance = RDSDatabase()
    return _rds_db_instance

# For backward compatibility, create instance on first access
class _RDSDBProxy:
    """Proxy to delay RDS database initialization until first use"""
    def __getattr__(self, name):
        return getattr(get_rds_db(), name)
    
    def __setattr__(self, name, value):
        return setattr(get_rds_db(), name, value)

rds_db = _RDSDBProxy()


def get_rds_connection():
    """Get RDS database connection (for compatibility)"""
    return rds_db.get_connection()


def get_rds_cursor(commit=False):
    """Get RDS database cursor (for compatibility)"""
    return rds_db.get_cursor(commit=commit)



def init_rds_db():
    """Initialize RDS database tables"""
    print("\n" + "="*70)
    print("Initializing RDS Database Tables")
    print("="*70)
    
    # Check if RDS is configured
    health = rds_db.health_check()
    if health['status'] != 'healthy':
        print(f"\n⚠️  WARNING: RDS database not healthy: {health.get('error', 'Unknown error')}")
        print("   Skipping table initialization...")
        return
    
    print(f"\n✅ RDS Connection: {health['database']['host']}")
    
    # Ensure required extensions
    create_extensions = """
    CREATE EXTENSION IF NOT EXISTS pgcrypto;
    """
    
    # Users table with 2FA support
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        firebase_uid VARCHAR(255) UNIQUE,
        google_oauth_id VARCHAR(255) UNIQUE,
        email VARCHAR(255) NOT NULL,
        name VARCHAR(255) NOT NULL,
        auth_provider VARCHAR(50) DEFAULT 'firebase',
        google_access_token TEXT,
        google_refresh_token TEXT,
        google_token_expires_at TIMESTAMP,
        email_notifications BOOLEAN DEFAULT TRUE,
        in_app_notifications BOOLEAN DEFAULT TRUE,
        google_calendar_enabled BOOLEAN DEFAULT FALSE,
        role VARCHAR(50) DEFAULT 'user',
        password_hash VARCHAR(255),
        last_login_at TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE,
        two_factor_enabled BOOLEAN DEFAULT FALSE,
        two_factor_method VARCHAR(50),
        two_factor_secret TEXT,
        backup_codes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT users_auth_check CHECK (
            (firebase_uid IS NOT NULL) OR (google_oauth_id IS NOT NULL) OR (password_hash IS NOT NULL)
        )
    );
    """
    
    # Meetings table
    create_meetings_table = """
    CREATE TABLE IF NOT EXISTS meetings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        title VARCHAR(255) NOT NULL,
        audio_url TEXT,
        transcript TEXT,
        summary TEXT,
        status VARCHAR(50) DEFAULT 'processing',
        file_size BIGINT,
        duration INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Timeline table
    create_timeline_table = """
    CREATE TABLE IF NOT EXISTS timeline (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
        timestamp_minutes DECIMAL(10,2) NOT NULL,
        event_type VARCHAR(50) NOT NULL,
        title VARCHAR(255) NOT NULL,
        content TEXT,
        participants TEXT[],
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Tasks table
    create_tasks_table = """
    CREATE TABLE IF NOT EXISTS tasks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        assigned_to VARCHAR(255),
        deadline TIMESTAMP,
        priority VARCHAR(20) DEFAULT 'medium',
        status VARCHAR(20) DEFAULT 'pending',
        calendar_event_id VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Processing status table
    create_processing_status_table = """
    CREATE TABLE IF NOT EXISTS processing_status (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
        step VARCHAR(50) NOT NULL,
        status VARCHAR(20) NOT NULL,
        progress INTEGER DEFAULT 0,
        error_message TEXT,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    );
    """
    
    # Notifications table
    create_notifications_table = """
    CREATE TABLE IF NOT EXISTS notifications (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        type VARCHAR(50) NOT NULL,
        title VARCHAR(255) NOT NULL,
        message TEXT NOT NULL,
        email_sent BOOLEAN DEFAULT FALSE,
        email_sent_at TIMESTAMP,
        read_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Admin tables
    create_admin_issues_table = """
    CREATE TABLE IF NOT EXISTS admin_issues (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        status VARCHAR(50) DEFAULT 'open',
        priority VARCHAR(20) DEFAULT 'medium',
        category VARCHAR(100),
        assigned_to VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        resolved_by VARCHAR(255)
    );
    """
    
    create_admin_payments_table = """
    CREATE TABLE IF NOT EXISTS admin_payments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        amount DECIMAL(10,2) NOT NULL,
        currency VARCHAR(3) DEFAULT 'USD',
        status VARCHAR(50) DEFAULT 'pending',
        payment_method VARCHAR(50),
        transaction_id VARCHAR(255),
        stripe_payment_intent_id VARCHAR(255),
        description VARCHAR(255),
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_admin_notifications_table = """
    CREATE TABLE IF NOT EXISTS admin_notifications (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        message TEXT NOT NULL,
        type VARCHAR(50) DEFAULT 'system',
        priority VARCHAR(20) DEFAULT 'normal',
        target_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        is_read BOOLEAN DEFAULT FALSE,
        created_by VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_admin_logs_table = """
    CREATE TABLE IF NOT EXISTS admin_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        admin_email VARCHAR(255) NOT NULL,
        action VARCHAR(100) NOT NULL,
        resource_type VARCHAR(50),
        resource_id VARCHAR(255),
        details TEXT,
        ip_address VARCHAR(45),
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        print("\n📝 Creating database tables...")
        
        rds_db.execute_query(create_extensions)
        print("  ✅ Extensions created")
        
        rds_db.execute_query(create_users_table)
        print("  ✅ Users table created")
        
        rds_db.execute_query(create_meetings_table)
        print("  ✅ Meetings table created")
        
        rds_db.execute_query(create_timeline_table)
        print("  ✅ Timeline table created")
        
        rds_db.execute_query(create_tasks_table)
        print("  ✅ Tasks table created")
        
        rds_db.execute_query(create_processing_status_table)
        print("  ✅ Processing status table created")
        
        rds_db.execute_query(create_notifications_table)
        print("  ✅ Notifications table created")
        
        rds_db.execute_query(create_admin_issues_table)
        print("  ✅ Admin issues table created")
        
        rds_db.execute_query(create_admin_payments_table)
        print("  ✅ Admin payments table created")
        
        rds_db.execute_query(create_admin_notifications_table)
        print("  ✅ Admin notifications table created")
        
        rds_db.execute_query(create_admin_logs_table)
        print("  ✅ Admin logs table created")
        
        print("\n✅ All RDS database tables initialized successfully!")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"Error initializing RDS database: {e}")
        print(f"\n❌ Error initializing RDS database: {e}")
        print("="*70 + "\n")
        raise e
