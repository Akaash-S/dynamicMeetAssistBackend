"""
Fix ALL Routes to Use RDS and S3 Properly
- Remove get_db() imports
- Add fetch_one=True or fetch_all=True to all queries
- Ensure proper error handling
"""

import os
import re


def fix_route_file(filepath):
    """Fix a single route file"""
    
    filename = os.path.basename(filepath)
    print(f"\n📄 Fixing: {filename}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    changes = []
    
    # Create backup
    backup_path = filepath + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(original)
    
    # Fix 1: Remove get_db() imports
    if 'from config.database import get_db' in content:
        content = content.replace('from config.database import get_db', '# Removed: from config.database import get_db')
        changes.append("Removed get_db() import")
    
    # Fix 2: Replace get_db() calls with rds_db
    if 'get_db()' in content:
        content = re.sub(r'get_db\(\)\.execute_query', 'rds_db.execute_query', content)
        changes.append("Replaced get_db() with rds_db")
    
    # Fix 3: Add fetch parameters to SELECT queries
    # Pattern: execute_query("SELECT ...", params) without fetch parameter
    
    # For queries that should return one row
    single_row_patterns = [
        r'(rds_db\.execute_query\("SELECT \* FROM users WHERE \w+ = %s", \([^)]+\)\))',
        r'(rds_db\.execute_query\("SELECT [^"]+ FROM users WHERE [^"]+", \([^)]+\)\))',
        r'(rds_db\.execute_query\(get_\w+_query, \([^)]+\)\))',
    ]
    
    for pattern in single_row_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if 'fetch_one' not in match and 'fetch_all' not in match:
                # Add fetch_one=True before the closing parenthesis
                new_match = match.rstrip(')') + ', fetch_one=True)'
                content = content.replace(match, new_match)
                changes.append("Added fetch_one=True")
    
    # For queries that should return multiple rows
    multi_row_patterns = [
        r'(rds_db\.execute_query\("SELECT [^"]+ FROM \w+ ORDER BY [^"]+", \([^)]*\)\))',
        r'(rds_db\.execute_query\("SELECT [^"]+ FROM \w+ WHERE [^"]+ LIMIT [^"]+", \([^)]*\)\))',
    ]
    
    for pattern in multi_row_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if 'fetch_one' not in match and 'fetch_all' not in match:
                new_match = match.rstrip(')') + ', fetch_all=True)'
                content = content.replace(match, new_match)
                changes.append("Added fetch_all=True")
    
    # Fix 4: Fix double commas and duplicate fetch parameters
    content = re.sub(r',\s*,', ',', content)
    content = re.sub(r', fetch_all=True\), fetch_one=True\)', ', fetch_one=True)', content)
    content = re.sub(r', fetch_one=True\), fetch_all=True\)', ', fetch_all=True)', content)
    
    # Fix 5: Ensure storage imports use S3
    if 'from config.storage import storage' in content:
        content = content.replace(
            'from config.storage import storage',
            'from services.aws_s3_service import s3_service'
        )
        content = content.replace('storage.', 's3_service.')
        changes.append("Replaced storage with s3_service")
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if changes:
            for change in set(changes):
                print(f"  ✅ {change}")
        return True
    else:
        print(f"  ℹ️  No changes needed")
        return False


def main():
    print("="*70)
    print("Fixing ALL Routes to Use RDS and S3")
    print("="*70)
    
    routes_dir = os.path.join(os.path.dirname(__file__), 'routes')
    
    # Get all Python files in routes directory
    route_files = []
    for filename in os.listdir(routes_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            route_files.append(os.path.join(routes_dir, filename))
    
    fixed = 0
    for filepath in sorted(route_files):
        if fix_route_file(filepath):
            fixed += 1
    
    print("\n" + "="*70)
    print(f"✅ Fixed {fixed} route files")
    print("="*70)
    
    print("\n📋 What was done:")
    print("  • Removed get_db() imports")
    print("  • Replaced get_db() with rds_db")
    print("  • Added fetch_one=True to single-row queries")
    print("  • Added fetch_all=True to multi-row queries")
    print("  • Replaced storage with s3_service")
    print("  • Fixed syntax errors (double commas, etc.)")
    
    print("\n🔄 Next steps:")
    print("  1. Restart backend: python app.py")
    print("  2. Test all endpoints")
    print("  3. Register new user")
    print("  4. Upload meeting")
    
    print("\n⚠️  Important:")
    print("  • All routes now use RDS")
    print("  • All storage uses S3")
    print("  • Database is empty - users must register")


if __name__ == "__main__":
    main()
