"""
Fix Auth Route Database Queries
Adds fetch_all=True parameter to all SELECT queries in auth.py
"""

import os
import re


def fix_auth_file():
    """Fix execute_query calls in auth.py"""
    
    print("\n" + "="*70)
    print("Fixing Auth Route Database Queries")
    print("="*70)
    
    auth_path = os.path.join(os.path.dirname(__file__), 'routes/auth.py')
    
    if not os.path.exists(auth_path):
        print("\n❌ routes/auth.py not found!")
        return False
    
    # Read file
    with open(auth_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create backup
    backup_path = auth_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n💾 Backup created: {backup_path}")
    
    # Fix patterns
    fixes = [
        # Pattern 1: execute_query with SELECT that assigns to variable
        (
            r'(\w+_result) = rds_db\.execute_query\("SELECT \* FROM users WHERE (\w+) = %s", \[(\w+)\]\)',
            r'\1 = rds_db.execute_query("SELECT * FROM users WHERE \2 = %s", [\3], fetch_all=True)'
        ),
        # Pattern 2: execute_query with SELECT in if statement
        (
            r'rds_db\.execute_query\("SELECT \* FROM users WHERE (\w+) = %s", \[(\w+)\]\)',
            r'rds_db.execute_query("SELECT * FROM users WHERE \1 = %s", [\2], fetch_all=True)'
        ),
        # Pattern 3: execute_query with tuple params
        (
            r'rds_db\.execute_query\((\w+_query), \(([^)]+)\)\)',
            r'rds_db.execute_query(\1, (\2), fetch_all=True)'
        ),
    ]
    
    changes = 0
    for pattern, replacement in fixes:
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            changes += len(matches)
            print(f"  ✅ Fixed {len(matches)} queries")
    
    if changes == 0:
        print("\n  ℹ No changes needed (queries may already be fixed)")
        return True
    
    # Write updated content
    with open(auth_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ Fixed {changes} database queries in auth.py")
    print("\nChanges made:")
    print("  • Added fetch_all=True to SELECT queries")
    print("  • Ensures queries return list of results")
    print("\nNext steps:")
    print("  1. Restart backend: python app.py")
    print("  2. Test login from frontend")
    
    return True


if __name__ == "__main__":
    print("\n🔧 Auth Route Query Fix")
    
    if fix_auth_file():
        print("\n" + "="*70)
        print("✅ Auth route fixed successfully!")
        print("="*70)
        print("\nRestart your backend server:")
        print("  python app.py")
    else:
        print("\n❌ Failed to fix auth route")
        exit(1)
