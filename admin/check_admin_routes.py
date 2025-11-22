import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from admin.app import create_admin_app

app = create_admin_app()

print("\n=== ADMIN ROUTES ===")
for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
    methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
    print(f"{methods:10} {rule}")
