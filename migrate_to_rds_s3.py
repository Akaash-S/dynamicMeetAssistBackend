"""
Migration Script: Update all routes to use RDS and S3
This script updates imports and database calls across all route files
"""

import os
import re

# Files to update
ROUTE_FILES = [
    'routes/auth.py',
    'routes/meetings.py',
    'routes/tasks.py',
    'routes/upload.py',
    'routes/health.py',
    'routes/google_calendar.py',
    'routes/admin_auth.py',
    'routes/admin_users.py',
    'routes/admin_issues.py',
    'routes/admin_payments.py',
    'routes/admin_notifications.py',
]

# Import replacements
IMPORT_REPLACEMENTS = {
    'from config.database import get_db': 'from config.aws_rds_database import rds_db',
    'from config.database import get_db_connection': 'from config.aws_rds_database import rds_db',
    'from config.storage import storage': 'from services.aws_s3_service import s3_service',
}

# Database call replacements
DB_REPLACEMENTS = {
    # SQLite style
    r'get_db\(\)\.execute_query\(': 'rds_db.execute_query(',
    r'get_db\(\)\.cursor\(\)': 'rds_db.get_cursor()',
    r'get_db\(\)\.commit\(\)': '# Commit handled by rds_db',
    r'get_db\(\)\.close\(\)': '# Close handled by rds_db',
    
    # Placeholder style (? to %s)
    r'\?': '%s',
}

def update_file(filepath):
    """Update a single file"""
    print(f"\nUpdating: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"  ⚠ File not found, skipping")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes = 0
    
    # Update imports
    for old_import, new_import in IMPORT_REPLACEMENTS.items():
        if old_import in content:
            content = content.replace(old_import, new_import)
            changes += 1
            print(f"  ✓ Updated import: {old_import}")
    
    # Update database calls
    for pattern, replacement in DB_REPLACEMENTS.items():
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            changes += len(matches)
            print(f"  ✓ Updated {len(matches)} occurrence(s) of: {pattern}")
    
    if changes > 0:
        # Backup original
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"  ✓ Backup created: {backup_path}")
        
        # Write updated content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ File updated with {changes} changes")
        return True
    else:
        print(f"  ℹ No changes needed")
        return False

def main():
    print("="*60)
    print("RDS & S3 Migration Script")
    print("="*60)
    print("\nThis script will update all route files to use:")
    print("  - AWS RDS PostgreSQL (instead of SQLite)")
    print("  - AWS S3 (instead of local storage)")
    print("\nBackup files will be created with .backup extension")
    print("="*60)
    
    input("\nPress Enter to continue or Ctrl+C to cancel...")
    
    updated_files = []
    skipped_files = []
    
    for route_file in ROUTE_FILES:
        filepath = os.path.join(os.path.dirname(__file__), route_file)
        if update_file(filepath):
            updated_files.append(route_file)
        else:
            skipped_files.append(route_file)
    
    print("\n" + "="*60)
    print("Migration Complete!")
    print("="*60)
    print(f"\nUpdated files: {len(updated_files)}")
    for f in updated_files:
        print(f"  ✓ {f}")
    
    if skipped_files:
        print(f"\nSkipped files: {len(skipped_files)}")
        for f in skipped_files:
            print(f"  - {f}")
    
    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60)
    print("1. Review the changes in each file")
    print("2. Test the endpoints")
    print("3. If issues occur, restore from .backup files")
    print("4. Update frontend API endpoints")
    print("\nTo restore a file:")
    print("  copy routes\\filename.py.backup routes\\filename.py")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
