"""
Remove duplicate stats functions from both meetings.py and tasks.py
"""

import os


def remove_duplicate_function(filepath, function_name):
    """Remove duplicate function from a file"""
    
    print(f"\n{'='*70}")
    print(f"Processing: {filepath}")
    print('='*70)
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Find all occurrences of the function
    func_indices = []
    for i, line in enumerate(lines):
        if line.strip().startswith(f'def {function_name}'):
            func_indices.append(i)
    
    print(f"Found {len(func_indices)} '{function_name}' functions at lines: {[i+1 for i in func_indices]}")
    
    if len(func_indices) < 2:
        print(f"✅ No duplicates found")
        return False
    
    # Keep the first one, remove all others
    # Start from the last duplicate and work backwards
    for func_index in reversed(func_indices[1:]):
        # Find the decorator before the function
        start_remove = func_index
        for i in range(func_index - 1, -1, -1):
            if lines[i].strip().startswith('@'):
                start_remove = i
                break
        
        # Find the end of the function (next decorator, next function, or end of file)
        end_remove = len(lines)
        for i in range(func_index + 1, len(lines)):
            if lines[i].strip() and not lines[i].startswith(' ') and not lines[i].startswith('\t'):
                # Found a non-indented line (next function or decorator)
                if lines[i].strip().startswith('@') or lines[i].strip().startswith('def '):
                    end_remove = i
                    break
        
        print(f"Removing lines {start_remove+1} to {end_remove} (duplicate)")
        
        # Remove the duplicate
        lines = lines[:start_remove] + lines[end_remove:]
    
    new_content = '\n'.join(lines)
    
    # Create backup
    backup_file = filepath + '.backup'
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"💾 Backup created: {backup_file}")
    
    # Write the fixed content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Removed {len(func_indices) - 1} duplicate(s)")
    return True


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    files_to_fix = [
        (os.path.join(script_dir, 'routes', 'meetings.py'), 'get_meeting_stats'),
        (os.path.join(script_dir, 'routes', 'tasks.py'), 'get_task_stats'),
    ]
    
    print("\n" + "="*70)
    print("Removing Duplicate Stats Functions")
    print("="*70)
    
    fixed_count = 0
    
    for filepath, function_name in files_to_fix:
        if os.path.exists(filepath):
            if remove_duplicate_function(filepath, function_name):
                fixed_count += 1
        else:
            print(f"\n❌ File not found: {filepath}")
    
    print("\n" + "="*70)
    print(f"✅ Fixed {fixed_count} file(s)")
    print("="*70)
    
    if fixed_count > 0:
        print("\nNext steps:")
        print("  1. Restart backend: python app.py")
        print("  2. Refresh frontend")
        print("  3. All endpoints should work!")


if __name__ == "__main__":
    main()
