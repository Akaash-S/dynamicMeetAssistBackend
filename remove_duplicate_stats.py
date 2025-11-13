"""
Remove duplicate get_meeting_stats function from meetings.py
"""

import os

# Get the correct path
script_dir = os.path.dirname(os.path.abspath(__file__))
meetings_file = os.path.join(script_dir, 'routes', 'meetings.py')

print(f"Reading: {meetings_file}")

# Read the file
with open(meetings_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Find all occurrences of the stats function
lines = content.split('\n')

# Find the indices of both stats functions
stats_indices = []
for i, line in enumerate(lines):
    if line.strip().startswith('def get_meeting_stats'):
        stats_indices.append(i)

print(f"Found {len(stats_indices)} get_meeting_stats functions at lines: {[i+1 for i in stats_indices]}")

if len(stats_indices) == 2:
    # Keep the first one, remove the second one
    # Find the end of the second function (next @meetings_bp.route or end of file)
    start_remove = stats_indices[1] - 2  # Include the @meetings_bp.route decorator
    
    # Find where to stop removing (next function or end of file)
    end_remove = len(lines)
    for i in range(stats_indices[1] + 1, len(lines)):
        if lines[i].strip().startswith('@meetings_bp.route') or lines[i].strip().startswith('def '):
            end_remove = i
            break
    
    print(f"Removing lines {start_remove+1} to {end_remove}")
    
    # Remove the duplicate
    new_lines = lines[:start_remove] + lines[end_remove:]
    new_content = '\n'.join(new_lines)
    
    # Create backup
    backup_file = meetings_file + '.backup'
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Backup created: {backup_file}")
    
    # Write the fixed content
    with open(meetings_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Duplicate removed successfully!")
    print(f"Removed {end_remove - start_remove} lines")
    
else:
    print("❌ Expected 2 functions, found", len(stats_indices))
