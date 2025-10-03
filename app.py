from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import blueprints
from routes.auth import auth_bp
from routes.meetings import meetings_bp
from routes.tasks import tasks_bp
from routes.upload import upload_bp
from routes.health import health_bp

# Import database initialization
from config.database import init_db

# Import middleware
from middleware.rate_limiting import limiter

def create_app():
    app = Flask(__name__)
    
    # Configure CORS for all origins on API routes
    # This allows the React frontend to call APIs without CORS issues
    CORS(app, 
         resources={
             r"/api/*": {
                 "origins": "*",  # Allow all origins for API routes
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                 "supports_credentials": False
             }
         },
         # Handle preflight OPTIONS requests
         send_wildcard=False,
         automatic_options=True
    )
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
    
    # Initialize database
    init_db()
    
    # Initialize rate limiter
    limiter.init_app(app)
    
    # Simple health endpoint (as requested)
    @app.route('/api/health', methods=['GET', 'OPTIONS'])
    def simple_health():
        """Simple health endpoint that returns {"status": "ok"} with 200 response"""
        try:
            if request.method == 'OPTIONS':
                # Handle preflight request
                response = jsonify()
                response.headers.add('Access-Control-Allow-Origin', '*')
                response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
                response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
                return response
            
            # Always return 200 for health checks
            return jsonify({
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Backend is running"
            }), 200
            
        except Exception as e:
            # Even if there's an error, return 200 to prevent frontend issues
            return jsonify({
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "message": "Backend is running but encountered an error"
            }), 200
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(meetings_bp, url_prefix='/api/meetings')
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    app.register_blueprint(health_bp, url_prefix='/api/health/detailed')
    
    # Global error handlers
    @app.errorhandler(400)
    def bad_request(error):
        print(f"❌ 400 Bad Request: {error}")
        print(f"❌ Request URL: {request.url}")
        print(f"❌ Request method: {request.method}")
        print(f"❌ Request headers: {dict(request.headers)}")
        return jsonify({
            'error': 'Bad Request',
            'message': str(error),
            'url': request.url,
            'method': request.method
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({'error': 'File too large. Maximum size is 100MB'}), 413
    
    # Root endpoint
    @app.route('/')
    def root():
        return jsonify({
            'message': 'AI Meeting Assistant Backend API',
            'version': '1.0.0',
            'status': 'running',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    return app

if __name__ == '__main__':
    app = create_app()
    # Get port from environment variable (for Render deployment) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    # Use debug=False for production, debug=True for development
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

# For deployment (Gunicorn will use this)
app = create_app()
