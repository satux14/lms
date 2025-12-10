# Production Migration Guide - Today's Changes

## 🎯 Summary

**Today's code changes:** Only code refactoring and bug fixes - **NO database schema changes**

However, you may need to run these migrations if you haven't already:
1. **Cashback Tables Migration** (if not already run)
2. **Loan Splitting Migration** (if not already run)

---

## ✅ Safety Guarantee

**Both migrations are 100% SAFE:**
- ✅ Only **ADD** new tables/columns
- ✅ Do **NOT** modify existing data
- ✅ Do **NOT** delete any data
- ✅ Safe to run multiple times (idempotent)
- ✅ Your existing loans, payments, users remain untouched

---

## 📋 Pre-Migration Checklist

- [ ] Code has been tested in dev environment
- [ ] All changes are committed and pushed to repository
- [ ] You have SSH/access to production server
- [ ] You know where production database is located
- [ ] You have backup access configured

**⚠️ IMPORTANT:** Database files (`.db`) are **NOT** in git. Each server has its own database. Migrations **MUST** be run on the production server where the database actually exists.

---

## 🔍 Step 1: Check What Migrations Are Needed

**First, check what's already been migrated:**

```bash
# SSH to your production server
ssh your-production-server
cd /path/to/lms-dev

# Check cashback tables (dry run)
python3 migrate_cashback_tables.py prod --dry-run

# Check loan splitting (dry run)
python3 migrate_loan_splitting.py --instance prod
```

**What to look for:**

### Cashback Migration Check:
- ✅ If it says "table already exists" → Migration already done, skip to Step 2
- ⚠️ If it says "Would create table" → Need to run migration

### Loan Splitting Migration Check:
- ✅ If it says "column already exists" → Migration already done, skip to Step 3
- ⚠️ If it says "Would add column" → Need to run migration

---

## 🚀 Step 2: Migrate Cashback Tables (If Needed)

**Only run this if the dry run showed tables need to be created.**

### 2.1: Stop the Application

```bash
# Docker
docker compose -f docker-compose.prod.yml down

# OR Direct
sudo systemctl stop lending-app
```

### 2.2: Create Backup

```bash
mkdir -p instances/prod/backups
cp instances/prod/database/lending_app_prod.db \
   instances/prod/backups/lending_app_prod_pre_cashback_$(date +%Y%m%d_%H%M%S).db
```

### 2.3: Run Migration

```bash
# Dry run first (verify what will happen)
python3 migrate_cashback_tables.py prod --dry-run

# If dry run looks good, run actual migration
python3 migrate_cashback_tables.py prod
```

**What it does:**
- Adds 6 new tables:
  - `cashback_transaction`
  - `loan_cashback_config`
  - `tracker_entry`
  - `tracker_cashback_config`
  - `user_payment_method`
  - `cashback_redemption`

**Expected output:**
```
✓ cashback_transaction table created successfully
✓ loan_cashback_config table created successfully
... (and so on)
```

---

## 🚀 Step 3: Migrate Loan Splitting (If Needed)

**Only run this if the dry run showed columns need to be added.**

### 3.1: Stop the Application (if not already stopped)

```bash
# Docker
docker compose -f docker-compose.prod.yml down

# OR Direct
sudo systemctl stop lending-app
```

### 3.2: Create Backup (if not already done)

```bash
mkdir -p instances/prod/backups
cp instances/prod/database/lending_app_prod.db \
   instances/prod/backups/lending_app_prod_pre_loan_split_$(date +%Y%m%d_%H%M%S).db
```

### 3.3: Run Migration

```bash
# Dry run first (verify what will happen)
python3 migrate_loan_splitting.py --instance prod

# If dry run looks good, run actual migration
python3 migrate_loan_splitting.py --instance prod --apply
```

**What it does:**
- Adds 2 columns to `payment` table:
  - `split_loan_id` (INTEGER, nullable)
  - `original_principal_amount` (NUMERIC, nullable)
- Creates new table:
  - `loan_split`

**Expected output:**
```
✓ Would add split_loan_id and original_principal_amount columns to payment table
✓ Would create loan_split table
```

---

## ✅ Step 4: Verify Migrations

**Verify both migrations completed successfully:**

```bash
# Check cashback tables
python3 migrate_cashback_tables.py prod --dry-run
# Should show: "Tables that already exist: 6"

# Check loan splitting
python3 migrate_loan_splitting.py --instance prod
# Should show: "column already exists" for both columns
```

**Or check directly:**

```bash
sqlite3 instances/prod/database/lending_app_prod.db ".tables" | grep -E "(cashback|loan_split)"
```

**Expected output:**
```
cashback_redemption
cashback_transaction
loan_cashback_config
loan_split
tracker_cashback_config
tracker_entry
user_payment_method
```

---

## 🚀 Step 5: Restart Application

**After migrations are complete:**

```bash
# Docker
docker compose -f docker-compose.prod.yml up -d --build

# Verify it's running
docker compose -f docker-compose.prod.yml ps

# Check logs
docker compose -f docker-compose.prod.yml logs -f

# OR Direct
sudo systemctl start lending-app
tail -f /path/to/logs/app.log
```

---

## 🧪 Step 6: Test Application

**Verify everything works:**

1. **Login to production:** `http://your-production-url/prod/`
2. **Test existing features:**
   - View loans (should all be visible)
   - View payments (should all be visible)
   - View users (should all be visible)
3. **Test new features (if migrations were run):**
   - Cashback management (if cashback migration was run)
   - Loan splitting (if loan splitting migration was run)

---

## 🔄 Quick Reference Commands

```bash
# Check what needs migration
python3 migrate_cashback_tables.py prod --dry-run
python3 migrate_loan_splitting.py --instance prod

# Run migrations (if needed)
python3 migrate_cashback_tables.py prod
python3 migrate_loan_splitting.py --instance prod --apply

# Verify migrations
python3 migrate_cashback_tables.py prod --dry-run
python3 migrate_loan_splitting.py --instance prod

# Check tables directly
sqlite3 instances/prod/database/lending_app_prod.db ".tables"

# Docker commands
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f
```

---

## ⚠️ Important Notes

1. **Today's code changes:** Only refactoring and bug fixes - no DB changes needed
2. **Migrations are safe:** They only ADD tables/columns, never DELETE or MODIFY existing data
3. **Idempotent:** Safe to run multiple times - won't cause errors if already run
4. **Backups:** Always create backups before running migrations (just to be safe)
5. **Production server:** Migrations MUST be run on the server where the database exists

---

## 🆘 Troubleshooting

### Error: "database is locked"
- Make sure application is stopped
- Check for other processes: `lsof instances/prod/database/lending_app_prod.db`
- Kill any processes holding the lock

### Error: "table/column already exists"
- This is normal if migration was already run
- Scripts are idempotent - safe to ignore

### Error: "Permission denied"
```bash
chmod 644 instances/prod/database/lending_app_prod.db
chown your-user:your-group instances/prod/database/lending_app_prod.db
```

### Need to rollback?
```bash
# Restore from backup
cp instances/prod/backups/lending_app_prod_pre_*.db \
   instances/prod/database/lending_app_prod.db
```

---

## ✅ Final Checklist

- [ ] Checked what migrations are needed (dry run)
- [ ] Created database backup
- [ ] Stopped application
- [ ] Ran cashback migration (if needed)
- [ ] Ran loan splitting migration (if needed)
- [ ] Verified migrations completed successfully
- [ ] Restarted application
- [ ] Tested application - all features working
- [ ] No errors in logs

---

## 🎉 Success!

Once migrations are complete:
- ✅ All new features are available
- ✅ Existing data remains untouched
- ✅ Application is running normally
- ✅ No data loss occurred

**Remember:** Keep backup files safe for at least a few days!

