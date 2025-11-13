@echo off
echo ========================================
echo Complete AWS Migration Script
echo ========================================
echo.

echo Step 1: Analyzing current backend setup...
python migrate_backend_to_aws.py
echo.

echo Step 2: Registering TOTP blueprint...
python register_totp_blueprint.py
echo.

echo Step 3: Adding 2FA columns to database...
python add_2fa_columns.py
echo.

echo ========================================
echo Migration Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Update your .env file with AWS credentials
echo 2. Restart your backend server
echo 3. Test the endpoints
echo.
pause
