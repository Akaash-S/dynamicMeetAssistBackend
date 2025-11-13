"""
Analyze Migration Needs
Shows what needs to be updated in each file without making changes
"""

import os
import re

def analyze_file(filepath):
    """Analyze a single file for migration needs"""
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    
    # Check imports
    if 'from config.database import' in content:
        issues.append({
            'type': 'import',
            'severity': 'high',
            'message': 'Uses old SQLite database import',
            'fix': 'Replace with: from config.aws_rds_database import rds_db'
        })
    
    if 'from config.storage import' in content:
        issues.append({
            'type': 'import',
            'severity': 'high',
            'message': 'Uses old local storage import',
            'fix': 'Replace with: from services.aws_s3_service import s3_service'
        })
    
    # Check SQL placeholders
    sql_placeholders = re.findall(r'["\'].*?\?.*?["\']', content)
    if sql_placeholders:
        issues.append({
            'type': 'sql',
            'severity': 'high',
            'message': f'Found {len(sql_placeholders)} SQL queries with ? placeholders',
            'fix': 'Replace ? with %s for PostgreSQL'
        })
    
    # Check database calls
    if 'get_db()' in content:
        count = content.count('get_db()')
        issues.append({
            'type': 'database',
            'severity': 'high',
            'message': f'Found {count} get_db() calls',
            'fix': 'Replace with rds_db.execute_query()'
        })
    
    if '.cursor()' in content:
        count = content.count('.cursor()')
        issues.append({
            'type': 'database',
            'severity': 'medium',
            'message': f'Found {count} .cursor() calls',
            'fix': 'Use rds_db.execute_query() instead'
        })
    
    if '.commit()' in content:
        count = content.count('.commit()')
        issues.append({
            'type': 'database',
            'severity': 'low',
            'message': f'Found {count} .commit() calls',
            'fix': 'Remove (automatic in rds_db)'
        })
    
    if '.fetchone()' in content:
        count = content.count('.fetchone()')
        issues.append({
            'type': 'database',
            'severity': 'medium',
            'message': f'Found {count} .fetchone() calls',
            'fix': 'Use fetch_one=True parameter'
        })
    
    if '.fetchall()' in content:
        count = content.count('.fetchall()')
        issues.append({
            'type': 'database',
            'severity': 'medium',
            'message': f'Found {count} .fetchall() calls',
            'fix': 'Use fetch_all=True parameter'
        })
    
    # Check storage calls
    if 'storage.' in content:
        count = content.count('storage.')
        issues.append({
            'type': 'storage',
            'severity': 'high',
            'message': f'Found {count} storage calls',
            'fix': 'Replace with s3_service methods'
        })
    
    return issues

def main():
    print("="*70)
    print("Migration Analysis Report")
    print("="*70)
    print("\nAnalyzing backend route files for migration needs...\n")
    
    route_files = [
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
        'routes/data_export.py',
        'routes/two_factor_auth.py',
    ]
    
    total_issues = 0
    files_needing_update = []
    files_already_updated = []
    
    for route_file in route_files:
        filepath = os.path.join(os.path.dirname(__file__), route_file)
        issues = analyze_file(filepath)
        
        if issues is None:
            print(f"⚠ {route_file} - NOT FOUND")
            continue
        
        if not issues:
            print(f"✓ {route_file} - Already updated or no issues")
            files_already_updated.append(route_file)
            continue
        
        files_needing_update.append(route_file)
        total_issues += len(issues)
        
        print(f"\n{'='*70}")
        print(f"📄 {route_file}")
        print(f"{'='*70}")
        
        # Group by severity
        high = [i for i in issues if i['severity'] == 'high']
        medium = [i for i in issues if i['severity'] == 'medium']
        low = [i for i in issues if i['severity'] == 'low']
        
        if high:
            print(f"\n🔴 HIGH PRIORITY ({len(high)} issues):")
            for issue in high:
                print(f"  • {issue['message']}")
                print(f"    Fix: {issue['fix']}")
        
        if medium:
            print(f"\n🟡 MEDIUM PRIORITY ({len(medium)} issues):")
            for issue in medium:
                print(f"  • {issue['message']}")
                print(f"    Fix: {issue['fix']}")
        
        if low:
            print(f"\n🟢 LOW PRIORITY ({len(low)} issues):")
            for issue in low:
                print(f"  • {issue['message']}")
                print(f"    Fix: {issue['fix']}")
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"\nTotal files analyzed: {len(route_files)}")
    print(f"Files needing updates: {len(files_needing_update)}")
    print(f"Files already updated: {len(files_already_updated)}")
    print(f"Total issues found: {total_issues}")
    
    if files_needing_update:
        print(f"\n📋 Files that need updating:")
        for f in files_needing_update:
            print(f"  • {f}")
    
    if files_already_updated:
        print(f"\n✓ Files already updated:")
        for f in files_already_updated:
            print(f"  • {f}")
    
    print(f"\n{'='*70}")
    print("NEXT STEPS")
    print(f"{'='*70}")
    print("\n1. Review the issues above")
    print("2. See MIGRATION_GUIDE_RDS_S3.md for detailed instructions")
    print("3. Update files manually or run: python migrate_to_rds_s3.py")
    print("4. Test each endpoint after updating")
    print("5. Update frontend if needed")
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    main()
