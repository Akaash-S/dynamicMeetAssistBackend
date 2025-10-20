import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import os
import threading
from contextlib import contextmanager

class Database:
    def __init__(self):
        self.connection_string = os.getenv('NEON_DATABASE_URL')
        if not self.connection_string:
            raise ValueError("NEON_DATABASE_URL environment variable is required")
        
        # Connection pool configuration
        self.min_connections = int(os.getenv('DB_MIN_CONNECTIONS', 1))
        self.max_connections = int(os.getenv('DB_MAX_CONNECTIONS', 20))
        
        # Initialize connection pool
        self._pool = None
        self._pool_lock = threading.Lock()
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool"""
        try:
            # Connection tuning for managed Postgres (Neon/Render): keepalives + SSL
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.min_connections,
                maxconn=self.max_connections,
                dsn=self.connection_string,
                cursor_factory=RealDictCursor,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
                sslmode='require'
            )
            print(f"[SUCCESS] Database connection pool initialized: {self.min_connections}-{self.max_connections} connections")
        except Exception as e:
            print(f"[ERROR] Failed to initialize connection pool: {e}")
            raise e
    
    def _get_connection_from_pool(self):
        """Get connection from pool with error handling"""
        try:
            if self._pool is None:
                with self._pool_lock:
                    if self._pool is None:
                        self._initialize_pool()
            conn = self._pool.getconn()
            # Replace closed or broken connections
            if getattr(conn, 'closed', 0):
                try:
                    conn.close()
                except Exception:
                    pass
                return psycopg2.connect(
                    self.connection_string,
                    cursor_factory=RealDictCursor
                )
            return conn
        except Exception as e:
            print(f"[ERROR] Failed to get connection from pool: {e}")
            # Fallback to direct connection if pool fails
            return psycopg2.connect(
                self.connection_string,
                cursor_factory=RealDictCursor,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
                sslmode='require'
            )
    
    def _return_connection_to_pool(self, conn):
        """Return connection to pool"""
        try:
            if self._pool and conn:
                self._pool.putconn(conn)
        except Exception as e:
            print(f"[ERROR] Failed to return connection to pool: {e}")
            # If pool return fails, close connection directly
            if conn:
                conn.close()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections with connection pooling"""
        conn = None
        try:
            conn = self._get_connection_from_pool()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self._return_connection_to_pool(conn)
    
    def execute_query(self, query, params=None):
        """Execute a query and return results with single retry on closed connections"""
        def _run():
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    if query.strip().upper().startswith('SELECT'):
                        return cursor.fetchall()
                    conn.commit()
                    return cursor.rowcount
        try:
            return _run()
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            msg = str(e).lower()
            if 'closed' in msg or 'server closed the connection' in msg or 'connection already closed' in msg:
                print('[WARN] Connection closed detected. Reinitializing pool and retrying once...')
                with self._pool_lock:
                    try:
                        if self._pool:
                            self._pool.closeall()
                    except Exception:
                        pass
                    self._initialize_pool()
                return _run()
            print(f"[ERROR] Database operational/interface error: {e}")
            print(f"[ERROR] Query: {query}")
            print(f"[ERROR] Params: {params}")
            raise e
        except psycopg2.Error as e:
            print(f"[ERROR] Database error: {e}")
            print(f"[ERROR] Query: {query}")
            print(f"[ERROR] Params: {params}")
            raise e
        except Exception as e:
            print(f"[ERROR] Unexpected error in execute_query: {e}")
            print(f"[ERROR] Query: {query}")
            print(f"[ERROR] Params: {params}")
            raise e
    
    def execute_many(self, query, params_list):
        """Execute multiple queries with different parameters"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
    
    def get_pool_status(self):
        """Get connection pool status for monitoring"""
        try:
            if self._pool:
                # Note: psycopg2 doesn't provide direct pool status methods
                # This is a basic implementation
                return {
                    'min_connections': self.min_connections,
                    'max_connections': self.max_connections,
                    'pool_initialized': True,
                    'pool_available': self._pool is not None
                }
            else:
                return {
                    'min_connections': self.min_connections,
                    'max_connections': self.max_connections,
                    'pool_initialized': False,
                    'pool_available': False
                }
        except Exception as e:
            return {
                'error': str(e),
                'pool_initialized': False,
                'pool_available': False
            }
    
    def close_pool(self):
        """Close all connections in the pool"""
        try:
            if self._pool:
                self._pool.closeall()
                print("[SUCCESS] Database connection pool closed")
        except Exception as e:
            print(f"[ERROR] Error closing connection pool: {e}")
    
    def test_connection(self):
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result is not None
        except Exception as e:
            print(f"[ERROR] Database connection test failed: {e}")
            return False

# Global database instance
db = Database()

def init_db():
    """Initialize database tables"""
    # Ensure required extensions (for gen_random_uuid)
    create_extensions = """
    CREATE EXTENSION IF NOT EXISTS pgcrypto;
    """
    
    # Users table - Updated for dual authentication support
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        firebase_uid VARCHAR(255) UNIQUE,
        google_oauth_id VARCHAR(255) UNIQUE,
        email VARCHAR(255) NOT NULL,
        name VARCHAR(255) NOT NULL,
        auth_provider VARCHAR(50) DEFAULT 'firebase', -- 'firebase' or 'google_oauth'
        google_access_token TEXT,
        google_refresh_token TEXT,
        google_token_expires_at TIMESTAMP,
        email_notifications BOOLEAN DEFAULT TRUE,
        in_app_notifications BOOLEAN DEFAULT TRUE,
        google_calendar_enabled BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT users_auth_check CHECK (
            (firebase_uid IS NOT NULL) OR (google_oauth_id IS NOT NULL)
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
    
    # Notifications table for detailed notification settings and history
    create_notifications_table = """
    CREATE TABLE IF NOT EXISTS notifications (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        type VARCHAR(50) NOT NULL, -- 'meeting_summary', 'task_reminder', 'system_alert'
        title VARCHAR(255) NOT NULL,
        message TEXT NOT NULL,
        email_sent BOOLEAN DEFAULT FALSE,
        email_sent_at TIMESTAMP,
        read_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        db.execute_query(create_extensions)
        db.execute_query(create_users_table)
        db.execute_query(create_meetings_table)
        db.execute_query(create_timeline_table)
        db.execute_query(create_tasks_table)
        db.execute_query(create_processing_status_table)
        db.execute_query(create_notifications_table)
        
        # Run migration for existing users
        migrate_existing_users()
        
        print("[SUCCESS] Database tables initialized successfully")
    except Exception as e:
        print(f"[ERROR] Error initializing database: {e}")
        raise e

def migrate_existing_users():
    """Migrate existing users to support dual authentication"""
    try:
        # Check if new columns exist, if not add them
        migration_queries = [
            # Add new columns if they don't exist
            """
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='google_oauth_id') THEN
                    ALTER TABLE users ADD COLUMN google_oauth_id VARCHAR(255) UNIQUE;
                END IF;
            END $$;
            """,
            """
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='auth_provider') THEN
                    ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'firebase';
                END IF;
            END $$;
            """,
            """
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='google_access_token') THEN
                    ALTER TABLE users ADD COLUMN google_access_token TEXT;
                END IF;
            END $$;
            """,
            """
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='google_refresh_token') THEN
                    ALTER TABLE users ADD COLUMN google_refresh_token TEXT;
                END IF;
            END $$;
            """,
            """
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='google_token_expires_at') THEN
                    ALTER TABLE users ADD COLUMN google_token_expires_at TIMESTAMP;
                END IF;
            END $$;
            """,
            """
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='google_calendar_enabled') THEN
                    ALTER TABLE users ADD COLUMN google_calendar_enabled BOOLEAN DEFAULT FALSE;
                END IF;
            END $$;
            """,
            # Update existing users to have firebase as auth_provider
            """
            UPDATE users 
            SET auth_provider = 'firebase' 
            WHERE auth_provider IS NULL AND firebase_uid IS NOT NULL;
            """
        ]
        
        for query in migration_queries:
            db.execute_query(query)
        
        print("[SUCCESS] User table migration completed")
        
    except Exception as e:
        print(f"[WARNING] User table migration failed: {e}")
        # Don't fail the entire initialization if migration fails
