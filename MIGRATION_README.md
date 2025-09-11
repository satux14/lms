# Database Migration: Add loan.status column

## Overview
This migration adds a new `status` column to the `loan` table to support loan closing and deletion functionality.

## What it does
- Adds `status VARCHAR(20) DEFAULT 'active'` column to all loan tables
- Sets all existing loans to 'active' status
- Creates automatic backups before migration
- Preserves all existing data

## How to run on production

### 1. Commit and pull changes
```bash
git add .
git commit -m "Add loan close/delete functionality with database migration"
git push origin main

# On production machine:
git pull origin main
```

### 2. Run the migration
```bash
cd /path/to/lending_app
python3 migrate_add_loan_status.py
```

### 3. Verify migration
The script will:
- ✅ Find all database files automatically
- ✅ Create backups with timestamps
- ✅ Add the status column
- ✅ Set existing loans to 'active'
- ✅ Report success/failure for each database

### 4. Start the application
```bash
python3 run_multi.py
```

## Safety Features

### Automatic Backups
- Creates timestamped backups: `database.db.backup_YYYYMMDD_HHMMSS`
- Can restore from backup if needed

### Data Preservation
- No data is deleted or modified
- Only adds new column with default values
- All existing loans remain unchanged

### Error Handling
- Validates database exists before migration
- Checks if column already exists
- Rolls back on errors

## Database Files Migrated
- `instances/prod/database/lending_app_prod.db`
- `instances/dev/database/lending_app_dev.db`
- `instances/testing/database/lending_app_testing.db`
- `instance/prod/database/lending_app_prod.db`
- `instance/dev/database/lending_app_dev.db`
- `instance/testing/database/lending_app_testing.db`

## Rollback (if needed)
If something goes wrong, restore from backup:
```bash
cp database.db.backup_YYYYMMDD_HHMMSS database.db
```

## New Features After Migration
- Close loans (hide from customer view)
- Delete loans (permanent removal)
- Filter loans by status (Active/Closed/Paid Off)
- Customer view only shows active loans

## Requirements
- Python 3.x
- SQLite3
- No special dependencies needed
