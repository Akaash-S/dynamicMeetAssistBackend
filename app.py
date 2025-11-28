from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Run automatic AWS setup on startup
try:
    from initialize import initialize_backend
    print("\n[SETUP] Running automatic AWS setup...")
    initialize_backend()
except Exception as e:
    print(f"[WARNING] Auto-setup failed: {e}")
    print("   Continuing with manual configuration...")

# Import blueprints
from routes.auth import auth_bp
from routes.meetings import meetings_bp
from routes.tasks import tasks_bp
from routes.upload import upload_bp
from routes.health import health_bp
from routes.google_calendar import google_calendar_bp
from routes.notifications import notifications_bp
from routes.auth_2fa import auth_2fa_bp  # Enhanced 2FA routes

# Import database initialization
from config.aws_rds_database import init_rds_db

# Import middleware
from middleware.rate_limiting import limiter

def create_app():
    app = Flask(__name__)
    
    # Environment-based CORS configuration
    flask_env = os.getenv('FLASK_ENV', 'production')
    cors_origins = os.getenv('CORS_ORIGINS', '')
    
    # Parse CORS origins from environment variable
    if cors_origins:
        allowed_origins = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]
    else:
        allowed_origins = []
    
    # Add development origins only in development mode
    if flask_env == 'development':
        development_origins = [
            'http://localhost:5173',
            'http://localhost:5174', 
            'http://localhost:3000',
            'http://127.0.0.1:8080',
            'http://127.0.0.1:5173',
            'http://127.0.0.1:8080'
        ]
        allowed_origins.extend(development_origins)
        allowed_origins = list(set(allowed_origins))  # Remove duplicates
    
    # Security: In production, never allow all origins
    if flask_env == 'production' and not allowed_origins:
        raise ValueError("CORS_ORIGINS must be set in production environment")
    
    # Configure CORS with environment-specific settings
    cors_config = {
        "resources": {
            r"/api/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                "allow_headers": [
                    "Content-Type", 
                    "Authorization", 
                    "X-Requested-With", 
                    "Accept", 
                    "Origin",
                    "X-API-Key",
                    "X-CSRFToken",
                    "X-User-ID",
                    "X-Session-ID",
                    # Additional headers for voice file uploads
                    "Content-Disposition",
                    "Content-Length",
                    "Cache-Control",
                    "Pragma"
                ],
                "supports_credentials": False,
                "max_age": 86400,  # 24 hours
                "expose_headers": [
                    "Content-Type",
                    "Content-Length",
                    "Content-Disposition"
                ]
            }
        },
        "supports_credentials": False,
        "automatic_options": True
    }
    
    # Only add send_wildcard in development
    if flask_env == 'development':
        cors_config["send_wildcard"] = True
    
    CORS(app, **cors_config)

    @app.after_request
    def add_cors_headers(response):
        try:
            # Apply CORS headers to all API routes
            if request.path.startswith('/api/'):
                origin = request.headers.get('Origin')
                
                # Security: Only allow specific origins
                if origin and origin in allowed_origins:
                    response.headers['Access-Control-Allow-Origin'] = origin
                elif flask_env == 'development' and origin and (
                    origin.startswith('http://localhost:') or 
                    origin.startswith('http://127.0.0.1:') or
                    origin.startswith('https://localhost:') or
                    origin.startswith('https://127.0.0.1:')
                ):
                    # Allow localhost in development only
                    response.headers['Access-Control-Allow-Origin'] = origin
                elif flask_env == 'development' and not allowed_origins:
                    # Fallback for development when no CORS_ORIGINS set
                    response.headers['Access-Control-Allow-Origin'] = origin or '*'
                else:
                    # In production, reject unknown origins
                    if flask_env == 'production':
                        response.headers['Access-Control-Allow-Origin'] = allowed_origins[0] if allowed_origins else 'null'
                    else:
                        response.headers['Access-Control-Allow-Origin'] = origin or '*'
                
                # Set comprehensive CORS headers
                response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS,PATCH'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,Accept,Origin,X-API-Key,X-CSRFToken,X-User-ID,X-Session-ID,Content-Disposition,Content-Length,Cache-Control,Pragma'
                response.headers['Access-Control-Allow-Credentials'] = 'false'
                response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours
                response.headers['Access-Control-Expose-Headers'] = 'Content-Type,Content-Length,Content-Disposition'
                response.headers['Vary'] = 'Origin'
                
                # Handle preflight requests
                if request.method == 'OPTIONS':
                    response.status_code = 200
                    
        except Exception as e:
            print(f"CORS header error: {e}")
            # Secure fallback - only allow in development
            if flask_env == 'development':
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS,PATCH'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,Accept,Origin,X-API-Key,X-CSRFToken,X-User-ID,X-Session-ID,Content-Disposition,Content-Length,Cache-Control,Pragma'
                response.headers['Access-Control-Expose-Headers'] = 'Content-Type,Content-Length,Content-Disposition'
            else:
                # In production, don't set CORS headers on error
                pass
            
        return response
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
    
    # Initialize RDS database
    try:
        init_rds_db()
    except UnicodeEncodeError as e:
        print(f"[WARNING] Database initialization skipped due to encoding error: {e}")
        print("   Continuing without database initialization...")
    except Exception as e:
        print(f"[WARNING] Database initialization failed: {e}")
        print("   Continuing without database initialization...")
    
    # Initialize rate limiter
    limiter.init_app(app)
    
    # Global OPTIONS handler for CORS preflight requests
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = jsonify()
            origin = request.headers.get('Origin')
            
            # Security: Only allow specific origins
            if origin and origin in allowed_origins:
                response.headers.add("Access-Control-Allow-Origin", origin)
            elif flask_env == 'development' and origin and (
                origin.startswith('http://localhost:') or 
                origin.startswith('http://127.0.0.1:') or
                origin.startswith('https://localhost:') or
                origin.startswith('https://127.0.0.1:')
            ):
                # Allow localhost in development only
                response.headers.add("Access-Control-Allow-Origin", origin)
            elif flask_env == 'development' and not allowed_origins:
                # Fallback for development when no CORS_ORIGINS set
                response.headers.add("Access-Control-Allow-Origin", origin or "*")
            else:
                # In production, reject unknown origins
                if flask_env == 'production':
                    response.headers.add("Access-Control-Allow-Origin", allowed_origins[0] if allowed_origins else "null")
                else:
                    response.headers.add("Access-Control-Allow-Origin", origin or "*")
                
            response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization,X-Requested-With,Accept,Origin,X-API-Key,X-CSRFToken,X-User-ID,X-Session-ID,Content-Disposition,Content-Length,Cache-Control,Pragma")
            response.headers.add('Access-Control-Allow-Methods', "GET,POST,PUT,DELETE,OPTIONS,PATCH")
            response.headers.add('Access-Control-Allow-Credentials', "false")
            response.headers.add('Access-Control-Max-Age', "86400")
            response.headers.add('Access-Control-Expose-Headers', "Content-Type,Content-Length,Content-Disposition")
            return response
    
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
            
            # Check database connection
            db_status = "healthy"
            try:
                from config.database import get_db
                get_db().execute_query("SELECT 1")
            except Exception as db_error:
                db_status = "unhealthy"
                print(f"Database health check failed: {db_error}")
            
            # Always return 200 for health checks
            return jsonify({
                "success": True,
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Backend is running",
                "service": "Dynamic Meeting Assistant API",
                "version": "1.0.0",
                "components": {
                    "database": db_status,
                    "api": "healthy"
                }
            }), 200
            
        except Exception as e:
            # Even if there's an error, return 200 to prevent frontend issues
            return jsonify({
                "success": False,
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
    app.register_blueprint(google_calendar_bp, url_prefix='/api/calendar')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(auth_2fa_bp, url_prefix='/api')  # Enhanced 2FA with logout tracking and inactivity
    
    # Register chatbot blueprint
    try:
        from routes.chatbot import chatbot_bp
        app.register_blueprint(chatbot_bp, url_prefix='/api/chatbot')
        print("[INFO] Chatbot blueprint registered successfully")
    except Exception as e:
        print(f"[WARNING] Failed to register chatbot blueprint: {e}")
    
    # Register admin blueprints from admin directory
    try:
        print("[INFO] Importing admin blueprints from admin directory...")
        
        # Import using proper module paths
        from admin.routes.auth import admin_auth_bp
        from admin.routes.users import admin_users_bp
        from admin.routes.issues import admin_issues_bp
        from admin.routes.payments import admin_payments_bp
        from admin.routes.notifications import admin_notifications_bp
        
        app.register_blueprint(admin_auth_bp, url_prefix='/api/admin/auth')
        app.register_blueprint(admin_users_bp, url_prefix='/api/admin/users')
        app.register_blueprint(admin_issues_bp, url_prefix='/api/admin/issues')
        app.register_blueprint(admin_payments_bp, url_prefix='/api/admin/payments')
        app.register_blueprint(admin_notifications_bp, url_prefix='/api/admin/notifications')
        
        # Verify routes were registered
        admin_routes = [str(rule) for rule in app.url_map.iter_rules() if 'admin' in str(rule)]
        print(f"[INFO] Admin blueprints registered: {len(admin_routes)} routes")
    except Exception as e:
        print(f"[ERROR] Failed to register admin blueprints: {e}")
        import traceback
        traceback.print_exc()
    
    # Global error handlers
    @app.errorhandler(400)
    def bad_request(error):
        print(f"400 Bad Request: {error}")
        print(f"Request URL: {request.url}")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
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
    # Validate configuration before starting
    from utils.config_validator import ConfigValidator
    
    print("\n" + "=" * 60)
    print("[SERVER] Dynamic Meeting Assistant Backend")
    print("=" * 60)
    
    # Run configuration validation
    config_valid = ConfigValidator.print_validation_report()
    
    if not config_valid:
        print("\n[WARNING] Critical configuration issues detected!")
        print("   The application may not function correctly.")
        print("   Please review the warnings above.\n")
    
    # Print configuration summary
    config_summary = ConfigValidator.get_config_summary()
    print("\n[CONFIG] Configuration Summary:")
    print(f"   Environment: {config_summary['environment']}")
    print(f"   Port: {config_summary['port']}")
    print(f"   Database: {'[OK]' if config_summary['database_configured'] else '[MISSING]'}")
    print(f"   Storage: {'[OK]' if config_summary['storage_configured'] else '[MISSING]'}")
    print(f"   AI Processing: {'[OK]' if config_summary['ai_configured'] else '[MISSING]'}")
    print(f"   Transcription: {'[OK]' if config_summary['transcription_configured'] else '[MISSING]'}")
    print(f"   Calendar Sync: {'[OK]' if config_summary['calendar_configured'] else '[MISSING]'}")
    print(f"   Email: {'[OK]' if config_summary['email_configured'] else '[MISSING]'}")
    print(f"   Admin: {'[OK]' if config_summary['admin_configured'] else '[MISSING]'}")
    print("=" * 60 + "\n")
    
    app = create_app()
    # Get port from environment variable (for Render deployment) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    # Use debug=False for production, debug=True for development
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"[SERVER] Starting server on http://0.0.0.0:{port}")
    print(f"   Mode: {'Development' if debug_mode else 'Production'}")
    print(f"   Admin Dashboard: http://localhost:{port}/api/admin/auth/login")
    print(f"   Health Check: http://localhost:{port}/api/health\n")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
else:
    # For deployment (Gunicorn will use this)
    app = create_app()
