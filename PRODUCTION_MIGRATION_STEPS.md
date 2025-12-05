# Production Migration Steps - Cashback Feature

## 🎯 Quick Overview

This migration adds 6 new tables to your production database:
- `cashback_transaction`
- `loan_cashback_config`
- `tracker_entry`
- `tracker_cashback_config`
- `user_payment_method`
- `cashback_redemption`

**✅ SAFE:** Only adds new tables, does NOT modify existing data.

---

## 📋 Pre-Migration Checklist

- [ ] Code has been tested in dev environment
- [ ] All changes are committed and pushed to repository
- [ ] You have SSH/access to production server
- [ ] You know where production database is located
- [ ] You have backup access configured

**Note:** Database files (`.db`) are **NOT** in the git repository (they're in `.gitignore`). Each server has its own separate database file. The migration must be run on each server separately.

---

## 🚀 Step-by-Step Migration Process

### ⚠️ CRITICAL: Where to Run Migration

**The migration script MUST be run on the server where your production database actually exists.**

**Why?** The migration script uses relative paths (`instances/prod/database/lending_app_prod.db`). If you run it locally, it will:
- ❌ Create or modify a **local database file** (not your production database)
- ❌ Show "tables already exist" if you have a local copy with those tables
- ❌ **NOT affect your actual production database**

**✅ Correct approach:**
1. **SSH to your production server** where the database file actually lives
2. **OR run inside Docker container** if your database is in a Docker volume
3. **OR run on the host** where Docker volumes are mounted

**How to identify where your production database is:**
- **Docker setup:** Check `docker-compose.prod.yml` - it shows where `instances/` is mounted
  - Example: `./instances:/app/instances` means database is at `./instances/prod/database/` on the host
- **Direct setup:** Database is at `instances/prod/database/lending_app_prod.db` relative to your app directory
- **Inside Docker:** Database is at `/app/instances/prod/database/lending_app_prod.db`

**To verify you're on the right server:**
```bash
# Check database file size - should match your production data size
ls -lh instances/prod/database/lending_app_prod.db

# If it's very small (< 1MB) or doesn't exist, you might be on wrong server
```

### Step 1: Connect to Production Server

**Option A: SSH to Production Server**
```bash
# SSH into your production server
ssh your-production-server

# Navigate to application directory
cd /path/to/lms-dev
```

**Option B: Access Docker Container (if database is in container)**
```bash
# If using Docker, access the running container
docker exec -it lending-management-system-prod bash

# Inside container, navigate to app directory
cd /app
```

**Option C: Run on Host (if Docker uses bind mount)**
```bash
# If Docker uses bind mount (./instances:/app/instances)
# You can run migration on the host where the volume is mounted
# Just make sure you're in the directory where instances/ folder exists
cd /path/to/lms-dev  # Where instances/ folder is located
```

### Step 2: Verify Production Database Location

**Before proceeding, verify you're on the right server with the right database:**

```bash
# Check if production database exists
ls -lh instances/prod/database/lending_app_prod.db

# Check database size (should match your production data)
# If it's very small or doesn't exist, you might be on the wrong server
```

**If using Docker:**
```bash
# Check database inside container
docker exec lending-management-system-prod ls -lh /app/instances/prod/database/lending_app_prod.db

# Or check on host if using bind mount
ls -lh /path/to/instances/prod/database/lending_app_prod.db
```

### Step 3: Stop the Application (Important!)

**If using Docker:**
```bash
# Stop production container
docker compose -f docker-compose.prod.yml down
```

**If running directly:**
```bash
# Stop the Flask application
# (Use your process manager: systemd, supervisor, etc.)
sudo systemctl stop lending-app
# OR
pkill -f "python.*app_multi.py"
```

**Why?** Prevents database locks during migration.

---

### Step 4: Create Database Backup

**Option A: Using the backup script (if available)**
```bash
python3 backup_before_migration.py
```

**Option B: Manual backup**
```bash
# Create backup directory if it doesn't exist
mkdir -p instances/prod/backups

# Create timestamped backup
cp instances/prod/database/lending_app_prod.db \
   instances/prod/backups/lending_app_prod_pre_cashback_$(date +%Y%m%d_%H%M%S).db

# Verify backup was created
ls -lh instances/prod/backups/lending_app_prod_pre_cashback_*.db
```

**Expected output:**
```
-rw-r--r-- 1 user user 2.5M Dec  5 10:30 instances/prod/backups/lending_app_prod_pre_cashback_20241205_103045.db
```

---

### Step 5: Dry Run (Verify What Will Happen)

**Run a dry run first to see what the migration will do:**

```bash
python3 migrate_cashback_tables.py prod --dry-run
```

**Expected output:**
```
============================================================
CASHBACK TABLES MIGRATION
============================================================

This migration will add the following NEW tables:
  - cashback_transaction
  - loan_cashback_config
  - tracker_entry
  - tracker_cashback_config
  - user_payment_method
  - cashback_redemption

⚠️  SAFETY GUARANTEE:
  ✅ Only ADDS new tables
  ✅ Does NOT modify existing tables
  ✅ Does NOT delete any data
  ✅ Safe to run multiple times

🔍 DRY RUN MODE - No changes will be made

Instances to migrate: prod

============================================================
Migrating instance: prod
  [DRY RUN MODE - No changes will be made]
============================================================
Database URI: sqlite:///instances/prod/database/lending_app_prod.db
→ [DRY RUN] Would create cashback_transaction table
→ [DRY RUN] Would create loan_cashback_config table
... (and so on)

[DRY RUN SUMMARY]
  Tables that would be created: 6
    - cashback_transaction
    - loan_cashback_config
    - tracker_entry
    - tracker_cashback_config
    - user_payment_method
    - cashback_redemption
  Tables that already exist: 0
```

**✅ If dry run looks good, proceed to Step 6.**

**⚠️ If it shows "tables already exist":**
- **If you're on the production server:** The migration was already run - you can skip to Step 8 (restart application)
- **If you're on your local machine:** This is a **local database**, not production! You need to:
  1. SSH to your production server
  2. Run the migration there
  3. The production database is separate from your local database

---

### Step 6: Run the Actual Migration

**Run the migration for production:**

```bash
python3 migrate_cashback_tables.py prod
```

**The script will:**
1. Show what it's about to do
2. Ask for confirmation: `Proceed with migration? (yes/no):`
3. Type `yes` and press Enter
4. Create the 6 new tables
5. Verify each table was created

**Expected output:**
```
============================================================
CASHBACK TABLES MIGRATION
============================================================
...
Proceed with migration? (yes/no): yes

============================================================
Migrating instance: prod
============================================================
Database URI: sqlite:///instances/prod/database/lending_app_prod.db
→ Creating cashback_transaction table...
✓ cashback_transaction table created successfully
→ Creating loan_cashback_config table...
✓ loan_cashback_config table created successfully
→ Creating tracker_entry table...
✓ tracker_entry table created successfully
→ Creating tracker_cashback_config table...
✓ tracker_cashback_config table created successfully
→ Creating user_payment_method table...
✓ user_payment_method table created successfully
→ Creating cashback_redemption table...
✓ cashback_redemption table created successfully

✓ Migration completed for prod
  Tables created: 6
  Tables already existed: 0

============================================================
MIGRATION SUMMARY
============================================================
✅ Migration completed: 1/1 instances migrated successfully

🎉 All instances migrated successfully!

Next steps:
  1. Restart your application
  2. Verify cashback features are working
```

---

### Step 7: Verify Migration Success

**Verify the tables were created:**

```bash
# Option 1: Run dry run again (should show all tables exist)
python3 migrate_cashback_tables.py prod --dry-run
```

**Expected output:**
```
✓ cashback_transaction table already exists
✓ loan_cashback_config table already exists
✓ tracker_entry table already exists
✓ tracker_cashback_config table already exists
✓ user_payment_method table already exists
✓ cashback_redemption table already exists

[DRY RUN SUMMARY]
  Tables that would be created: 0
  Tables that already exist: 6
```

**Option 2: Check database directly**
```bash
sqlite3 instances/prod/database/lending_app_prod.db ".tables" | grep -E "(cashback|tracker_entry|user_payment_method)"
```

**Expected output:**
```
cashback_redemption
cashback_transaction
loan_cashback_config
tracker_cashback_config
tracker_entry
user_payment_method
```

---

### Step 8: Restart the Application

**If using Docker:**
```bash
# Rebuild and start (to include latest code changes)
docker compose -f docker-compose.prod.yml up -d --build

# Verify container is running
docker compose -f docker-compose.prod.yml ps

# Check logs for any errors
docker compose -f docker-compose.prod.yml logs -f
```

**If running directly:**
```bash
# Start the Flask application
sudo systemctl start lending-app
# OR
# Use your process manager to start the app

# Check logs
tail -f /path/to/logs/app.log
```

---

### Step 9: Test Cashback Features

**Access production and test:**

1. **Login to production:** `http://your-production-url/prod/`
2. **Test admin features:**
   - Go to Admin Dashboard → Cashback Management
   - Try adding unconditional cashback to a user
   - Configure cashback for a loan
   - View cashback history
3. **Test user features:**
   - Login as a regular user
   - Go to Cashback page
   - Try transferring cashback to another user
   - Try creating a redemption request
4. **Verify existing data:**
   - Check that all existing loans are still visible
   - Check that all existing payments are intact
   - Check that all users can login normally

---

## 🔧 Troubleshooting

### Error: "database is locked"

**Solution:**
1. Make sure application is stopped
2. Check for other processes accessing the database:
   ```bash
   lsof instances/prod/database/lending_app_prod.db
   ```
3. Kill any processes holding the lock
4. Retry migration

### Error: "table already exists"

**Solution:**
- This is normal if migration was run before
- The script is idempotent (safe to run multiple times)
- Check if tables actually exist with dry run

### Error: "Permission denied"

**Solution:**
```bash
# Check database file permissions
ls -l instances/prod/database/lending_app_prod.db

# Fix permissions if needed
chmod 644 instances/prod/database/lending_app_prod.db
chown your-user:your-group instances/prod/database/lending_app_prod.db
```

### Migration fails halfway

**Solution:**
1. Check the error message in the output
2. If needed, restore from backup:
   ```bash
   cp instances/prod/backups/lending_app_prod_pre_cashback_*.db \
      instances/prod/database/lending_app_prod.db
   ```
3. Fix the issue (usually permissions or database lock)
4. Run migration again (it's safe - only creates missing tables)

---

## 📊 Post-Migration Verification

**Check database integrity:**
```bash
# Verify all tables exist
sqlite3 instances/prod/database/lending_app_prod.db ".tables"

# Check table schemas
sqlite3 instances/prod/database/lending_app_prod.db ".schema cashback_transaction"
```

**Check application logs:**
```bash
# Docker
docker compose -f docker-compose.prod.yml logs | grep -i error

# Direct
tail -100 /path/to/logs/app.log | grep -i error
```

**Verify existing data:**
- Login and check that all loans are visible
- Check that all payments are intact
- Verify user accounts work normally

---

## 🔄 Rollback (If Needed)

**If you need to rollback (unlikely, but just in case):**

```bash
# 1. Stop application
docker compose -f docker-compose.prod.yml down
# OR
sudo systemctl stop lending-app

# 2. Restore database from backup
cp instances/prod/backups/lending_app_prod_pre_cashback_*.db \
   instances/prod/database/lending_app_prod.db

# 3. Restart application
docker compose -f docker-compose.prod.yml up -d
# OR
sudo systemctl start lending-app
```

**Note:** Rolling back will remove the cashback tables. You'll need to re-run migration if you want to use cashback features again.

---

## ✅ Migration Complete Checklist

- [ ] Backup created successfully
- [ ] Dry run completed without errors
- [ ] Migration executed successfully
- [ ] All 6 tables created and verified
- [ ] Application restarted
- [ ] No errors in application logs
- [ ] Cashback features tested and working
- [ ] Existing data verified intact

---

## 📞 Quick Reference Commands

```bash
# Dry run
python3 migrate_cashback_tables.py prod --dry-run

# Run migration
python3 migrate_cashback_tables.py prod

# Verify migration
python3 migrate_cashback_tables.py prod --dry-run

# Check tables directly
sqlite3 instances/prod/database/lending_app_prod.db ".tables" | grep cashback

# Stop Docker
docker compose -f docker-compose.prod.yml down

# Start Docker
docker compose -f docker-compose.prod.yml up -d --build

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

---

## 🎉 Success!

Once migration is complete and verified:
- ✅ All cashback features are now available in production
- ✅ Existing data remains untouched
- ✅ Users can start earning and redeeming cashback points
- ✅ Admins can configure and manage cashback settings

**Remember:** Keep the backup file safe for at least a few days in case you need to rollback.

