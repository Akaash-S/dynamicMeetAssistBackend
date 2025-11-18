"""
Fix table column types in RDS database
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from config.aws_rds_database import rds_db

def fix_table_types():
    print("=" * 60)
    print("FIXING TABLE COLUMN TYPES")
    print("=" * 60)
    print()
    
    try:
        # Drop tables in correct order (respecting foreign keys)
        print("Dropping existing tables...")
        
        drop_queries = [
            "DROP TABLE IF EXISTS notifications CASCADE;",
            "DROP TABLE IF EXISTS processing_status CASCADE;",
            "DROP TABLE IF EXISTS tasks CASCADE;",
            "DROP TABLE IF EXISTS timeline CASCADE;",
            "DROP TABLE IF EXISTS meetings CASCADE;",
            "DROP TABLE IF EXISTS users CASCADE;",
        ]
        
        for query in drop_queries:
            rds_db.execute_query(query)
            table_name = query.split()[4]
            print(f"  ✅ Dropped {table_name}")
        
        print()
        print("✅ All tables dropped successfully!")
        print()
        print("Now restart the backend server to recreate tables with correct types:")
        print("  python backend/app.py")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    fix_table_types()
