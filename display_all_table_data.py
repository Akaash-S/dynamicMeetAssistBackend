"""
Display All Table Data from RDS Database
Shows contents of all tables in a readable format
"""

import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

from config.aws_rds_database import rds_db
from datetime import datetime
import json


def display_table_data(table_name, limit=10):
    """Display data from a specific table"""
    
    print(f"\n{'='*70}")
    print(f"Table: {table_name}")
    print('='*70)
    
    try:
        # Get count
        count_query = f"SELECT COUNT(*) as count FROM {table_name}"
        count_result = rds_db.execute_query(count_query, fetch_one=True)
        total_count = count_result['count'] if count_result else 0
        
        print(f"Total Records: {total_count}")
        
        if total_count == 0:
            print("  (Empty table)")
            return
        
        # Get data
        data_query = f"SELECT * FROM {table_name} ORDER BY created_at DESC LIMIT {limit}"
        results = rds_db.execute_query(data_query, fetch_all=True)
        
        if not results:
            print("  (No data)")
            return
        
        # Display each record
        for i, record in enumerate(results, 1):
            print(f"\n--- Record {i} ---")
            for key, value in record.items():
                # Format datetime objects
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                # Format long text
                elif isinstance(value, str) and len(value) > 100:
                    value = value[:100] + '...'
                # Format lists/arrays
                elif isinstance(value, list):
                    value = ', '.join(str(v) for v in value)
                
                print(f"  {key}: {value}")
        
        if total_count > limit:
            print(f"\n... and {total_count - limit} more records")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")


def display_all_tables():
    """Display data from all tables"""
    
    print("\n" + "="*70)
    print("RDS Database - All Tables Data")
    print("="*70)
    
    # Check connection
    health = rds_db.health_check()
    if health['status'] != 'healthy':
        print("\n❌ Database connection failed!")
        print(f"   Error: {health.get('error')}")
        return
    
    print(f"\n✅ Connected to: {health['database']['host']}")
    print(f"   Database: {health['database']['name']}")
    
    # List of tables to display
    tables = [
        'users',
        'meetings',
        'timeline',
        'tasks',
        'processing_status',
        'notifications',
        'admin_issues',
        'admin_payments',
        'admin_notifications',
        'admin_logs'
    ]
    
    # Display each table
    for table in tables:
        display_table_data(table, limit=5)
    
    print("\n" + "="*70)
    print("End of Data Display")
    print("="*70)


def display_table_summary():
    """Display summary of all tables"""
    
    print("\n" + "="*70)
    print("RDS Database - Tables Summary")
    print("="*70)
    
    tables = [
        'users',
        'meetings',
        'timeline',
        'tasks',
        'processing_status',
        'notifications',
        'admin_issues',
        'admin_payments',
        'admin_notifications',
        'admin_logs'
    ]
    
    print(f"\n{'Table':<25} {'Records':<10} {'Status'}")
    print("-" * 70)
    
    for table in tables:
        try:
            count_query = f"SELECT COUNT(*) as count FROM {table}"
            result = rds_db.execute_query(count_query, fetch_one=True)
            count = result['count'] if result else 0
            status = "✅ OK" if count >= 0 else "❌ Error"
            print(f"{table:<25} {count:<10} {status}")
        except Exception as e:
            print(f"{table:<25} {'N/A':<10} ❌ Error: {str(e)[:30]}")
    
    print("-" * 70)


def search_user(email_or_id):
    """Search for a specific user"""
    
    print(f"\n{'='*70}")
    print(f"Searching for user: {email_or_id}")
    print('='*70)
    
    try:
        # Try by email first
        query = "SELECT * FROM users WHERE email = %s OR id::text = %s OR firebase_uid = %s"
        result = rds_db.execute_query(query, (email_or_id, email_or_id, email_or_id), fetch_one=True)
        
        if result:
            print("\n✅ User found:")
            for key, value in result.items():
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                print(f"  {key}: {value}")
            
            # Get user's meetings
            meetings_query = "SELECT COUNT(*) as count FROM meetings WHERE user_id = %s"
            meetings_result = rds_db.execute_query(meetings_query, (result['id'],), fetch_one=True)
            print(f"\n  Meetings: {meetings_result['count'] if meetings_result else 0}")
            
            # Get user's tasks
            tasks_query = "SELECT COUNT(*) as count FROM tasks WHERE user_id = %s"
            tasks_result = rds_db.execute_query(tasks_query, (result['id'],), fetch_one=True)
            print(f"  Tasks: {tasks_result['count'] if tasks_result else 0}")
        else:
            print("\n❌ User not found")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")


def export_to_json(table_name, output_file=None):
    """Export table data to JSON file"""
    
    if not output_file:
        output_file = f"{table_name}_export.json"
    
    print(f"\n📤 Exporting {table_name} to {output_file}...")
    
    try:
        query = f"SELECT * FROM {table_name}"
        results = rds_db.execute_query(query, fetch_all=True)
        
        if not results:
            print("  ℹ️  No data to export")
            return
        
        # Convert datetime objects to strings
        data = []
        for record in results:
            record_dict = dict(record)
            for key, value in record_dict.items():
                if isinstance(value, datetime):
                    record_dict[key] = value.isoformat()
            data.append(record_dict)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Exported {len(data)} records to {output_file}")
    
    except Exception as e:
        print(f"  ❌ Error: {e}")


def main():
    """Main function with menu"""
    
    print("\n" + "="*70)
    print("RDS Database Data Viewer")
    print("="*70)
    
    while True:
        print("\nOptions:")
        print("  1. Display all tables summary")
        print("  2. Display all tables data (first 5 records each)")
        print("  3. Display specific table")
        print("  4. Search user")
        print("  5. Export table to JSON")
        print("  6. Exit")
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == '1':
            display_table_summary()
        
        elif choice == '2':
            display_all_tables()
        
        elif choice == '3':
            table_name = input("Enter table name: ").strip()
            limit = input("Enter limit (default 10): ").strip()
            limit = int(limit) if limit else 10
            display_table_data(table_name, limit)
        
        elif choice == '4':
            search_term = input("Enter email, ID, or firebase_uid: ").strip()
            search_user(search_term)
        
        elif choice == '5':
            table_name = input("Enter table name: ").strip()
            output_file = input("Enter output file (optional): ").strip()
            export_to_json(table_name, output_file if output_file else None)
        
        elif choice == '6':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("\n❌ Invalid choice")


if __name__ == "__main__":
    # Quick display mode - just show summary
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'summary':
            display_table_summary()
        elif sys.argv[1] == 'all':
            display_all_tables()
        elif sys.argv[1] == 'search' and len(sys.argv) > 2:
            search_user(sys.argv[2])
        else:
            print("Usage:")
            print("  python display_all_table_data.py           # Interactive menu")
            print("  python display_all_table_data.py summary   # Show summary")
            print("  python display_all_table_data.py all       # Show all data")
            print("  python display_all_table_data.py search <email>  # Search user")
    else:
        # Interactive menu
        main()
