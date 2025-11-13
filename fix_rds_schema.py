"""
Fix RDS Database Schema
Drops all existing tables and recreates them with correct UUID schema
"""

from config.aws_rds_database import rds_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def drop_all_tables():
    """Drop all existing tables"""
    print("\n" + "="*70)
    print("Dropping All Existing Tables")
    print("="*70)
    
    drop_queries = [
        "DROP TABLE IF EXISTS admin_logs CASCADE;",
        "DROP TABLE IF EXISTS admin_notifications CASCADE;",
        "DROP TABLE IF EXISTS admin_payments CASCADE;",
        "DROP TABLE IF EXISTS admin_issues CASCADE;",
        "DROP TABLE IF EXISTS notifications CASCADE;",
        "DROP TABLE IF EXISTS processing_status CASCADE;",
        "DROP TABLE IF EXISTS tasks CASCADE;",
        "DROP TABLE IF EXISTS timeline CASCADE;",
        "DROP TABLE IF EXISTS meetings CASCADE;",
        "DROP TABLE IF EXISTS users CASCADE;",
    ]
    
    try:
        for query in drop_queries:
            table_name = query.split("IF EXISTS ")[1].split(" ")[0]
            rds_db.execute_query(query)
            print(f"  ✅ Dropped table: {table_name}")
        
        print("\n✅ All tables dropped successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        print(f"\n❌ Error: {e}")
        return False


def main():
    print("\n🔧 RDS Database Schema Fix")
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
        return False
    
    print("\n✅ Database connection successful!")
    print(f"   Host: {health['database']['host']}")
    print(f"   Database: {health['database']['name']}")
    
    # Ask for confirmation
    print("\n⚠️  WARNING: This will DELETE ALL DATA in your RDS database!")
    print("   All tables will be dropped and recreated with correct schema.")
    response = input("\nType 'YES' to continue: ")
    
    if response != 'YES':
        print("\n❌ Operation cancelled.")
        return False
    
    # Drop all tables
    if not drop_all_tables():
        return False
    
    # Recreate tables using init_rds_db
    print("\n" + "="*70)
    print("Recreating Tables with Correct Schema")
    print("="*70)
    
    try:
        from config.aws_rds_database import init_rds_db
        init_rds_db()
        
        print("\n" + "="*70)
        print("✅ Database Schema Fixed Successfully!")
        print("="*70)
        print("\nYour RDS database now has:")
        print("  • All tables with UUID primary keys")
        print("  • Proper foreign key relationships")
        print("  • 2FA columns in users table")
        print("  • All admin tables")
        print("\nYou can now start your application:")
        print("  python app.py")
        
        return True
        
    except Exception as e:
        logger.error(f"Error recreating tables: {e}")
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
