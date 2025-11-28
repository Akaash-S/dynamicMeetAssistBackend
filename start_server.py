#!/usr/bin/env python3
"""
Backend Server Startup Script
Starts the Dynamic Meeting Assistant backend server with proper configuration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_requirements():
    """Check if all required packages are installed"""
    required_packages = [
        'flask',
        'flask_cors',
        'psycopg2',
        'python-dotenv',
        'bcrypt'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_environment():
    """Check if required environment variables are set"""
    required_vars = [
        'RDS_HOST',
        'RDS_USER',
        'RDS_PASSWORD',
        'RDS_DATABASE',
        'PORT',
        'ADMIN_EMAIL',
        'ADMIN_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Add these variables to backend/.env file")
        return False
    
    return True

def main():
    """Main startup function"""
    print("\n" + "=" * 60)
    print("🚀 Dynamic Meeting Assistant Backend Server")
    print("=" * 60 + "\n")
    
    # Check requirements
    print("📦 Checking requirements...")
    if not check_requirements():
        sys.exit(1)
    print("✅ All required packages installed\n")
    
    # Check environment
    print("🔧 Checking environment configuration...")
    if not check_environment():
        sys.exit(1)
    print("✅ Environment configured correctly\n")
    
    # Get configuration
    port = int(os.getenv('PORT', 8000))
    flask_env = os.getenv('FLASK_ENV', 'development')
    
    print("📋 Server Configuration:")
    print(f"   Port: {port}")
    print(f"   Environment: {flask_env}")
    print(f"   Database: {'✅ Configured' if os.getenv('RDS_HOST') else '❌ Not configured'}")
    print(f"   Storage: {'✅ Configured' if os.getenv('S3_BUCKET_NAME') else '❌ Not configured'}")
    print(f"   Admin: {os.getenv('ADMIN_EMAIL', 'Not configured')}")
    print("\n" + "=" * 60 + "\n")
    
    # Import and run app
    try:
        from app import app
        
        print(f"🌐 Starting server on http://0.0.0.0:{port}")
        print(f"   Local: http://localhost:{port}")
        print(f"   Health Check: http://localhost:{port}/api/health")
        print(f"   Admin Login: http://localhost:{port}/api/admin/auth/login")
        print("\n💡 Press CTRL+C to stop the server\n")
        print("=" * 60 + "\n")
        
        # Run the app
        app.run(
            debug=(flask_env == 'development'),
            host='0.0.0.0',
            port=port
        )
        
    except Exception as e:
        print(f"\n❌ Failed to start server: {e}")
        print("\n💡 Check the error message above and fix the issue")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
        sys.exit(0)
