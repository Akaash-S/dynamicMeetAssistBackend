"""
Quick script to create RDS tables immediately
Run this if auto-setup is having issues
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

print("="*60)
print("Create RDS Tables - Quick Fix")
print("="*60)

# Get RDS credentials
rds_host = os.getenv('RDS_HOST')
rds_port = os.getenv('RDS_PORT', '5432')
rds_database = os.getenv('RDS_DATABASE')
rds_user = os.getenv('RDS_USER')
rds_password = os.getenv('RDS_PASSWORD')

if not all([rds_host, rds_database, rds_user, rds_password]):
    print("\n✗ RDS credentials not configured in .env file")
    print("Please set: RDS_HOST, RDS_DATABASE, RDS_USER, RDS_PASSWORD")
    sys.exit(1)

print(f"\nConnecting to RDS...")
print(f"  Host: {rds_host}")
print(f"  Database: {rds_database}")
print(f"  User: {rds_user}")

try:
    # Connect to RDS
    conn = psycopg2.connect(
        host=rds_host,
        port=rds_port,
        database=rds_database,
        user=rds_user,
        password=rds_password,
        sslmode='prefer',
        connect_timeout=10
    )
    
    print("✓ Connected to RDS successfully")
    
    # Read schema file
    schema_path = os.path.join(os.path.dirname(__file__), 'migrations', 'rds_schema.sql')
    
    if not os.path.exists(schema_path):
        print(f"\n✗ Schema file not found: {schema_path}")
        sys.exit(1)
    
    print(f"\nReading schema file: {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    print(f"✓ Schema file loaded ({len(schema_sql)} characters)")
    
    # Execute schema
    print("\nExecuting schema...")
    print("This may take a minute...")
    
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        cursor.execute(schema_sql)
        print("✓ Schema executed successfully!")
    except Exception as e:
        print(f"\n⚠ Error executing schema: {e}")
        print("\nTrying to continue anyway...")
    
    # Verify tables were created
    print("\nVerifying tables...")
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    tables = cursor.fetchall()
    
    if tables:
        print(f"\n✓ Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
    else:
        print("\n✗ No tables found!")
        print("Schema execution may have failed.")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*60)
    print("Table Creation Complete!")
    print("="*60)
    print("\nYou can now start the server:")
    print("  python app.py")
    print("\n" + "="*60)
    
except psycopg2.OperationalError as e:
    print(f"\n✗ Connection failed: {e}")
    print("\nCheck:")
    print("  1. RDS instance is running")
    print("  2. Security group allows your IP on port 5432")
    print("  3. Credentials are correct in .env file")
    sys.exit(1)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
