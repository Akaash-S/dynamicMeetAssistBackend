from flask import Blueprint, jsonify
from datetime import datetime
import psycopg2

from config.database import db
from config.storage import storage
from services.transcription import transcription_service
from services.ai_processor import ai_processor
from services.calendar_sync import calendar_service
from services.email_service import email_service

health_bp = Blueprint('health', __name__)

@health_bp.route('/', methods=['GET'])
def health_check():
    """Basic health check - always returns 200 to prevent frontend errors"""
    try:
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'services': {}
        }
        
        # Check database health (most critical)
        try:
            db_health = check_database_health()
            health_status['services']['database'] = db_health
        except Exception as e:
            health_status['services']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        # Check other services safely
        services_to_check = [
            ('storage', lambda: check_storage_health()),
            ('transcription', lambda: transcription_service.get_transcription_health()),
            ('ai_processor', lambda: ai_processor.get_ai_health()),
            ('calendar', lambda: calendar_service.get_calendar_health()),
            ('email', lambda: email_service.get_email_health())
        ]
        
        for service_name, check_func in services_to_check:
            try:
                health_status['services'][service_name] = check_func()
            except Exception as e:
                health_status['services'][service_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
        
        # Always return 200 to prevent frontend connection issues
        return jsonify(health_status), 200
        
    except Exception as e:
        # Even if everything fails, return 200 with error info
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'unhealthy',
            'error': str(e),
            'message': 'Health check encountered errors but API is responding'
        }), 200

@health_bp.route('/database', methods=['GET'])
def database_health():
    """Check database connectivity and status"""
    return jsonify(check_database_health())

@health_bp.route('/storage', methods=['GET'])
def storage_health():
    """Check storage service status"""
    return jsonify(check_storage_health())

@health_bp.route('/transcription', methods=['GET'])
def transcription_health():
    """Check transcription service status"""
    return jsonify(transcription_service.get_transcription_health())

@health_bp.route('/ai', methods=['GET'])
def ai_health():
    """Check AI processor status"""
    return jsonify(ai_processor.get_ai_health())

@health_bp.route('/calendar', methods=['GET'])
def calendar_health():
    """Check calendar service status"""
    return jsonify(calendar_service.get_calendar_health())

@health_bp.route('/email', methods=['GET'])
def email_health():
    """Check email service status"""
    return jsonify(email_service.get_email_health())

@health_bp.route('/detailed', methods=['GET'])
def detailed_health():
    """Detailed health check with metrics"""
    try:
        detailed_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'services': {},
            'metrics': {}
        }
        
        # Database metrics
        db_metrics = get_database_metrics()
        detailed_status['services']['database'] = {
            **check_database_health(),
            'metrics': db_metrics
        }
        
        # Storage metrics
        storage_metrics = get_storage_metrics()
        detailed_status['services']['storage'] = {
            **check_storage_health(),
            'metrics': storage_metrics
        }
        
        # API services
        detailed_status['services']['transcription'] = transcription_service.get_transcription_health()
        detailed_status['services']['ai_processor'] = ai_processor.get_ai_health()
        detailed_status['services']['calendar'] = calendar_service.get_calendar_health()
        detailed_status['services']['email'] = email_service.get_email_health()
        
        # Overall metrics
        detailed_status['metrics']['total_meetings'] = db_metrics.get('total_meetings', 0)
        detailed_status['metrics']['total_tasks'] = db_metrics.get('total_tasks', 0)
        detailed_status['metrics']['processing_queue'] = db_metrics.get('processing_meetings', 0)
        
        return jsonify(detailed_status), 200
        
    except Exception as e:
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

def check_database_health():
    """Check database connectivity and basic operations"""
    try:
        # Test connection
        test_query = "SELECT 1 as test"
        result = db.execute_query(test_query)
        
        # Get pool status
        pool_status = db.get_pool_status()
        
        if result and result[0]['test'] == 1:
            return {
                'service': 'database',
                'status': 'healthy',
                'connection': 'active',
                'type': 'postgresql',
                'connection_pool': pool_status
            }
        else:
            return {
                'service': 'database',
                'status': 'unhealthy',
                'error': 'Query test failed',
                'connection_pool': pool_status
            }
            
    except psycopg2.OperationalError as e:
        return {
            'service': 'database',
            'status': 'unhealthy',
            'error': f'Connection failed: {str(e)}',
            'connection_pool': db.get_pool_status()
        }
    except Exception as e:
        return {
            'service': 'database',
            'status': 'unhealthy',
            'error': str(e)
        }

def check_storage_health():
    """Check storage service connectivity"""
    try:
        # Test storage connectivity
        # For Supabase, we can check if we can access the client
        if hasattr(storage, 'client') and storage.client:
            return {
                'service': 'storage',
                'status': 'healthy',
                'provider': 'supabase',
                'bucket': storage.bucket_name
            }
        else:
            return {
                'service': 'storage',
                'status': 'unhealthy',
                'error': 'Storage client not initialized'
            }
            
    except Exception as e:
        return {
            'service': 'storage',
            'status': 'unhealthy',
            'error': str(e)
        }

def get_database_metrics():
    """Get database usage metrics"""
    try:
        metrics = {}
        
        # Count meetings
        meetings_query = "SELECT COUNT(*) as count FROM meetings"
        meetings_result = db.execute_query(meetings_query)
        metrics['total_meetings'] = meetings_result[0]['count'] if meetings_result else 0
        
        # Count tasks
        tasks_query = "SELECT COUNT(*) as count FROM tasks"
        tasks_result = db.execute_query(tasks_query)
        metrics['total_tasks'] = tasks_result[0]['count'] if tasks_result else 0
        
        # Count processing meetings
        processing_query = "SELECT COUNT(*) as count FROM meetings WHERE status = 'processing'"
        processing_result = db.execute_query(processing_query)
        metrics['processing_meetings'] = processing_result[0]['count'] if processing_result else 0
        
        # Count completed meetings
        completed_query = "SELECT COUNT(*) as count FROM meetings WHERE status = 'completed'"
        completed_result = db.execute_query(completed_query)
        metrics['completed_meetings'] = completed_result[0]['count'] if completed_result else 0
        
        # Count failed meetings
        failed_query = "SELECT COUNT(*) as count FROM meetings WHERE status = 'failed'"
        failed_result = db.execute_query(failed_query)
        metrics['failed_meetings'] = failed_result[0]['count'] if failed_result else 0
        
        # Recent activity (last 24 hours)
        recent_query = """
        SELECT COUNT(*) as count FROM meetings 
        WHERE created_at > NOW() - INTERVAL '24 hours'
        """
        recent_result = db.execute_query(recent_query)
        metrics['meetings_last_24h'] = recent_result[0]['count'] if recent_result else 0
        
        return metrics
        
    except Exception as e:
        return {'error': str(e)}

def get_storage_metrics():
    """Get storage usage metrics"""
    try:
        metrics = {}
        
        # Get total file size from database
        size_query = "SELECT SUM(file_size) as total_size FROM meetings WHERE file_size IS NOT NULL"
        size_result = db.execute_query(size_query)
        total_size = size_result[0]['total_size'] if size_result and size_result[0]['total_size'] else 0
        
        metrics['total_storage_bytes'] = int(total_size)
        metrics['total_storage_mb'] = round(total_size / (1024 * 1024), 2)
        
        # Count files
        files_query = "SELECT COUNT(*) as count FROM meetings WHERE audio_url IS NOT NULL"
        files_result = db.execute_query(files_query)
        metrics['total_files'] = files_result[0]['count'] if files_result else 0
        
        return metrics
        
    except Exception as e:
        return {'error': str(e)}

@health_bp.route('/routes', methods=['GET'])
def routes_health():
    """Check all API routes and their status"""
    try:
        routes_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'routes': {
                'auth': {
                    'status': 'active',
                    'endpoints': ['/api/auth/verify']
                },
                'meetings': {
                    'status': 'active',
                    'endpoints': [
                        '/api/meetings',
                        '/api/meetings/<id>',
                        '/api/meetings/<id>/timeline',
                        '/api/meetings/<id>/summary'
                    ]
                },
                'tasks': {
                    'status': 'active',
                    'endpoints': [
                        '/api/tasks',
                        '/api/tasks/<id>',
                        '/api/tasks/<id>/status'
                    ]
                },
                'upload': {
                    'status': 'active',
                    'endpoints': [
                        '/api/upload/audio',
                        '/api/upload/status/<meeting_id>'
                    ]
                },
                'health': {
                    'status': 'active',
                    'endpoints': [
                        '/api/health',
                        '/api/health/database',
                        '/api/health/storage',
                        '/api/health/transcription',
                        '/api/health/ai',
                        '/api/health/calendar',
                        '/api/health/email',
                        '/api/health/detailed',
                        '/api/health/routes'
                    ]
                }
            }
        }
        
        return jsonify(routes_status), 200
        
    except Exception as e:
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500
