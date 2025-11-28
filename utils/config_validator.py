"""
Configuration Validator
Validates environment variables and configuration on startup
"""

import os
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

class ConfigValidator:
    """Validates application configuration"""
    
    @staticmethod
    def validate_all() -> Tuple[bool, List[str]]:
        """
        Validate all configuration settings
        
        Returns:
            tuple: (is_valid, list_of_warnings)
        """
        warnings = []
        is_valid = True
        
        # Check AWS RDS database configuration
        rds_host = os.getenv('RDS_HOST')
        rds_user = os.getenv('RDS_USER')
        rds_password = os.getenv('RDS_PASSWORD')
        rds_database = os.getenv('RDS_DATABASE')
        
        if not all([rds_host, rds_user, rds_password, rds_database]):
            warnings.append("⚠️  AWS RDS database not properly configured")
            is_valid = False
        
        # Check API keys
        gemini_key = os.getenv('GEMINI_API_KEY')
        if not gemini_key:
            warnings.append("⚠️  Gemini API key not configured (AI features disabled)")
        
        rapidapi_key = os.getenv('RAPIDAPI_KEY')
        if not rapidapi_key:
            warnings.append("⚠️  RapidAPI key not configured (transcription may not work)")
        
        # Check Google Calendar configuration
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        if not google_client_id or not google_client_secret:
            warnings.append("⚠️  Google Calendar API not configured (calendar sync disabled)")
        
        # Check email configuration
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        if not email_address or not email_password:
            warnings.append("⚠️  Email configuration missing (notifications disabled)")
        
        # Check secret key
        secret_key = os.getenv('SECRET_KEY')
        if not secret_key or secret_key == 'dev-secret-key':
            warnings.append("⚠️  Using default secret key (change in production!)")
        
        # Check CORS configuration
        flask_env = os.getenv('FLASK_ENV', 'production')
        cors_origins = os.getenv('CORS_ORIGINS', '')
        if flask_env == 'production' and not cors_origins:
            warnings.append("⚠️  CORS origins not configured for production")
            is_valid = False
        
        # Check admin configuration
        admin_email = os.getenv('ADMIN_EMAIL')
        admin_password = os.getenv('ADMIN_PASSWORD')
        if not admin_email or not admin_password:
            warnings.append("⚠️  Admin credentials not configured")
        elif admin_password == 'admin123':
            warnings.append("⚠️  Using default admin password (change in production!)")
        
        return is_valid, warnings
    
    @staticmethod
    def print_validation_report():
        """Print configuration validation report"""
        logger.info("=" * 60)
        logger.info("Configuration Validation Report")
        logger.info("=" * 60)
        
        is_valid, warnings = ConfigValidator.validate_all()
        
        if is_valid and not warnings:
            logger.info("✅ All configuration checks passed!")
        else:
            if warnings:
                logger.warning("Configuration warnings:")
                for warning in warnings:
                    logger.warning(f"  {warning}")
            
            if not is_valid:
                logger.error("❌ Critical configuration errors detected!")
                logger.error("   Application may not function correctly")
            else:
                logger.info("✅ Core configuration is valid")
        
        logger.info("=" * 60)
        
        return is_valid
    
    @staticmethod
    def get_config_summary() -> dict:
        """Get configuration summary"""
        return {
            "environment": os.getenv('FLASK_ENV', 'production'),
            "port": os.getenv('PORT', '5000'),
            "database_configured": bool(os.getenv('RDS_HOST') and os.getenv('RDS_USER')),
            "storage_configured": bool(os.getenv('S3_BUCKET_NAME')),
            "ai_configured": bool(os.getenv('GEMINI_API_KEY')),
            "transcription_configured": bool(os.getenv('RAPIDAPI_KEY')),
            "calendar_configured": bool(os.getenv('GOOGLE_CLIENT_ID')),
            "email_configured": bool(os.getenv('EMAIL_ADDRESS')),
            "admin_configured": bool(os.getenv('ADMIN_EMAIL')),
            "cors_origins": os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []
        }
