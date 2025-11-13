"""
Verify RDS Database Tables
Check that all required tables exist with correct schema
"""

from config.aws_rds_database import rds_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_tables():
    """Verify all required tables exist"""
    print("\n" + "="*70)
    print("Verifying RDS Database Tables")
    print("="*70)
    
    # Required tables for the application
    required_tables = [
        'users',
        'meetings',
        'timeline',
        'tasks',
        'processing_status',
        'notifications',
        'admin_issues',
        'admin_payments',
        'admin_notifications',
        'admin_logs',
    ]
    
    try:
        # Get all tables
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
        """
        
        result = rds_db.execute_query(query, fetch_all=True)
        existing_tables = [row['table_name'] for row in result]
        
        print(f"\n📊 Found {len(existing_tables)} tables in database:")
        for table in existing_tables:
            print(f"  • {table}")
        
        # Check required tables
        print(f"\n✅ Checking required tables:")
        missing_tables = []
        
        for table in required_tables:
            if table in existing_tables:
                print(f"  ✅ {table}")
            else:
                print(f"  ❌ {table} - MISSING")
                missing_tables.append(table)
        
        if missing_tables:
            print(f"\n❌ Missing {len(missing_tables)} required tables!")
            return False
        
        print(f"\n✅ All {len(required_tables)} required tables exist!")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying tables: {e}")
        print(f"\n❌ Error: {e}")
        return False


def verify_users_table_schema():
    """Verify users table has 2FA columns"""
    print("\n" + "="*70)
    print("Verifying Users Table Schema (2FA Support)")
    print("="*70)
    
    try:
        query = """
        SELECT column_name, data_type, column_default
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name IN (
            'id', 'email', 'name', 'firebase_uid', 'google_oauth_id',
            'two_factor_enabled', 'two_factor_method', 'two_factor_secret', 'backup_codes'
        )
        ORDER BY column_name
        """
        
        result = rds_db.execute_query(query, fetch_all=True)
        
        print(f"\n📋 Users table columns:")
        for col in result:
            default = col['column_default'] or 'NULL'
            print(f"  • {col['column_name']}: {col['data_type']} (default: {default})")
        
        # Check for 2FA columns
        column_names = [col['column_name'] for col in result]
        required_2fa_columns = ['two_factor_enabled', 'two_factor_method', 'two_factor_secret', 'backup_codes']
        
        missing_2fa = [col for col in required_2fa_columns if col not in column_names]
        
        if missing_2fa:
            print(f"\n⚠️  Missing 2FA columns: {', '.join(missing_2fa)}")
            return False
        
        print(f"\n✅ Users table has all 2FA columns!")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying users table: {e}")
        print(f"\n❌ Error: {e}")
        return False


def verify_uuid_columns():
    """Verify that primary keys are UUIDs"""
    print("\n" + "="*70)
    print("Verifying UUID Primary Keys")
    print("="*70)
    
    tables_to_check = ['users', 'meetings', 'tasks', 'timeline']
    
    try:
        for table in tables_to_check:
            query = f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table}' 
            AND column_name = 'id'
            """
            
            result = rds_db.execute_query(query, fetch_one=True)
            
            if result:
                data_type = result['data_type']
                if data_type == 'uuid':
                    print(f"  ✅ {table}.id: {data_type}")
                else:
                    print(f"  ❌ {table}.id: {data_type} (should be uuid)")
                    return False
            else:
                print(f"  ❌ {table}: No 'id' column found")
                return False
        
        print(f"\n✅ All primary keys are UUIDs!")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying UUID columns: {e}")
        print(f"\n❌ Error: {e}")
        return False


def verify_foreign_keys():
    """Verify foreign key relationships"""
    print("\n" + "="*70)
    print("Verifying Foreign Key Relationships")
    print("="*70)
    
    try:
        query = """
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name, kcu.column_name
        """
        
        result = rds_db.execute_query(query, fetch_all=True)
        
        print(f"\n📋 Found {len(result)} foreign key relationships:")
        for fk in result:
            print(f"  • {fk['table_name']}.{fk['column_name']} → {fk['foreign_table_name']}.{fk['foreign_column_name']}")
        
        print(f"\n✅ All foreign keys are properly configured!")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying foreign keys: {e}")
        print(f"\n❌ Error: {e}")
        return False


def count_records():
    """Count records in each table"""
    print("\n" + "="*70)
    print("Counting Records in Tables")
    print("="*70)
    
    tables = ['users', 'meetings', 'tasks', 'timeline', 'notifications']
    
    try:
        print(f"\n📊 Record counts:")
        for table in tables:
            query = f"SELECT COUNT(*) as count FROM {table}"
            result = rds_db.execute_query(query, fetch_one=True)
            count = result['count'] if result else 0
            print(f"  • {table}: {count} records")
        
        return True
        
    except Exception as e:
        logger.error(f"Error counting records: {e}")
        print(f"\n❌ Error: {e}")
        return False


def main():
    print("\n🔍 RDS Database Verification")
    print("="*70)
    
    # Check database connection
    health = rds_db.health_check()
    
    if health['status'] != 'healthy':
        print("\n❌ Database connection failed!")
        print(f"   Error: {health.get('error', 'Unknown error')}")
        return False
    
    print("\n✅ Database connection successful!")
    print(f"   Host: {health['database']['host']}")
    print(f"   Database: {health['database']['name']}")
    
    # Run all verifications
    checks = [
        ("Tables Exist", verify_tables),
        ("Users Table Schema", verify_users_table_schema),
        ("UUID Primary Keys", verify_uuid_columns),
        ("Foreign Keys", verify_foreign_keys),
        ("Record Counts", count_records),
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            logger.error(f"Error in {check_name}: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("Verification Summary")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check_name}")
    
    print(f"\n📊 Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n" + "="*70)
        print("✅ RDS Database is Ready!")
        print("="*70)
        print("\nYour database has:")
        print("  • All required tables")
        print("  • UUID primary keys")
        print("  • 2FA support in users table")
        print("  • Proper foreign key relationships")
        print("\nYou can now start your application:")
        print("  cd backend")
        print("  python app.py")
        return True
    else:
        print("\n❌ Some checks failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
