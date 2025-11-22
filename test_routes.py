from app import create_app

app = create_app()

print("\nRegistered Routes:")
print("=" * 60)
for rule in app.url_map.iter_rules():
    if 'admin' in str(rule):
        print(f"{rule.methods} {rule}")
print("=" * 60)
