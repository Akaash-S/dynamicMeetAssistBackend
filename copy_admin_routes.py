"""
Copy admin routes to backend/admin/routes directory
"""
import os
import shutil

def copy_admin_routes():
    print("=" * 60)
    print("COPYING ADMIN ROUTES")
    print("=" * 60)
    print()
    
    # Create directories
    admin_dir = "backend/admin"
    routes_dir = "backend/admin/routes"
    
    os.makedirs(admin_dir, exist_ok=True)
    os.makedirs(routes_dir, exist_ok=True)
    print("✅ Created directories")
    
    # Admin route files to copy
    admin_files = [
        "admin_auth.py",
        "admin_users.py",
        "admin_issues.py",
        "admin_payments.py",
        "admin_notifications.py"
    ]
    
    print()
    print("Copying files...")
    
    for filename in admin_files:
        source = f"backend/routes/{filename}"
        dest = f"backend/admin/routes/{filename}"
        
        if os.path.exists(source):
            shutil.copy2(source, dest)
            print(f"  ✅ Copied {filename}")
        else:
            print(f"  ❌ Not found: {filename}")
    
    print()
    print("=" * 60)
    print("✅ Admin routes copied successfully!")
    print("=" * 60)
    print()
    print("Next step: Restart backend server")
    print("  python backend/app.py")
    print()

if __name__ == '__main__':
    copy_admin_routes()
