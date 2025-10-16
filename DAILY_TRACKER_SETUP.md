# Daily Tracker Setup Guide

## Quick Start

Follow these steps to set up and start using the Daily Tracker feature.

## Step 1: Run Database Migration

The Daily Tracker feature requires a new database table. Run the migration script:

```bash
cd /Users/skumarraju/Documents/Work/progs/lending_app
python migrate_daily_tracker.py
```

This will:
- Add the `daily_tracker` table to all instances (prod, dev, testing)
- Verify the table was created successfully
- Show a summary of migration status

## Step 2: Verify Directory Structure

The migration automatically creates necessary directories, but you can verify:

```
lending_app/
├── daily-trackers/
│   ├── template/
│   │   └── DailyTrackerTemplate.xlsx  ✓ (already exists)
│   └── tracker_manager.py              ✓ (already exists)
└── instances/
    ├── prod/daily-trackers/            ✓ (auto-created)
    ├── dev/daily-trackers/             ✓ (auto-created)
    └── testing/daily-trackers/         ✓ (auto-created)
```

## Step 3: Start the Application

```bash
python app_multi.py
```

Or if using the run script:

```bash
python run_multi.py
```

The app will start on http://127.0.0.1:8080

## Step 4: Access Admin Panel

1. Open browser to http://127.0.0.1:8080/prod/ (or /dev/ or /testing/)
2. Log in as admin:
   - Username: `admin`
   - Password: `admin123`

## Step 5: Create Your First Tracker

### Admin Steps:

1. Click **"Daily Trackers"** in the left sidebar
2. Click **"Create Tracker"** button
3. Fill in the form:
   - **User**: Select a user (not admin)
   - **Tracker Name**: e.g., "John's Q4 Investment"
   - **Tracker Type**: Choose 50K, 1L, or No Reinvest
   - **Investment**: e.g., 50000
   - **Scheme Period**: e.g., 100 days
   - **Start Date**: Select date (default is today)
4. Click **"Create Tracker"**

Result: Excel file created at `instances/prod/daily-trackers/tracker_username_timestamp.xlsx`

### Add First Entry:

1. From the trackers list, click the **View (eye icon)** button
2. Click **"Add Entry"** button
3. Fill in entry details:
   - **Day Number**: 0 (for start date), 1 (for first day), etc.
   - **Daily Payment**: e.g., 500
   - **Payment Mode**: Select from dropdown
   - **Notes**: Optional notes
4. Click **"Save Entry"**

Result: Excel file updated with your entry, formulas recalculated

## Step 6: User View

### Have User Log In:

1. Log out from admin
2. Log in as the user you created tracker for
3. Dashboard will show the tracker card at the top
4. Click **"View My Tracker"** button
5. User can see:
   - Investment details
   - Summary (total payments, cumulative, balance)
   - All daily entries in table format
   - Tracker parameters

## Usage Scenarios

### Scenario 1: 50K Reinvest Tracker

**Use Case**: Track ₹50,000 investment with daily ₹500 payment for 100 days

1. Create tracker with:
   - Type: 50K Reinvest
   - Investment: 50000
   - Period: 100 days
2. Add entries daily with payment amounts
3. Track cumulative and balance
4. Record withdrawals when applicable

### Scenario 2: 1L Enhanced Tracker

**Use Case**: Track ₹3,00,000 initial investment with ₹1L reinvestment strategy

1. Create tracker with:
   - Type: 1L Enhanced
   - Investment: 300000
   - Period: 200 days
2. Add entries with:
   - Daily payments (₹1000)
   - Reinvestment amounts
   - Pocket money tracking
3. System tracks total invested over time

### Scenario 3: No Reinvest Tracker

**Use Case**: Simple fixed-return investment tracking

1. Create tracker with:
   - Type: No Reinvest
   - Investment: 300000
   - Period: 100 days
2. Add entries with:
   - Daily payments (₹3000)
   - Transaction details
   - Payment modes
3. Track cumulative returns

## Troubleshooting

### Issue: "Tracker not found" error

**Solution**: 
- Check that you're in the correct instance (prod/dev/testing)
- Verify tracker is marked as active in database
- Check file exists in `instances/{instance}/daily-trackers/`

### Issue: Excel file error when viewing

**Solution**:
- Verify openpyxl is installed: `pip install openpyxl`
- Check file permissions on the tracker file
- Ensure template file exists and is readable

### Issue: User doesn't see tracker on dashboard

**Solution**:
- Verify tracker was created for that specific user
- Check tracker `is_active` is True
- Log out and log back in
- Clear browser cache

### Issue: Formulas not calculating

**Solution**:
- Don't manually edit formula cells in Excel
- Only update input cells (daily payment, notes, etc.)
- Re-create tracker if formulas are corrupted

## Testing Checklist

- [ ] Migration completed successfully for all instances
- [ ] Can access admin daily trackers page
- [ ] Can create new tracker
- [ ] Excel file is generated correctly
- [ ] Can view tracker details
- [ ] Can add entry to tracker
- [ ] Entry appears in Excel file
- [ ] User can see tracker on dashboard
- [ ] User can view their tracker details
- [ ] Summary calculations are correct

## File Locations

### Template:
```
daily-trackers/template/DailyTrackerTemplate.xlsx
```

### Generated Trackers:
```
instances/prod/daily-trackers/tracker_*.xlsx
instances/dev/daily-trackers/tracker_*.xlsx
instances/testing/daily-trackers/tracker_*.xlsx
```

### Code Files:
```
app_multi.py                    # Main app with routes and models
daily-trackers/tracker_manager.py  # Excel operations
templates/admin/daily_*.html    # Admin templates
templates/customer/daily_tracker.html  # User template
```

## Support

For detailed documentation, see `DAILY_TRACKER_README.md`

For issues:
1. Check the troubleshooting section
2. Review application logs
3. Verify file permissions
4. Check database connection

## Next Steps

After successful setup:
1. Create trackers for all users who need them
2. Train users on how to view their trackers
3. Establish a schedule for adding entries
4. Set up regular backups of the Excel files
5. Monitor disk space in instances directories

## Backup Recommendations

The Excel files contain important financial data. Back them up regularly:

```bash
# Backup all tracker files
tar -czf daily_trackers_backup_$(date +%Y%m%d).tar.gz instances/*/daily-trackers/

# Or use the existing backup system
python backup_multi.py
```

## Maintenance

### Regular Tasks:
- Weekly: Review all trackers for accuracy
- Monthly: Archive completed trackers
- Quarterly: Clean up old test trackers
- Annually: Review and optimize tracker types

### Monitoring:
- Check disk space in instances directories
- Monitor Excel file sizes (should be < 1MB each)
- Verify all trackers have recent updates
- Check for orphaned files (files without database entries)

---

**You're all set!** Start creating daily trackers for your users.

