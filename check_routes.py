"""Check what routes are actually registered"""
from app import create_app

app = create_app()

print("\n=== ALL REGISTERED ROUTES ===")
for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
    methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
    print(f"{methods:10} {rule}")

print("\n=== ADMIN ROUTES ONLY ===")
admin_routes = [rule for rule in app.url_map.iter_rules() if 'admin' in str(rule)]
if admin_routes:
    for rule in admin_routes:
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        print(f"{methods:10} {rule}")
else:
    print("NO ADMIN ROUTES FOUND!")
