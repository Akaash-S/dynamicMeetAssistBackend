"""
Admin Backend Application
Separate Flask app for admin dashboard
Runs on port 8001 (different from client app on 8000)
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from backend
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from flask import Flask, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_admin_app():
    """Create and configure the admin Flask application"""
    app = Flask(__name__)
    
    # CORS configuration for admin app
    admin_origins = os.getenv('ADMIN_CORS_ORIGINS', 'http://localhost:5174').split(',')
    CORS(app, 
         resources={r"/api/*": {"origins": admin_origins}},
         supports_credentials=False,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    
    # Import and register admin routes
    import sys
    from pathlib import Path
    admin_routes_dir = Path(__file__).parent / 'routes'
    sys.path.insert(0, str(admin_routes_dir))
    
    from auth import admin_auth_bp
    from users import admin_users_bp
    from issues import admin_issues_bp
    from payments import admin_payments_bp
    from notifications import admin_notifications_bp
    
    app.register_blueprint(admin_auth_bp, url_prefix='/api/admin/auth')
    app.register_blueprint(admin_users_bp, url_prefix='/api/admin/users')
    app.register_blueprint(admin_issues_bp, url_prefix='/api/admin/issues')
    app.register_blueprint(admin_payments_bp, url_prefix='/api/admin/payments')
    app.register_blueprint(admin_notifications_bp, url_prefix='/api/admin/notifications')
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'ok',
            'service': 'Admin Backend API',
            'version': '1.0.0'
        }), 200
    
    # 404 handler
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404
    
    # 500 handler
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error', 'message': str(error)}), 500
    
    print("[ADMIN] Admin backend initialized successfully")
    print(f"[ADMIN] Registered {len(app.url_map._rules)} routes")
    
    return app

if __name__ == '__main__':
    app = create_admin_app()
    port = int(os.getenv('ADMIN_PORT', 8001))
    
    print("\n" + "=" * 60)
    print("[ADMIN] Admin Backend Server")
    print("=" * 60)
    print(f"[ADMIN] Starting on http://0.0.0.0:{port}")
    print(f"[ADMIN] Admin Dashboard: http://localhost:{port}/api/admin/auth/login")
    print(f"[ADMIN] Health Check: http://localhost:{port}/api/health")
    print("=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=port)
