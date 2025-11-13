"""
Complete Migration Script: Neon → RDS, Supabase → S3
Updates all backend files to use AWS services
"""

import os
import re

print("="*70)
print("Complete AWS Migration Script")
print("="*70)
print("\nThis will update:")
print("  • Neon PostgreSQL → AWS RDS")
print("  • Supabase Storage → AWS S3")
print("  • SQLite → AWS RDS")
print("\nBackup files will be created with .backup extension")
print("="*70)

input("\nPress Enter to continue or Ctrl+C to cancel...")

# Files to update
files_to_update = {
    'config/database.py': {
        'description': 'Database configuration',
        'replacements': [
            ('NEON_DATABASE_URL', 'RDS connection (see aws_rds_database.py)'),
            ('from psycopg2.pool import SimpleConnectionPool', 'Use aws_rds_database.py instead'),
        ]
    },
    'config/storage.py': {
        'description': 'Storage configuration',
        'replacements': [
            ('SUPABASE_URL', 'S3_BUCKET_NAME'),
            ('SUPABASE_KEY', 'AWS credentials'),
            ('supabase', 's3_service'),
        ]
    },
    'utils/config_validator.py': {
        'description': 'Configuration validator',
        'replacements': [
            ("os.getenv('NEON_DATABASE_URL')", "os.getenv('RDS_HOST')"),
            ("os.getenv('SUPABASE_URL')", "os.getenv('S3_BUCKET_NAME')"),
            ("os.getenv('SUPABASE_KEY')", "os.getenv('AWS_ACCESS_KEY_ID')"),
            ('"Database URL not properly configured"', '"RDS not properly configured"'),
            ('"Supabase configuration missing"', '"S3 configuration missing"'),
        ]
    },
    'routes/upload.py': {
        'description': 'File upload routes',
        'replacements': [
            ('from config.storage import storage', 'from services.aws_s3_service import s3_service'),
            ('storage.upload_file', 's3_service.upload_file'),
            ('storage.client', 's3_service.s3_client'),
            ('SUPABASE_URL', 'S3_BUCKET_NAME'),
            ('SUPABASE_KEY', 'AWS_ACCESS_KEY_ID'),
            ('supabase', 'S3'),
        ]
    },
    'routes/health.py': {
        'description': 'Health check routes',
        'replacements': [
            ('from config.storage import storage', 'from services.aws_s3_service import s3_service'),
            ("'provider': 'supabase'", "'provider': 's3'"),
            ('storage.bucket_name', 's3_service.s3_bucket_name'),
        ]
    },
    'start_server.py': {
        'description': 'Server startup script',
        'replacements': [
            ("'NEON_DATABASE_URL'", "'RDS_HOST'"),
            ("os.getenv('NEON_DATABASE_URL')", "os.getenv('RDS_HOST')"),
        ]
    },
}

updated_count = 0
error_count = 0

for filepath, config in files_to_update.items():
    full_path = os.path.join(os.path.dirname(__file__), filepath)
    
    print(f"\n{'='*70}")
    print(f"Processing: {filepath}")
    print(f"Description: {config['description']}")
    print(f"{'='*70}")
    
    if not os.path.exists(full_path):
        print(f"  ⚠ File not found, skipping")
        continue
    
    # Read file
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = 0
    
    # Apply replacements
    for old_text, new_text in config['replacements']:
        if old_text in content:
            content = content.replace(old_text, new_text)
            changes_made += 1
            print(f"  ✓ Replaced: {old_text[:50]}...")
    
    if changes_made > 0:
        # Create backup
        backup_path = full_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"  ✓ Backup created: {backup_path}")
        
        # Write updated content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ File updated ({changes_made} changes)")
        updated_count += 1
    else:
        print(f"  ℹ No changes needed")

print("\n" + "="*70)
print("Migration Summary")
print("="*70)
print(f"\nFiles updated: {updated_count}")
print(f"Files with errors: {error_count}")

print("\n" + "="*70)
print("Next Steps")
print("="*70)
print("\n1. Review the changes in each file")
print("2. Update .env to use RDS and S3 variables")
print("3. Create RDS tables: create_tables.bat")
print("4. Test: test_aws_services.bat")
print("5. Start server: start_backend.bat")
print("\nTo restore a file:")
print("  copy <filename>.backup <filename>")
print("="*70)
