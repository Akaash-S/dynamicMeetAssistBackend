-- Drop existing table if it exists (to ensure clean state)
DROP TABLE IF EXISTS user_sessions CASCADE;

-- Create user_sessions table for tracking logout/login and 2FA requirements
CREATE TABLE user_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_type VARCHAR(50) NOT NULL DEFAULT 'active',
    logged_out_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_created_at ON user_sessions(created_at);
CREATE INDEX idx_user_sessions_session_type ON user_sessions(session_type);

-- Add comments
COMMENT ON TABLE user_sessions IS 'Tracks user sessions for 2FA requirements';
COMMENT ON COLUMN user_sessions.session_type IS 'active, logged_out, or expired';
