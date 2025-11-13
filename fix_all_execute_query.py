"""
Fix ALL execute_query calls across all route files
Adds proper fetch_one=True or fetch_all=True parameters
"""

import os
import glob


def fix_file(filepath):
    """Fix execute_query calls in a single file"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Skip if already has fetch parameters in most queries
    if content.count('fetch_one=True') + content.count('fetch_all=True') > 5:
        return False, "Already fixed"
    
    # Create backup
    backup_path = filepath + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(original)
    
    # Fix common patterns
    changes = 0
    
    # Pattern 1: SELECT with tuple params, no fetch
    import re
    pattern1 = r'rds_db\.execute_query\("SELECT ([^"]+)", \(([^)]+)\)\)'
    matches = re.findall(pattern1, content)
    if matches:
        for match in matches:
            old = f'rds_db.execute_query("SELECT {match[0]}", ({match[1]}))'
            new = f'rds_db.execute_query("SELECT {match[0]}", ({match[1]}), fetch_all=True)'
            content = content.replace(old, new)
            changes += 1
    
    # Pattern 2: SELECT with list params, no fetch
    pattern2 = r'rds_db\.execute_query\("SELECT ([^"]+)", \[([^\]]+)\]\)'
    matches = re.findall(pattern2, content)
    if matches:
        for match in matches:
            old = f'rds_db.execute_query("SELECT {match[0]}", [{match[1]}])'
            new = f'rds_db.execute_query("SELECT {match[0]}", [{match[1]}], fetch_all=True)'
            content = content.replace(old, new)
            changes += 1
    
    # Pattern 3: Fix double commas and double fetch params
    content = re.sub(r',\s*,', ',', content)
    content = re.sub(r', fetch_all=True\), fetch_one=True', ', fetch_one=True', content)
    content = re.sub(r', fetch_one=True\), fetch_all=True', ', fetch_all=True', content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, f"Fixed {changes} queries"
    
    return False, "No changes needed"


def main():
    print("\n" + "="*70)
    print("Fixing ALL execute_query Calls in Route Files")
    print("="*70)
    
    routes_dir = os.path.join(os.path.dirname(__file__), 'routes')
    route_files = glob.glob(os.path.join(routes_dir, '*.py'))
    
    fixed = 0
    skipped = 0
    
    for filepath in route_files:
        filename = os.path.basename(filepath)
        if filename.startswith('__'):
            continue
        
        changed, message = fix_file(filepath)
        
        if changed:
            print(f"  ✅ {filename}: {message}")
            fixed += 1
        else:
            print(f"  ℹ️  {filename}: {message}")
            skipped += 1
    
    print("\n" + "="*70)
    print(f"✅ Fixed {fixed} files, skipped {skipped} files")
    print("="*70)
    
    if fixed > 0:
        print("\nBackups created with .backup extension")
        print("\nRestart your backend:")
        print("  python app.py")


if __name__ == "__main__":
    main()
