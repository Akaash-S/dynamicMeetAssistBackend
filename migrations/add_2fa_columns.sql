-- Add Two-Factor Authentication columns to users table

-- Add 2FA enabled flag
ALTER TABLE users ADD COLUMN two_factor_enabled INTEGER DEFAULT 0;

-- Add 2FA method (2fa_email, 2fa_sms, 2fa_app)
ALTER TABLE users ADD COLUMN two_factor_method TEXT;

-- Add 2FA secret for authenticator app
ALTER TABLE users ADD COLUMN two_factor_secret TEXT;

-- Add phone number for SMS 2FA
ALTER TABLE users ADD COLUMN two_factor_phone TEXT;

-- Create data_exports table for tracking export requests
CREATE TABLE IF NOT EXISTS data_exports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    export_id TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_data_exports_export_id ON data_exports(export_id);
CREATE INDEX IF NOT EXISTS idx_data_exports_expires_at ON data_exports(expires_at);
CREATE INDEX IF NOT EXISTS idx_users_two_factor ON users(two_factor_enabled, two_factor_method);
