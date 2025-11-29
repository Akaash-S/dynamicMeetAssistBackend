-- Fix chatbot tables to use VARCHAR for user_id instead of UUID
-- This is needed because Firebase UIDs are not in UUID format

-- Drop foreign key constraints first
ALTER TABLE chatbot_sessions 
DROP CONSTRAINT IF EXISTS chatbot_sessions_user_id_fkey;

-- Change user_id column type to VARCHAR
ALTER TABLE chatbot_sessions 
ALTER COLUMN user_id TYPE VARCHAR(255);

-- Recreate foreign key constraint (optional, only if users table uses VARCHAR for id)
-- ALTER TABLE chatbot_sessions 
-- ADD CONSTRAINT chatbot_sessions_user_id_fkey 
-- FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Add index for better performance
CREATE INDEX IF NOT EXISTS idx_chatbot_sessions_user_id ON chatbot_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_messages_session_id ON chatbot_messages(session_id);

-- Verify the changes
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'chatbot_sessions' 
AND column_name = 'user_id';
