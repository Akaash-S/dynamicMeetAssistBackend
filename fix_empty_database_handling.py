"""
Fix Empty Database Handling in All Routes
Adds proper null checks and error handling for empty RDS database
"""

import os
import re


def fix_route_file(filepath):
    """Add null checks and proper error handling"""
    
    filename = os.path.basename(filepath)
    print(f"\n📄 Fixing: {filename}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    changes = 0
    
    # Create backup
    backup_path = filepath + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(original)
    
    # Pattern 1: Add null check after fetch_one queries
    # Find: result = rds_db.execute_query(..., fetch_one=True)
    # Add: if not result: return error
    
    pattern1 = r'(\s+)(\w+) = rds_db\.execute_query\([^)]+\), fetch_one=True\)\n(\s+)(\w+) = \2\[\'(\w+)\'\]'
    
    def add_null_check(match):
        indent = match.group(1)
        var_name = match.group(2)
        next_indent = match.group(3)
        next_var = match.group(4)
        key = match.group(5)
        
        return f'''{indent}{var_name} = rds_db.execute_query(..., fetch_one=True)
{indent}if not {var_name}:
{indent}    return jsonify({{'error': 'Resource not found'}}), 404
{next_indent}{next_var} = {var_name}['{key}']'''
    
    # For now, let's do a simpler fix - just ensure all routes return proper errors
    
    # Fix 1: Ensure all execute_query with fetch_one have null checks
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # Check if this line has fetch_one=True
        if 'fetch_one=True' in line and '=' in line:
            # Get the variable name
            var_match = re.match(r'\s+(\w+)\s*=\s*rds_db\.execute_query', line)
            if var_match:
                var_name = var_match.group(1)
                indent = len(line) - len(line.lstrip())
                indent_str = ' ' * indent
                
                # Check if next line already has null check
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if f'if not {var_name}' not in next_line and f'if {var_name}' not in next_line:
                        # Add null check
                        new_lines.append(f'{indent_str}if not {var_name}:')
                        new_lines.append(f'{indent_str}    return jsonify({{"error": "Resource not found"}}), 404')
                        changes += 1
        
        i += 1
    
    if changes > 0:
        content = '\n'.join(new_lines)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ Added {changes} null checks")
        return True
    else:
        print(f"  ℹ️  No changes needed")
        return False


def main():
    print("="*70)
    print("Fixing Empty Database Handling in All Routes")
    print("="*70)
    print("\nThis will add null checks to prevent 500 errors on empty database")
    
    routes_dir = os.path.join(os.path.dirname(__file__), 'routes')
    
    route_files = [
        'auth.py',
        'meetings.py',
        'tasks.py',
        'google_calendar.py',
        'admin_users.py',
        'admin_issues.py',
        'admin_payments.py',
    ]
    
    fixed = 0
    
    for filename in route_files:
        filepath = os.path.join(routes_dir, filename)
        if os.path.exists(filepath):
            if fix_route_file(filepath):
                fixed += 1
    
    print("\n" + "="*70)
    print(f"✅ Fixed {fixed} route files")
    print("="*70)
    
    print("\n📋 What was done:")
    print("  • Added null checks after fetch_one queries")
    print("  • Return 404 instead of 500 for missing resources")
    print("  • Handle empty database gracefully")
    
    print("\n🔄 Next steps:")
    print("  1. Restart backend: python app.py")
    print("  2. Register as new user (database is empty)")
    print("  3. Test all endpoints")
    
    print("\n⚠️  Important:")
    print("  • All users must register again")
    print("  • No data from Neon database")
    print("  • Start fresh with RDS")


if __name__ == "__main__":
    main()
