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
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.min_connections,
                maxconn=self.max_connections,
                dsn=self.connection_string,
                cursor_factory=RealDictCursor
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
            
            return self._pool.getconn()
        except Exception as e:
            print(f"[ERROR] Failed to get connection from pool: {e}")
            # Fallback to direct connection if pool fails
            return psycopg2.connect(
                self.connection_string,
                cursor_factory=RealDictCursor
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
        """Execute a query and return results"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    if query.strip().upper().startswith('SELECT'):
                        return cursor.fetchall()
                    conn.commit()
                    return cursor.rowcount
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
    
    # Users table
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        firebase_uid VARCHAR(255) UNIQUE NOT NULL,
        email VARCHAR(255) NOT NULL,
        name VARCHAR(255) NOT NULL,
        email_notifications BOOLEAN DEFAULT TRUE,
        in_app_notifications BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        db.execute_query(create_users_table)
        db.execute_query(create_meetings_table)
        db.execute_query(create_timeline_table)
        db.execute_query(create_tasks_table)
        db.execute_query(create_processing_status_table)
        db.execute_query(create_notifications_table)
        print("[SUCCESS] Database tables initialized successfully")
    except Exception as e:
        print(f"[ERROR] Error initializing database: {e}")
        raise e
