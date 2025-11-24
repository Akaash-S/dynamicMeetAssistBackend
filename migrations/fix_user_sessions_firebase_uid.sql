-- Fix user_sessions table to use firebase_uid instead of internal UUID
-- This allows the 2FA system to work correctly with Firebase authentication

-- Drop existing table
DROP TABLE IF EXISTS user_sessions CASCADE;

-- Recreate user_sessions table with firebase_uid
CREATE TABLE user_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,  -- Changed to VARCHAR to store Firebase UID
    session_type VARCHAR(50) NOT NULL DEFAULT 'active',
    logged_out_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Add foreign key constraint to firebase_uid
    CONSTRAINT fk_user_sessions_firebase_uid 
        FOREIGN KEY (user_id) 
        REFERENCES users(firebase_uid) 
        ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_created_at ON user_sessions(created_at);
CREATE INDEX idx_user_sessions_session_type ON user_sessions(session_type);

-- Add comments
COMMENT ON TABLE user_sessions IS 'Tracks user sessions for 2FA requirements';
COMMENT ON COLUMN user_sessions.user_id IS 'Firebase UID of the user';
COMMENT ON COLUMN user_sessions.session_type IS 'active, logged_out, or expired';
