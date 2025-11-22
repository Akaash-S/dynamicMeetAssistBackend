"""Simple test to check if admin blueprints can be imported and registered"""
from flask import Flask

print("Creating Flask app...")
app = Flask(__name__)

print("Importing admin blueprints...")
try:
    from routes.admin_auth import admin_auth_bp
    print(f"[OK] admin_auth_bp imported: {admin_auth_bp}")
except Exception as e:
    print(f"[FAIL] Failed to import admin_auth_bp: {e}")
    import traceback
    traceback.print_exc()

try:
    from routes.admin_users import admin_users_bp
    print(f"[OK] admin_users_bp imported: {admin_users_bp}")
except Exception as e:
    print(f"[FAIL] Failed to import admin_users_bp: {e}")
    import traceback
    traceback.print_exc()

print("\nRegistering blueprints...")
try:
    app.register_blueprint(admin_auth_bp, url_prefix='/api/admin/auth')
    print("[OK] admin_auth_bp registered")
except Exception as e:
    print(f"[FAIL] Failed to register admin_auth_bp: {e}")

try:
    app.register_blueprint(admin_users_bp, url_prefix='/api/admin/users')
    print("[OK] admin_users_bp registered")
except Exception as e:
    print(f"[FAIL] Failed to register admin_users_bp: {e}")

print("\nRegistered routes:")
for rule in app.url_map.iter_rules():
    if 'admin' in str(rule):
        print(f"  {rule.methods} {rule}")
