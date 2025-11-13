# Emergency Fix - RDS Connection Timeout

## The Problem

Your backend is getting **Connection Timeout** when trying to connect to RDS:
```
connection to server at "meetingmind.ctousuwme9up.ap-south-1.rds.amazonaws.com" (13.204.199.127), port 5432 failed: Connection timed out
```

This means:
- ✅ RDS instance exists
- ✅ Credentials are correct
- ❌ **Your IP is blocked by AWS Security Group**

## The Solution

You MUST fix this in AWS Console. There's no code fix for this.

### Option 1: Add Your IP (Recommended)

1. Go to: https://console.aws.amazon.com/rds/
2. Click on database: `meetingmind`
3. Under "Connectivity & security" → Click the VPC security group link
4. Click "Edit inbound rules"
5. Click "Add rule"
6. Set:
   - Type: PostgreSQL
   - Port: 5432
   - Source: **My IP** (auto-detects your IP)
7. Click "Save rules"
8. Wait 1-2 minutes

### Option 2: Allow All IPs (Testing Only)

⚠️ **WARNING**: This is insecure! Only use for testing.

Same steps as above, but set:
- Source: `0.0.0.0/0` (allows all IPs)

### Option 3: Check if RDS is Publicly Accessible

1. Go to RDS → Your database
2. Click "Modify"
3. Under "Connectivity":
   - Set "Publicly accessible" to **Yes**
4. Click "Continue" → "Apply immediately"

## Verify the Fix

After making changes, test:

```bash
python test_rds_connection.py
```

You should see:
```
✅ Connection successful!
✅ PostgreSQL Version: ...
```

## Why This Happens

AWS RDS has a firewall (Security Group) that blocks all connections by default. You must explicitly allow your IP address to connect.

## Current Status

- ❌ Backend cannot connect to RDS
- ❌ All database queries fail with 500 errors
- ❌ Users cannot login/register
- ❌ No data can be saved or retrieved

## After Fix

- ✅ Backend connects to RDS
- ✅ All endpoints return 200
- ✅ Users can login/register
- ✅ Data saves and loads correctly

---

**This is an AWS infrastructure issue, not a code issue. You must fix it in AWS Console.**
