"""
Register TOTP Blueprint in app.py
Automatically adds the TOTP authentication blueprint
"""

import os
import re


def register_totp_blueprint():
    """Add TOTP blueprint registration to app.py"""
    
    print("\n" + "="*70)
    print("Registering TOTP Blueprint in app.py")
    print("="*70)
    
    app_path = os.path.join(os.path.dirname(__file__), 'app.py')
    
    if not os.path.exists(app_path):
        print("\n❌ app.py not found!")
        return False
    
    # Read app.py
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already registered
    if 'totp_auth_bp' in content:
        print("\n✅ TOTP blueprint already registered!")
        return True
    
    # Create backup
    backup_path = app_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n💾 Backup created: {backup_path}")
    
    # Find the import section
    import_pattern = r'(from routes\.google_calendar import google_calendar_bp)'
    import_replacement = r'\1\nfrom routes.totp_auth import totp_auth_bp'
    
    if re.search(import_pattern, content):
        content = re.sub(import_pattern, import_replacement, content)
        print("  ✅ Added TOTP import")
    else:
        print("  ⚠ Could not find import section, adding manually...")
        # Add after other route imports
        content = content.replace(
            'from routes.google_calendar import google_calendar_bp',
            'from routes.google_calendar import google_calendar_bp\nfrom routes.totp_auth import totp_auth_bp'
        )
    
    # Find the blueprint registration section
    register_pattern = r'(app\.register_blueprint\(google_calendar_bp, url_prefix=\'/api/calendar\'\))'
    register_replacement = r'\1\n    app.register_blueprint(totp_auth_bp, url_prefix=\'/api\')'
    
    if re.search(register_pattern, content):
        content = re.sub(register_pattern, register_replacement, content)
        print("  ✅ Added TOTP blueprint registration")
    else:
        print("  ⚠ Could not find registration section, adding manually...")
        # Add after google_calendar_bp registration
        content = content.replace(
            "app.register_blueprint(google_calendar_bp, url_prefix='/api/calendar')",
            "app.register_blueprint(google_calendar_bp, url_prefix='/api/calendar')\n    app.register_blueprint(totp_auth_bp, url_prefix='/api')"
        )
    
    # Write updated content
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ TOTP blueprint registered successfully!")
    print("\nAdded routes:")
    print("  • POST /api/2fa/setup")
    print("  • POST /api/2fa/verify")
    print("  • POST /api/2fa/validate")
    print("  • GET /api/2fa/status")
    print("  • POST /api/2fa/disable")
    print("  • POST /api/2fa/backup-codes")
    
    return True


if __name__ == "__main__":
    if register_totp_blueprint():
        print("\n" + "="*70)
        print("✅ Success! TOTP blueprint is now registered.")
        print("="*70)
        print("\nNext steps:")
        print("  1. Run: python add_2fa_columns.py")
        print("  2. Restart your server: python app.py")
        print("  3. Test 2FA endpoints")
    else:
        print("\n❌ Failed to register TOTP blueprint")
        exit(1)
