## Two-Factor Authentication & Email Services Setup Guide

## Overview

This guide covers the complete setup of:
1. Two-Factor Authentication (Email, SMS, Authenticator App)
2. Enhanced Email Services
3. Data Export Functionality

## Prerequisites

### Required Python Packages

Add to `requirements.txt`:
```
pyotp==2.9.0
qrcode==7.4.2
Pillow==10.1.0
twilio==8.10.0
```

Install:
```bash
pip install pyotp qrcode Pillow twilio
```

## Environment Variables

Add to your `.env` file:

```env
# Email Configuration (existing)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
FROM_NAME=AI Meeting Assistant

# Twilio Configuration (for SMS 2FA)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# App Configuration
APP_NAME=AI Meeting Assistant
APP_ISSUER=AI Meeting Assistant
BACKEND_URL=https://dynamicmeetassistbackend-1.onrender.com
```

## Setup Steps

### 1. Database Migration

Run the migration to add 2FA columns:

```bash
cd backend
sqlite3 database.db < migrations/add_2fa_columns.sql
```

Or manually execute:
```sql
ALTER TABLE users ADD COLUMN two_factor_enabled INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN two_factor_method TEXT;
ALTER TABLE users ADD COLUMN two_factor_secret TEXT;
ALTER TABLE users ADD COLUMN two_factor_phone TEXT;

CREATE TABLE IF NOT EXISTS data_exports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    export_id TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### 2. Register Routes in app.py

Add to `backend/app.py`:

```python
from routes.two_factor_auth import two_factor_auth_bp
from routes.data_export import data_export_bp

# Register blueprints
app.register_blueprint(two_factor_auth_bp, url_prefix='/api')
app.register_blueprint(data_export_bp, url_prefix='/api')
```

### 3. Email Service Setup

#### Gmail Setup (Recommended for Development)

1. Enable 2-Step Verification in your Google Account
2. Generate an App Password:
   - Go to Google Account → Security → 2-Step Verification → App passwords
   - Select "Mail" and "Other (Custom name)"
   - Copy the generated password
3. Add to `.env`:
   ```env
   EMAIL_ADDRESS=your-email@gmail.com
   EMAIL_PASSWORD=your-16-char-app-password
   ```

#### Other SMTP Providers

**SendGrid:**
```env
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
EMAIL_ADDRESS=apikey
EMAIL_PASSWORD=your-sendgrid-api-key
```

**Mailgun:**
```env
SMTP_SERVER=smtp.mailgun.org
SMTP_PORT=587
EMAIL_ADDRESS=postmaster@your-domain.mailgun.org
EMAIL_PASSWORD=your-mailgun-password
```

### 4. SMS Setup (Twilio)

1. Create a Twilio account at https://www.twilio.com/
2. Get your Account SID and Auth Token from the dashboard
3. Purchase a phone number or use the trial number
4. Add to `.env`:
   ```env
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+1234567890
   ```

**Note:** Twilio trial accounts can only send to verified numbers.

### 5. Test the Setup

#### Test Email 2FA:
```bash
curl -X POST https://dynamicmeetassistbackend-1.onrender.com/api/2fa/email/send \
  -H "Content-Type: application/json" \
  -H "X-User-ID: your-user-id" \
  -d '{"email": "user@example.com"}'
```

#### Test SMS 2FA:
```bash
curl -X POST https://dynamicmeetassistbackend-1.onrender.com/api/2fa/sms/send \
  -H "Content-Type: application/json" \
  -H "X-User-ID: your-user-id" \
  -d '{"phoneNumber": "+1234567890"}'
```

#### Test Authenticator App Setup:
```bash
curl -X POST https://dynamicmeetassistbackend-1.onrender.com/api/2fa/app/setup \
  -H "X-User-ID: your-user-id"
```

## API Endpoints

### Email 2FA
- `POST /api/2fa/email/send` - Send verification code
- `POST /api/2fa/email/verify` - Verify code and enable 2FA

### SMS 2FA
- `POST /api/2fa/sms/send` - Send verification code
- `POST /api/2fa/sms/verify` - Verify code and enable 2FA

### Authenticator App 2FA
- `POST /api/2fa/app/setup` - Generate QR code and secret
- `POST /api/2fa/app/verify` - Verify code and enable 2FA

### General 2FA
- `GET /api/2fa/status` - Get 2FA status
- `POST /api/2fa/disable` - Disable 2FA

### Data Export
- `POST /api/export-data` - Request data export
- `GET /api/download-export/:id` - Download export file

## Email Templates

The email service includes templates for:

1. **2FA Verification Code** - Large, easy-to-read code
2. **2FA Enabled Notification** - Confirmation email
3. **Data Export Ready** - Download link with expiration
4. **Meeting Processed** - Meeting completion notification
5. **Task Assignment** - Task notification
6. **Calendar Sync** - Sync confirmation
7. **Feature Updates** - New feature announcements
8. **Weekly Summary** - Activity summary

## Security Best Practices

### 2FA
1. **Code Expiration**: Codes expire after 10 minutes
2. **Rate Limiting**: Max 5 verification attempts
3. **Secure Storage**: Secrets encrypted in database
4. **TOTP Window**: 1-window tolerance for time drift

### Email
1. **App Passwords**: Never use actual email password
2. **TLS/SSL**: Always use encrypted connections
3. **Rate Limiting**: Prevent email spam
4. **Validation**: Verify email addresses

### SMS
1. **Phone Validation**: Verify phone number format
2. **Cost Control**: Monitor SMS usage
3. **Verified Numbers**: Use Twilio verified numbers in trial

### Data Export
1. **Expiration**: Links expire after 24 hours
2. **Authentication**: Require user authentication
3. **Cleanup**: Automatically delete expired files
4. **Encryption**: Consider encrypting export files

## Production Considerations

### Email Service
- Use a dedicated email service (SendGrid, Mailgun, AWS SES)
- Implement email queue for reliability
- Monitor delivery rates
- Handle bounces and complaints

### SMS Service
- Monitor costs (SMS can be expensive)
- Implement fallback to email
- Consider regional SMS providers
- Handle delivery failures

### 2FA Storage
- Use Redis for temporary codes (instead of in-memory)
- Encrypt 2FA secrets in database
- Implement backup codes
- Add recovery options

### Data Export
- Use background jobs for large exports
- Store exports in S3 or similar
- Implement compression
- Add export history

## Troubleshooting

### Email Not Sending
1. Check SMTP credentials
2. Verify app password (not regular password)
3. Check firewall/port 587
4. Enable "Less secure app access" if needed
5. Check spam folder

### SMS Not Sending
1. Verify Twilio credentials
2. Check phone number format (+1234567890)
3. Verify recipient number (trial accounts)
4. Check Twilio balance
5. Review Twilio logs

### QR Code Not Generating
1. Ensure pyotp and qrcode are installed
2. Check Pillow installation
3. Verify image generation permissions
4. Check base64 encoding

### 2FA Verification Failing
1. Check code expiration (10 minutes)
2. Verify code format (6 digits)
3. Check attempt limit (5 max)
4. Ensure correct identifier (email/phone)

## Monitoring

### Metrics to Track
- 2FA enrollment rate
- 2FA method distribution
- Email delivery rate
- SMS delivery rate
- Failed verification attempts
- Data export requests

### Logging
```python
logger.info(f"2FA enabled: user={user_id}, method={method}")
logger.warning(f"Failed 2FA attempt: user={user_id}")
logger.error(f"Email send failed: {error}")
```

## Maintenance Tasks

### Periodic Cleanup (Run Daily)
```bash
# Cleanup expired verification codes
curl -X POST https://dynamicmeetassistbackend-1.onrender.com/api/2fa/cleanup

# Cleanup expired exports
curl -X POST https://dynamicmeetassistbackend-1.onrender.com/api/cleanup-exports
```

### Database Maintenance
```sql
-- Remove old export records
DELETE FROM data_exports WHERE expires_at < datetime('now', '-7 days');

-- Check 2FA adoption
SELECT two_factor_method, COUNT(*) 
FROM users 
WHERE two_factor_enabled = 1 
GROUP BY two_factor_method;
```

## Testing Checklist

- [ ] Email 2FA code delivery
- [ ] Email 2FA code verification
- [ ] SMS 2FA code delivery
- [ ] SMS 2FA code verification
- [ ] Authenticator app QR code generation
- [ ] Authenticator app code verification
- [ ] 2FA status retrieval
- [ ] 2FA disable functionality
- [ ] Data export request
- [ ] Data export download
- [ ] Email template rendering
- [ ] Code expiration
- [ ] Rate limiting
- [ ] Error handling

## Support

For issues:
1. Check logs in `backend/logs/`
2. Verify environment variables
3. Test SMTP/Twilio connectivity
4. Review database schema
5. Check API responses

## Next Steps

1. ✅ Install required packages
2. ✅ Configure environment variables
3. ✅ Run database migrations
4. ✅ Register routes in app.py
5. ✅ Test each 2FA method
6. ✅ Test email delivery
7. ✅ Test data export
8. ✅ Deploy to production
9. ⏳ Monitor and optimize

Your 2FA and email services are now ready for production! 🔐📧
