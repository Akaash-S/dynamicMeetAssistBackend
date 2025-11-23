-- Add 2FA user preferences
ALTER TABLE users ADD COLUMN IF NOT EXISTS two_factor_inactivity_timeout INTEGER DEFAULT 600; -- 10 minutes in seconds
ALTER TABLE users ADD COLUMN IF NOT EXISTS two_factor_always_required BOOLEAN DEFAULT FALSE; -- Optional continuous 2FA
ALTER TABLE users ADD COLUMN IF NOT EXISTS two_factor_require_on_login BOOLEAN DEFAULT TRUE; -- Require on login after logout

-- Update existing users to have default values
UPDATE users 
SET two_factor_inactivity_timeout = 600,
    two_factor_always_required = FALSE,
    two_factor_require_on_login = TRUE
WHERE two_factor_inactivity_timeout IS NULL;
