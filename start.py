#!/usr/bin/env python3
"""
Startup script for AI Meeting Assistant Backend
"""
import os
import sys
from app import create_app

def main():
    """Start the Flask application"""
    try:
        # Create the Flask app
        app = create_app()
        
        # Get configuration from environment
        port = int(os.environ.get('PORT', 5000))
        debug_mode = os.environ.get('FLASK_ENV') == 'development'
        host = os.environ.get('HOST', '0.0.0.0')
        
        print(f"🚀 Starting AI Meeting Assistant Backend...")
        print(f"📍 Host: {host}")
        print(f"🔌 Port: {port}")
        print(f"🐛 Debug: {debug_mode}")
        print(f"🌐 Health Check: http://{host}:{port}/api/health")
        print(f"📚 API Documentation: http://{host}:{port}/")
        
        # Start the server
        app.run(
            debug=debug_mode,
            host=host,
            port=port,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
