# User Migration Guide - Fresh RDS Database

## Important: Database is Empty!

Since we migrated from Neon to AWS RDS, **all tables are empty**. This means:

- ❌ No existing users
- ❌ No meetings
- ❌ No tasks
- ❌ No data from Neon database

## What You Need to Do

### Step 1: Register Again

**All users must register again** because the RDS database is fresh.

1. Go to the login page
2. Click "Sign in with Google"
3. This will create a NEW user account in RDS
4. Your old Neon data is NOT migrated

### Step 2: Start Fresh

- Upload new meetings
- Create new tasks
- Set up 2FA again
- Reconnect Google Calendar

## Why 500 Errors?

The 500 errors happen because:

1. **User doesn't exist in RDS** - Need to register first
2. **No meetings** - Database is empty
3. **No tasks** - Database is empty
4. **Queries expecting data** - But tables are empty

## Fix for Developers

Update all route files to handle empty database gracefully:

### Pattern to Fix:

**Before (causes 500 error):**
```python
user = rds_db.execute_query("SELECT * FROM users WHERE id = %s", (user_id,), fetch_one=True)
# If user is None, accessing user['email'] causes error
email = user['email']  # ❌ Error if user is None
```

**After (handles empty database):**
```python
user = rds_db.execute_query("SELECT * FROM users WHERE id = %s", (user_id,), fetch_one=True)
if not user:
    return jsonify({'error': 'User not found'}), 404
email = user['email']  # ✅ Safe
```

## Quick Fix Script

Run this to fix all route files:

```bash
cd backend
python fix_empty_database_handling.py
```

This will:
- Add null checks for all database queries
- Return proper 404 errors instead of 500
- Handle empty results gracefully

## Testing After Fix

1. **Register new user**: Should work ✅
2. **View dashboard**: Should show empty state ✅
3. **Upload meeting**: Should work ✅
4. **View meetings**: Should show the uploaded meeting ✅

## Data Migration (Optional)

If you want to migrate data from Neon to RDS:

1. Export data from Neon
2. Transform to RDS schema (UUID format)
3. Import to RDS

**Script**: `migrate_neon_to_rds.py` (to be created)

## Summary

✅ **Solution**: Register as a new user
✅ **Fix**: Update routes to handle empty database
✅ **Result**: Application works with fresh RDS database

---

**Next**: Run `python fix_empty_database_handling.py` to fix all routes
