# Daily Tracker Migration Guide - Safe Production Deployment

## ⚠️ SAFETY GUARANTEE

**This migration is 100% SAFE because:**

1. ✅ It only **ADDS** a new table called `daily_tracker`
2. ✅ It does **NOT** modify any existing tables
3. ✅ It does **NOT** delete any data
4. ✅ It does **NOT** change any existing data
5. ✅ All your existing loans, payments, users, and interest rates remain untouched

The migration simply creates a new table alongside your existing tables.

## What Gets Created

The migration adds ONE new table:

```sql
CREATE TABLE daily_tracker (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,  -- Links to existing user table
    tracker_name VARCHAR(200),
    tracker_type VARCHAR(50),
    investment DECIMAL(15, 2),
    scheme_period INTEGER,
    start_date DATE,
    filename VARCHAR(255),
    created_at DATETIME,
    updated_at DATETIME,
    is_active BOOLEAN,
    FOREIGN KEY (user_id) REFERENCES user(id)
)
```

## Step-by-Step Migration Process

### Step 1: Verify What Will Happen (Dry Run)

First, see exactly what the migration will do WITHOUT making any changes:

```bash
cd /Users/skumarraju/Documents/Work/progs/lending_app
python3 verify_migration_plan.py
```

**This script:**
- ✅ Shows current database state
- ✅ Shows what will be added
- ✅ Makes NO changes
- ✅ Confirms safety guarantees

**Expected output:**
- Lists all existing tables
- Shows that `daily_tracker` doesn't exist
- Confirms it will only ADD the new table

---

### Step 2: Backup All Databases

Create backups before migration (just to be extra safe):

```bash
python3 backup_before_migration.py
```

**This script:**
- ✅ Creates timestamped backups of all databases
- ✅ Stores backups in `instance/{instance}/backups/`
- ✅ Verifies backup was created successfully

**Backup location:**
- `instance/prod/backups/lending_app_prod_pre_daily_tracker_migration_YYYYMMDD_HHMMSS.db`
- `instance/dev/backups/lending_app_dev_pre_daily_tracker_migration_YYYYMMDD_HHMMSS.db`
- `instance/testing/backups/lending_app_testing_pre_daily_tracker_migration_YYYYMMDD_HHMMSS.db`

---

### Step 3: Run the Migration

Now run the actual migration:

```bash
python3 migrate_daily_tracker.py
```

**This script:**
- ✅ Adds the `daily_tracker` table to each instance
- ✅ Skips if table already exists
- ✅ Shows success/failure for each instance

**Expected output:**
```
============================================================
DAILY TRACKER DATABASE MIGRATION
============================================================

→ Initializing application...
✓ Application initialized

============================================================
Migrating instance: prod
============================================================
Database URI: sqlite:///.../instance/prod/database/lending_app_prod.db
→ Creating DailyTracker table in prod database...
✓ DailyTracker table created successfully in prod database

[Similar for dev and testing]

============================================================
MIGRATION SUMMARY
============================================================
prod: ✓ SUCCESS
dev: ✓ SUCCESS
testing: ✓ SUCCESS

✓ All instances migrated successfully!
```

---

### Step 4: Verify Migration Success

Verify everything worked correctly:

```bash
python3 verify_migration_success.py
```

**This script:**
- ✅ Confirms `daily_tracker` table exists
- ✅ Verifies table structure is correct
- ✅ Checks existing tables are still intact
- ✅ Shows row counts for existing tables

**Expected output:**
```
============================================================
Instance: prod
============================================================
✓ daily_tracker table exists
✓ Table structure is correct

Existing tables status:
  ✓ user: 5 rows
  ✓ loan: 12 rows
  ✓ payment: 48 rows
  ✓ interest_rate: 3 rows
  ✓ pending_interest: 15 rows

✓ All existing tables intact
📊 Current trackers in database: 0

============================================================
VERIFICATION SUMMARY
============================================================
prod: ✓ SUCCESS

✓ MIGRATION SUCCESSFUL!
```

---

### Step 5: Restart Application

Restart your application to load the new code:

```bash
python3 app_multi.py
```

---

### Step 6: Test the Feature

1. Open browser to http://127.0.0.1:8080/prod/
2. Log in as admin
3. Look for "Daily Trackers" in the left sidebar
4. Click "Create Tracker"
5. Create a test tracker for a user
6. Verify the Excel file is created
7. Add an entry to the tracker
8. Log in as that user and verify they can see their tracker

---

## If Something Goes Wrong

### Rollback (Restore from Backup)

If you need to rollback (though this should not be necessary):

```bash
# Stop the application first

# Restore production database
cp instance/prod/backups/lending_app_prod_pre_daily_tracker_migration_*.db \
   instance/prod/database/lending_app_prod.db

# Restart application
```

### Common Issues and Solutions

#### Issue: Python command not found
**Solution:** Use `python3` instead of `python`

#### Issue: Module import errors
**Solution:** Ensure you're in the lending_app directory:
```bash
cd /Users/skumarraju/Documents/Work/progs/lending_app
```

#### Issue: Database locked
**Solution:** Stop the application before running migration:
```bash
# Find and kill the process
ps aux | grep app_multi
kill <process_id>

# Then run migration
```

#### Issue: Migration says table already exists
**Solution:** This is fine! It means the table is already there. Skip to verification step.

---

## File Checklist

Make sure these files exist before starting:

```
✓ app_multi.py (updated with DailyTracker model)
✓ daily-trackers/tracker_manager.py (new file)
✓ daily-trackers/template/DailyTrackerTemplate.xlsx (existing template)
✓ backup_before_migration.py (new script)
✓ verify_migration_plan.py (new script)
✓ migrate_daily_tracker.py (new script)
✓ verify_migration_success.py (new script)
✓ templates/admin/daily_trackers.html (new)
✓ templates/admin/create_daily_tracker.html (new)
✓ templates/admin/view_daily_tracker.html (new)
✓ templates/admin/add_tracker_entry.html (new)
✓ templates/customer/daily_tracker.html (new)
```

---

## Production Deployment Checklist

- [ ] Read this guide completely
- [ ] Run verify_migration_plan.py (dry run)
- [ ] Review the output - confirm it's safe
- [ ] Run backup_before_migration.py
- [ ] Verify backups were created
- [ ] Stop the application (if running)
- [ ] Run migrate_daily_tracker.py
- [ ] Review the output - confirm success
- [ ] Run verify_migration_success.py
- [ ] Review the output - confirm all checks pass
- [ ] Restart the application
- [ ] Test the feature as admin
- [ ] Test the feature as a regular user
- [ ] Monitor application logs for any errors
- [ ] Keep backups for at least 30 days

---

## Support

If you encounter any issues:

1. Check the error message carefully
2. Review the troubleshooting section above
3. Check application logs
4. Verify file permissions
5. Ensure database is not locked

---

## Summary

**Time required:** 5-10 minutes

**Risk level:** Very Low (only adds new table, doesn't touch existing data)

**Reversible:** Yes (via backup restoration)

**Downtime required:** Minimal (only during restart)

**Commands to run in order:**
```bash
cd /Users/skumarraju/Documents/Work/progs/lending_app
python3 verify_migration_plan.py      # Check what will happen
python3 backup_before_migration.py    # Backup databases
python3 migrate_daily_tracker.py      # Run migration
python3 verify_migration_success.py   # Verify success
python3 app_multi.py                  # Restart app
```

---

**You're ready to safely migrate! All your existing data will remain intact.**

