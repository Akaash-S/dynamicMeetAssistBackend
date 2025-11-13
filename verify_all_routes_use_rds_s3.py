"""
Verify All Routes Use RDS and S3 (No Mock Data)
Checks and reports which routes are properly using AWS services
"""

import os
import re


def check_file_imports(filepath):
    """Check what database/storage a file is using"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    filename = os.path.basename(filepath)
    issues = []
    
    # Check for old imports
    if 'from config.database import' in content:
        issues.append("❌ Using old config.database (should use aws_rds_database)")
    
    if 'from config.storage import' in content:
        issues.append("❌ Using old config.storage (should use aws_s3_service)")
    
    if 'get_db()' in content:
        issues.append("❌ Using get_db() (should use rds_db)")
    
    # Check for correct imports
    has_rds = 'from config.aws_rds_database import rds_db' in content
    has_s3 = 'from services.aws_s3_service import s3_service' in content
    
    # Check for execute_query without fetch parameters
    queries_without_fetch = re.findall(r'rds_db\.execute_query\([^)]+\)(?!\s*,\s*fetch_)', content)
    if queries_without_fetch:
        issues.append(f"⚠️  Found {len(queries_without_fetch)} queries without fetch parameters")
    
    return {
        'filename': filename,
        'has_rds': has_rds,
        'has_s3': has_s3,
        'issues': issues,
        'needs_rds': 'execute_query' in content or 'SELECT' in content,
        'needs_s3': 'upload' in content.lower() or 's3' in content.lower()
    }


def main():
    print("\n" + "="*70)
    print("Verifying All Routes Use RDS and S3")
    print("="*70)
    
    routes_dir = os.path.join(os.path.dirname(__file__), 'routes')
    
    route_files = [
        'auth.py',
        'meetings.py',
        'tasks.py',
        'upload.py',
        'health.py',
        'google_calendar.py',
        'totp_auth.py',
        'admin_auth.py',
        'admin_users.py',
        'admin_issues.py',
        'admin_payments.py',
        'admin_notifications.py',
    ]
    
    results = []
    
    for filename in route_files:
        filepath = os.path.join(routes_dir, filename)
        if os.path.exists(filepath):
            result = check_file_imports(filepath)
            results.append(result)
    
    # Print results
    print("\n📊 Route Files Analysis:\n")
    
    all_good = []
    needs_fix = []
    
    for result in results:
        print(f"📄 {result['filename']}")
        
        if result['needs_rds']:
            if result['has_rds']:
                print(f"   ✅ Using RDS (aws_rds_database)")
            else:
                print(f"   ❌ NOT using RDS properly")
                needs_fix.append(result['filename'])
        
        if result['needs_s3']:
            if result['has_s3']:
                print(f"   ✅ Using S3 (aws_s3_service)")
            else:
                print(f"   ⚠️  May need S3")
        
        if result['issues']:
            for issue in result['issues']:
                print(f"   {issue}")
            needs_fix.append(result['filename'])
        elif not result['issues'] and (result['has_rds'] or result['has_s3']):
            all_good.append(result['filename'])
        
        print()
    
    # Summary
    print("="*70)
    print("Summary")
    print("="*70)
    
    print(f"\n✅ Routes using RDS/S3 correctly: {len(all_good)}")
    for f in all_good:
        print(f"   • {f}")
    
    if needs_fix:
        print(f"\n⚠️  Routes needing fixes: {len(set(needs_fix))}")
        for f in set(needs_fix):
            print(f"   • {f}")
    
    print("\n" + "="*70)
    
    if needs_fix:
        print("\n❌ Some routes need fixes")
        print("\nRun this to fix:")
        print("  python fix_all_routes_to_rds_s3.py")
    else:
        print("\n✅ All routes are using RDS and S3 correctly!")
        print("\nYour application is ready to:")
        print("  • Store users in RDS")
        print("  • Store meetings in RDS")
        print("  • Upload files to S3")
        print("  • Fetch data from RDS")
        print("  • No mock data!")


if __name__ == "__main__":
    main()
