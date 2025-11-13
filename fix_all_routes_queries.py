"""
Fix All Route Files - Add fetch parameters to execute_query calls
This script updates ALL route files to use proper RDS query parameters
"""

import os
import re
from pathlib import Path


def fix_route_file(filepath):
    """Fix execute_query calls in a single route file"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes = 0
    
    # Pattern 1: execute_query with SELECT that expects single row
    # Look for patterns like: variable = rds_db.execute_query("SELECT...", (...))
    # followed by accessing [0] or checking if result exists
    
    # First, find all execute_query calls
    pattern = r'rds_db\.execute_query\(([^)]+)\)'
    matches = list(re.finditer(pattern, content))
    
    for match in reversed(matches):  # Process in reverse to maintain positions
        query_call = match.group(0)
        query_args = match.group(1)
        
        # Skip if already has fetch parameter
        if 'fetch_one' in query_call or 'fetch_all' in query_call:
            continue
        
        # Check if this is a SELECT query
        if 'SELECT' not in query_call.upper():
            continue
        
        # Determine if it should be fetch_one or fetch_all
        # Look at context after the query
        start_pos = match.end()
        context_after = content[start_pos:start_pos+200]
        
        # If followed by [0] access, it expects multiple rows but uses first
        # If followed by direct attribute access, it expects single row
        if '[0]' in context_after or 'if not' in context_after:
            # Likely expects list of results
            new_call = f'rds_db.execute_query({query_args}, fetch_all=True)'
        else:
            # Check if variable is used with direct attribute access
            # Get the variable name
            line_start = content.rfind('\n', 0, match.start()) + 1
            line = content[line_start:match.start()]
            if '=' in line:
                var_name = line.split('=')[0].strip()
                # Look for usage of this variable
                usage_pattern = f'{var_name}\\[' 
                if re.search(usage_pattern, context_after):
                    new_call = f'rds_db.execute_query({query_args}, fetch_all=True)'
                else:
                    new_call = f'rds_db.execute_query({query_args}, fetch_one=True)'
            else:
                new_call = f'rds_db.execute_query({query_args}, fetch_all=True)'
        
        # Replace the call
        content = content[:match.start()] + new_call + content[match.end():]
        changes += 1
    
    if changes > 0:
        # Create backup
        backup_path = str(filepath) + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # Write updated content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return changes
    
    return 0


def main():
    print("\n" + "="*70)
    print("Fixing All Route Files - RDS Query Parameters")
    print("="*70)
    
    routes_dir = Path(__file__).parent / 'routes'
    
    if not routes_dir.exists():
        print(f"\n❌ Routes directory not found: {routes_dir}")
        return False
    
    # Get all Python files in routes directory
    route_files = list(routes_dir.glob('*.py'))
    route_files = [f for f in route_files if not f.name.startswith('__')]
    
    print(f"\n📁 Found {len(route_files)} route files")
    
    total_changes = 0
    fixed_files = []
    
    for route_file in route_files:
        print(f"\n📄 Processing: {route_file.name}")
        changes = fix_route_file(route_file)
        
        if changes > 0:
            print(f"  ✅ Fixed {changes} queries")
            total_changes += changes
            fixed_files.append(route_file.name)
        else:
            print(f"  ℹ️  No changes needed")
    
    print("\n" + "="*70)
    print(f"✅ Fixed {total_changes} queries in {len(fixed_files)} files")
    print("="*70)
    
    if fixed_files:
        print("\nFixed files:")
        for filename in fixed_files:
            print(f"  • {filename}")
        
        print("\nBackups created with .backup extension")
        print("\nNext steps:")
        print("  1. Restart backend: python app.py")
        print("  2. Test all endpoints")
        print("  3. If issues occur, restore from .backup files")
    
    return True


if __name__ == "__main__":
    print("\n🔧 RDS Query Parameter Fix - All Routes")
    
    if main():
        print("\n✅ All route files have been updated!")
        print("\nRestart your backend server:")
        print("  python app.py")
    else:
        print("\n❌ Failed to fix route files")
        exit(1)
