"""
Add 2FA columns to users table for TOTP authentication
Run this script to update your RDS database schema
"""

from config.aws_rds_database import rds_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_2fa_columns():
    """Add 2FA-related columns to users table"""
    
    print("\n" + "="*70)
    print("Adding 2FA Columns to Users Table")
    print("="*70)
    
    # Check if columns already exist
    check_query = """
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'users' 
    AND column_name IN ('two_factor_enabled', 'two_factor_method', 'two_factor_secret', 'backup_codes')
    """
    
    try:
        existing_columns = rds_db.execute_query(check_query, fetch_all=True)
        existing_column_names = [col['column_name'] for col in existing_columns] if existing_columns else []
        
        print(f"\n📊 Existing 2FA columns: {existing_column_names}")
        
        # Add columns if they don't exist
        columns_to_add = []
        
        if 'two_factor_enabled' not in existing_column_names:
            columns_to_add.append(('two_factor_enabled', 'BOOLEAN DEFAULT FALSE'))
        
        if 'two_factor_method' not in existing_column_names:
            columns_to_add.append(('two_factor_method', 'VARCHAR(50)'))
        
        if 'two_factor_secret' not in existing_column_names:
            columns_to_add.append(('two_factor_secret', 'TEXT'))
        
        if 'backup_codes' not in existing_column_names:
            columns_to_add.append(('backup_codes', 'TEXT'))
        
        if not columns_to_add:
            print("\n✅ All 2FA columns already exist!")
            return True
        
        print(f"\n📝 Adding {len(columns_to_add)} new columns...")
        
        for column_name, column_type in columns_to_add:
            alter_query = f"""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS {column_name} {column_type}
            """
            
            try:
                rds_db.execute_query(alter_query)
                print(f"  ✅ Added column: {column_name}")
            except Exception as e:
                print(f"  ⚠ Error adding {column_name}: {e}")
        
        print("\n✅ 2FA columns added successfully!")
        
        # Verify the changes
        verify_query = """
        SELECT column_name, data_type, column_default
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name IN ('two_factor_enabled', 'two_factor_method', 'two_factor_secret', 'backup_codes')
        ORDER BY column_name
        """
        
        columns = rds_db.execute_query(verify_query, fetch_all=True)
        
        print("\n📋 Current 2FA columns:")
        for col in columns:
            print(f"  • {col['column_name']}: {col['data_type']} (default: {col['column_default']})")
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding 2FA columns: {e}")
        print(f"\n❌ Error: {e}")
        return False


def test_2fa_columns():
    """Test that 2FA columns work correctly"""
    
    print("\n" + "="*70)
    print("Testing 2FA Columns")
    print("="*70)
    
    try:
        # Try to select 2FA columns
        test_query = """
        SELECT two_factor_enabled, two_factor_method, two_factor_secret, backup_codes
        FROM users
        LIMIT 1
        """
        
        result = rds_db.execute_query(test_query, fetch_one=True)
        
        if result is not None:
            print("\n✅ 2FA columns are accessible!")
            print(f"   Sample data: {dict(result)}")
        else:
            print("\n✅ 2FA columns exist (no users yet)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing 2FA columns: {e}")
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n🔧 RDS Database Schema Update for 2FA")
    print("="*70)
    
    # Check database connection
    health = rds_db.health_check()
    
    if health['status'] != 'healthy':
        print("\n❌ Database connection failed!")
        print(f"   Error: {health.get('error', 'Unknown error')}")
        print("\n📋 Please check:")
        print("   1. RDS_HOST is correct")
        print("   2. RDS credentials are valid")
        print("   3. Security group allows your IP")
        print("   4. RDS instance is running")
        exit(1)
    
    print("\n✅ Database connection successful!")
    print(f"   Host: {health['database']['host']}")
    print(f"   Database: {health['database']['name']}")
    
    # Add 2FA columns
    if add_2fa_columns():
        # Test the columns
        test_2fa_columns()
        
        print("\n" + "="*70)
        print("✅ 2FA Schema Update Complete!")
        print("="*70)
        print("\nYou can now use TOTP 2FA features:")
        print("  • POST /api/2fa/setup - Setup TOTP")
        print("  • POST /api/2fa/verify - Verify and enable")
        print("  • POST /api/2fa/validate - Validate during login")
        print("  • GET /api/2fa/status - Check 2FA status")
        print("  • POST /api/2fa/disable - Disable 2FA")
        print("  • POST /api/2fa/backup-codes - Generate backup codes")
    else:
        print("\n❌ Failed to add 2FA columns")
        exit(1)
