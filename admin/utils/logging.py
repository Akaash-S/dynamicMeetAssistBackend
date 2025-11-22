"""Admin logging utilities"""
import logging

logger = logging.getLogger(__name__)

def log_admin_action(admin_email: str, action: str, resource_type: str = None, 
                    resource_id: str = None, details: str = None):
    """Log admin action to database"""
    try:
        from flask import request
        from config.aws_rds_database import rds_db
        from datetime import datetime
        
        ip_address = request.remote_addr if request else None
        user_agent = request.headers.get('User-Agent') if request else None
        
        log_query = """
        INSERT INTO admin_logs (admin_email, action, resource_type, resource_id, details, ip_address, user_agent, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        rds_db.execute_query(log_query, (
            admin_email, action, resource_type, resource_id, details,
            ip_address, user_agent, datetime.utcnow()
        ))
        
        logger.info(f"Admin action logged: {admin_email} - {action}")
    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")
