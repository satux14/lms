# Production Migration Guide - Today's Changes

## ⚠️ IMPORTANT - Read This First!

**Today's updates include:**
- Enhanced admin filters and summary tiles
- Improved customer tracker views
- Better pending payment displays
- **NO NEW DATABASE COLUMNS** (if you've run previous migrations)

## What Was Changed Today?

### Database Changes
✅ **NONE** - Today's changes were UI and filtering enhancements only!

### Code Changes
- Enhanced admin tracker page with filters (user, status, name, payment, pending)
- Added summary tiles (Total Trackers, Total Payments, Total Pending)
- Removed balance from customer views
- Added per day payment to all tracker displays
- Improved pending calculation displays

## Pre-Migration Safety Steps

### Step 1: Check Your Current Database Status

```bash
cd /Users/skumarraju/Documents/Work/progs/lending_app
python3 verify_production_status.py
```

This will show you:
- ✅ What columns exist
- ❌ What columns are missing
- 📊 How many trackers you have
- 📝 Sample tracker data

**This is READ-ONLY - it won't change anything!**

### Step 2: Backup Your Database (RECOMMENDED!)

```bash
python3 backup_before_migration.py
```

This creates timestamped backups of all your databases.

## Migration Process

### Option A: If verify_production_status.py shows "✅ ALL UP TO DATE"

**You're good to go!** Just deploy the new code:

1. Pull the latest code
2. Restart your application
3. Test the new features

### Option B: If verify_production_status.py shows "⚠️ NEEDS MIGRATION"

Run the complete migration:

```bash
python3 migrate_complete_tracker_system.py
```

This script will:
- ✅ Add any missing columns
- ✅ Set appropriate default values
- ✅ Preserve all existing data
- ❌ Never delete or modify existing entries

## What the Migration Does

### If `per_day_payment` column is missing:
- Adds the column
- Sets defaults based on tracker type:
  - 50K trackers → ₹500/day
  - 1L trackers → ₹1000/day
  - No Reinvest → ₹3000/day

### If `is_closed_by_user` column is missing:
- Adds the column
- Sets all existing trackers to `False` (active/visible)

## Post-Migration Steps

1. **Verify Migration Success**
   ```bash
   python3 verify_production_status.py
   ```
   Should now show "✅ ALL UP TO DATE"

2. **Deploy New Code**
   - Pull the latest code from git
   - Restart your application

3. **Test New Features**
   - Log in as admin
   - Go to Daily Trackers page
   - You should see:
     - 3 summary tiles at the top
     - Filter panel with 6 filter options
     - Pending column in the table
     - Days Paid and Total Payments columns

## What Each Column Does

| Column | Purpose | When Added |
|--------|---------|------------|
| `id` | Primary key | Initial creation |
| `user_id` | Links to user | Initial creation |
| `tracker_name` | Tracker display name | Initial creation |
| `tracker_type` | 50K/1L/No Reinvest | Initial creation |
| `investment` | Investment amount | Initial creation |
| `scheme_period` | Duration in days | Initial creation |
| `per_day_payment` | **Daily payment amount** | Previous update |
| `start_date` | Start date | Initial creation |
| `filename` | Excel file name | Initial creation |
| `created_at` | Creation timestamp | Initial creation |
| `updated_at` | Last update time | Initial creation |
| `is_active` | Soft delete flag | Initial creation |
| `is_closed_by_user` | **User hide/close flag** | Previous update |

## Safety Guarantees

✅ **What the migration WILL do:**
- Add missing columns only
- Set safe default values
- Preserve all existing data
- Work on all instances (prod, dev, testing)

❌ **What the migration will NEVER do:**
- Delete any data
- Modify existing entries (except adding default values to new columns)
- Drop any tables
- Remove any columns
- Change existing column types

## Troubleshooting

### "Table already exists" or "Column already exists"
✅ **This is GOOD!** The script detects this and skips it safely.

### "Database is locked"
- Stop your application first
- Then run the migration
- Restart application after

### "Permission denied"
- Check file permissions on your database files
- Ensure you have write access to the instances directory

### Migration fails halfway
- The script is safe to re-run
- It will skip already-completed steps
- No data will be lost

## Quick Reference

```bash
# 1. Check status (safe, no changes)
python3 verify_production_status.py

# 2. Backup (recommended)
python3 backup_before_migration.py

# 3. Run migration (if needed)
python3 migrate_complete_tracker_system.py

# 4. Verify success
python3 verify_production_status.py
```

## Need Help?

If you see any errors:
1. Don't panic - no data has been modified
2. Read the error message carefully
3. Check the troubleshooting section above
4. The migration is safe to run multiple times

## Summary

**Most likely scenario:** If you've been running the app with trackers and have run previous migrations, your database is already up to date! Just verify with the status check script and deploy the new code.

**New features you'll get:**
- Admin dashboard with summary tiles
- Advanced filtering (6 filter options)
- Better pending payment visibility
- Days paid column
- Cleaner customer views (no balance)
- Per day payment info everywhere

