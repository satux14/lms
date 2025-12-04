# Cashback Feature Migration Guide - Safe Production Deployment

## ⚠️ SAFETY GUARANTEE

**This migration is 100% SAFE because:**

1. ✅ It only **ADDS** new tables (6 new tables)
2. ✅ It does **NOT** modify any existing tables
3. ✅ It does **NOT** delete any data
4. ✅ It does **NOT** change any existing data
5. ✅ All your existing loans, payments, users, and trackers remain untouched
6. ✅ Safe to run multiple times (idempotent)

The migration simply creates new tables alongside your existing tables.

## What Gets Created

The migration adds **6 new tables**:

1. **cashback_transaction** - Tracks all cashback point transactions
2. **loan_cashback_config** - Stores per-loan cashback configuration
3. **tracker_entry** - Tracks individual tracker entries with approval status
4. **tracker_cashback_config** - Stores per-tracker cashback configuration
5. **user_payment_method** - Stores user's payment method details for redemption
6. **cashback_redemption** - Tracks cashback redemption requests

## Step-by-Step Migration Process

### Step 1: Verify What Will Happen (Dry Run)

First, see exactly what the migration will do WITHOUT making any changes:

```bash
cd /Users/rsk/Documents/GitHub/lms-dev
python3 migrate_cashback_tables.py prod --dry-run
```

**This script:**
- ✅ Shows current database state
- ✅ Shows what tables will be added
- ✅ Makes NO changes
- ✅ Confirms safety guarantees

**Expected output:**
- Lists all existing tables
- Shows which cashback tables don't exist
- Confirms it will only ADD the new tables

---

### Step 2: Backup Production Database (Recommended)

Create a backup before migration (just to be extra safe):

```bash
# Option 1: Use the backup script if available
python3 backup_before_migration.py

# Option 2: Manual backup
cp instances/prod/database/lending_app_prod.db \
   instances/prod/backups/lending_app_prod_pre_cashback_$(date +%Y%m%d_%H%M%S).db
```

**Backup location:**
- `instances/prod/backups/lending_app_prod_pre_cashback_YYYYMMDD_HHMMSS.db`

---

### Step 3: Run the Migration

**For production instance only:**
```bash
python3 migrate_cashback_tables.py prod
```

**For all instances (prod, dev, testing):**
```bash
python3 migrate_cashback_tables.py all
```

**What happens:**
1. The script checks which tables already exist
2. Creates only the tables that don't exist
3. Verifies each table was created successfully
4. Shows a summary of what was done

**Expected output:**
```
============================================================
Migrating instance: prod
============================================================
Database URI: sqlite:///instances/prod/database/lending_app_prod.db
→ Creating cashback_transaction table...
✓ cashback_transaction table created successfully
→ Creating loan_cashback_config table...
✓ loan_cashback_config table created successfully
... (and so on for all 6 tables)

✓ Migration completed for prod
  Tables created: 6
  Tables already existed: 0
```

---

### Step 4: Verify Migration Success

After migration, verify the tables were created:

```bash
# Option 1: Run the migration script again (it will show tables already exist)
python3 migrate_cashback_tables.py prod --dry-run

# Option 2: Check database directly
sqlite3 instances/prod/database/lending_app_prod.db ".tables" | grep cashback
```

**Expected result:**
- All 6 tables should be listed
- Migration script should show "already exists" for all tables

---

## What If Something Goes Wrong?

### Migration fails halfway

1. **Check the error message** - The script will show what failed
2. **Restore from backup** if needed:
   ```bash
   cp instances/prod/backups/lending_app_prod_pre_cashback_*.db \
      instances/prod/database/lending_app_prod.db
   ```
3. **Fix the issue** and run migration again
4. The script is safe to run multiple times - it only creates missing tables

### Database is locked

If you see "database is locked" error:
1. **Stop the application** (if running)
2. **Run the migration**
3. **Restart the application**

---

## Post-Migration Steps

1. **Restart your application** to ensure it picks up the new tables
2. **Test cashback features:**
   - Try adding cashback to a user
   - Try configuring cashback for a loan
   - Try a cashback transfer
   - Try a redemption request
3. **Verify data integrity:**
   - Check that existing loans/payments/users are unchanged
   - Check that new cashback tables are empty (as expected)

---

## Migration Checklist

Before migration:
- [ ] Code has been tested in dev environment
- [ ] Backup created (recommended)
- [ ] Dry run completed successfully
- [ ] Application stopped (if needed to avoid lock)

During migration:
- [ ] Run migration script
- [ ] Verify all tables created successfully
- [ ] Check for any error messages

After migration:
- [ ] Restart application
- [ ] Test cashback features
- [ ] Verify existing data is intact
- [ ] Monitor application logs for any issues

---

## Important Notes

1. **No data migration needed** - These are brand new tables, so they start empty
2. **Existing functionality unaffected** - All existing features continue to work
3. **Rollback is simple** - Just delete the 6 new tables if needed (though unlikely)
4. **Migration is idempotent** - Safe to run multiple times

---

## Quick Reference

```bash
# Dry run (see what would happen)
python3 migrate_cashback_tables.py prod --dry-run

# Migrate production
python3 migrate_cashback_tables.py prod

# Migrate all instances
python3 migrate_cashback_tables.py all

# Check migration status
python3 migrate_cashback_tables.py prod --dry-run
```

---

## Support

If you encounter any issues:
1. Check the error message in the migration output
2. Verify database file permissions
3. Ensure application is stopped (to avoid database locks)
4. Check that you have write permissions to the database directory

