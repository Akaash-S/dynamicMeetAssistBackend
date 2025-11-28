-- Migration: Add chatbot tables for conversation management
-- Description: Creates tables for chatbot sessions and messages with proper indexes
-- Requirements: 2.1, 2.3

-- Create chatbot_sessions table
CREATE TABLE IF NOT EXISTS chatbot_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create chatbot_messages table
CREATE TABLE IF NOT EXISTS chatbot_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chatbot_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_chatbot_sessions_user_id ON chatbot_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_sessions_updated_at ON chatbot_sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chatbot_sessions_is_active ON chatbot_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_chatbot_messages_session_id ON chatbot_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_messages_created_at ON chatbot_messages(created_at DESC);

-- Add table comments for documentation
COMMENT ON TABLE chatbot_sessions IS 'Stores chatbot conversation sessions for each user';
COMMENT ON TABLE chatbot_messages IS 'Stores individual messages within chatbot sessions';

-- Add column comments
COMMENT ON COLUMN chatbot_sessions.user_id IS 'Reference to the user who owns this session';
COMMENT ON COLUMN chatbot_sessions.message_count IS 'Total number of messages in this session';
COMMENT ON COLUMN chatbot_sessions.is_active IS 'Whether this session is currently active';
COMMENT ON COLUMN chatbot_messages.role IS 'Message sender: user or assistant';
COMMENT ON COLUMN chatbot_messages.content IS 'The actual message content';
COMMENT ON COLUMN chatbot_messages.metadata IS 'Additional metadata like sources, actions executed, etc.';
