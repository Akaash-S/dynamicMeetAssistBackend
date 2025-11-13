"""
Backend Initialization Script
Runs automatic setup before starting the Flask application
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def initialize_backend():
    """Initialize backend services"""
    logger.info("="*60)
    logger.info("MeetingMind Backend Initialization")
    logger.info("="*60)
    
    # Check Python version
    python_version = sys.version_info
    logger.info(f"Python Version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check environment
    env = os.getenv('FLASK_ENV', 'development')
    logger.info(f"Environment: {env}")
    
    # Run auto-setup
    try:
        from config.auto_setup import run_auto_setup
        
        logger.info("\nRunning automatic AWS setup...")
        results = run_auto_setup()
        
        # Check critical services
        critical_failures = []
        
        # RDS and S3 are optional for local development
        if not results['rds_tables'] and env == 'production':
            critical_failures.append("RDS tables not ready")
        
        if not results['s3_bucket'] and env == 'production':
            critical_failures.append("S3 bucket not ready")
        
        if critical_failures and env == 'production':
            logger.error("\n❌ Critical services not ready for production:")
            for failure in critical_failures:
                logger.error(f"  - {failure}")
            logger.error("\nPlease configure AWS services before deploying to production.")
            logger.error("See AWS_SETUP_GUIDE.md for instructions.\n")
            return False
        
        if env == 'development':
            logger.info("\n✓ Development environment initialized")
            logger.info("Note: AWS services are optional for local development")
        else:
            logger.info("\n✓ Production environment initialized")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        
        if env == 'production':
            return False
        else:
            logger.warning("Continuing in development mode despite errors...")
            return True


def check_dependencies():
    """Check if required Python packages are installed"""
    logger.info("\nChecking dependencies...")
    
    required_packages = {
        'flask': 'Flask',
        'psycopg2': 'psycopg2-binary',
        'boto3': 'boto3',
        'pyotp': 'pyotp',
        'qrcode': 'qrcode',
        'twilio': 'twilio',
        'sendgrid': 'sendgrid'
    }
    
    missing_packages = []
    
    for package, install_name in required_packages.items():
        try:
            __import__(package)
            logger.info(f"  ✓ {install_name}")
        except ImportError:
            logger.warning(f"  ✗ {install_name} (optional)")
            missing_packages.append(install_name)
    
    if missing_packages:
        logger.warning(f"\nOptional packages not installed: {', '.join(missing_packages)}")
        logger.warning("Install with: pip install " + " ".join(missing_packages))
    else:
        logger.info("✓ All packages installed")
    
    return True


def display_startup_info():
    """Display startup information"""
    logger.info("\n" + "="*60)
    logger.info("Server Configuration:")
    logger.info("="*60)
    
    # Display configuration (without sensitive data)
    configs = {
        'Port': os.getenv('PORT', '8000'),
        'Flask Environment': os.getenv('FLASK_ENV', 'development'),
        'AWS Region': os.getenv('AWS_REGION', 'not configured'),
        'RDS Host': os.getenv('RDS_HOST', 'not configured'),
        'S3 Bucket': os.getenv('S3_BUCKET_NAME', 'not configured'),
        'Email Service': 'Gmail SMTP' if os.getenv('EMAIL_ADDRESS') else 'not configured'
    }
    
    for key, value in configs.items():
        # Mask sensitive values
        if 'password' in key.lower() or 'secret' in key.lower() or 'key' in key.lower():
            display_value = '***' if value != 'not configured' else value
        else:
            display_value = value
        logger.info(f"  {key}: {display_value}")
    
    logger.info("="*60 + "\n")


def main():
    """Main initialization function"""
    try:
        # Check dependencies
        check_dependencies()
        
        # Display startup info
        display_startup_info()
        
        # Initialize backend
        success = initialize_backend()
        
        if success:
            logger.info("✓ Backend initialization complete\n")
            return True
        else:
            logger.error("✗ Backend initialization failed\n")
            return False
            
    except KeyboardInterrupt:
        logger.info("\nInitialization interrupted by user")
        return False
    except Exception as e:
        logger.error(f"\nUnexpected error during initialization: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
