# Backup System Documentation

## Overview

The Lending Management System includes a comprehensive backup system to protect your financial data. This system provides multiple backup options, automated scheduling, and easy recovery procedures.

## Features

### 🔄 **Multiple Backup Types**
- **Full Backup**: Complete system backup (database + Excel export in ZIP)
- **Database Backup**: SQLite database file only
- **Excel Export**: All data exported to Excel format with multiple sheets

### 📊 **Excel Export Details**
The Excel export includes the following sheets:
- **Users**: All user accounts and admin information
- **Loans**: Complete loan details including notes and status
- **Payments**: All payment records with transaction details
- **Interest Rates**: Historical interest rate data
- **Summary**: Key statistics and metrics

### 🗂️ **Organized Storage**
- `backups/database/` - Database backup files
- `backups/excel/` - Excel export files
- `backups/full/` - Complete backup ZIP files
- Automatic cleanup of old files

## Usage

### 🌐 **Web Interface (Admin Panel)**

1. **Access Backup Page**:
   - Login as admin
   - Click "Backup" in the sidebar or dashboard
   - Navigate to `/admin/backup`

2. **Create Backups**:
   - Click "Full Backup" for complete backup
   - Click "Database Only" for database backup
   - Click "Excel Export" for data export

3. **Download Backups**:
   - View all backup files in organized tables
   - Click download button for any backup file
   - Files are automatically downloaded to your computer

4. **Cleanup Old Files**:
   - Select retention period (7-90 days)
   - Click "Cleanup" to remove old backups
   - Confirmation required before deletion

### 💻 **Terminal Commands**

#### **Basic Commands**
```bash
# Create full backup (recommended)
python3 backup_script.py full

# Create database backup only
python3 backup_script.py database

# Create Excel export only
python3 backup_script.py excel

# Show backup information
python3 backup_script.py info

# Clean up old backups (default: 30 days)
python3 backup_script.py cleanup

# Clean up backups older than 7 days
python3 backup_script.py cleanup --days 7
```

#### **Advanced Commands**
```bash
# Setup daily backup schedule
python3 backup_script.py schedule

# Run daily backup with cleanup
python3 daily_backup.py --cleanup-days 30
```

## Automated Scheduling

### 📅 **Daily Backup Setup**

#### **Option 1: Using the Script**
```bash
python3 backup_script.py schedule
```
This will guide you through setting up a cron job.

#### **Option 2: Manual Cron Setup**
Add this line to your crontab:
```bash
# Run daily at 2:00 AM
0 2 * * * cd /path/to/lending_app && python3 daily_backup.py --cleanup-days 30 >> backup.log 2>&1
```

#### **Option 3: Using daily_backup.py**
```bash
# Add to crontab for automated daily backups
0 2 * * * cd /path/to/lending_app && python3 daily_backup.py >> backup.log 2>&1
```

### ⚙️ **Cron Management**
```bash
# Edit crontab
crontab -e

# View current crontab
crontab -l

# Remove all cron jobs
crontab -r
```

## File Structure

```
lending_app/
├── backup.py                 # Core backup module
├── backup_script.py          # Terminal backup script
├── daily_backup.py           # Automated daily backup
├── backups/                  # Backup storage directory
│   ├── database/            # Database backup files
│   ├── excel/               # Excel export files
│   └── full/                # Complete backup ZIP files
├── backup.log               # Backup operation logs
└── BACKUP_README.md         # This documentation
```

## Backup Contents

### 📦 **Full Backup ZIP Structure**
```
full_backup_YYYYMMDD_HHMMSS.zip
├── database/
│   └── lending_app_backup_YYYYMMDD_HHMMSS.db
├── excel/
│   └── lending_data_export_YYYYMMDD_HHMMSS.xlsx
└── metadata.json
```

### 📊 **Excel Export Sheets**
1. **Users Sheet**: User accounts, admin status, creation dates
2. **Loans Sheet**: Loan details, customer info, financial data
3. **Payments Sheet**: Payment history, transaction details, status
4. **Interest Rates Sheet**: Historical interest rate data
5. **Summary Sheet**: Key metrics and statistics

## Recovery Procedures

### 🔄 **Database Recovery**
1. Stop the application
2. Replace `lending_app.db` with backup file
3. Restart the application

### 📊 **Data Analysis**
1. Download Excel export from backup
2. Open in Excel or Google Sheets
3. Analyze data using built-in tools

### 🔍 **Verification**
1. Check backup file sizes (should be > 0 MB)
2. Verify Excel export opens correctly
3. Test database backup by restoring to test environment

## Best Practices

### 📋 **Backup Schedule**
- **Daily**: Full backup with 30-day retention
- **Weekly**: Additional full backup with 90-day retention
- **Monthly**: Archive important backups to external storage

### 🔒 **Security**
- Store backups in secure location
- Encrypt sensitive backup files
- Test recovery procedures regularly
- Keep multiple backup copies

### 📈 **Monitoring**
- Check backup logs regularly
- Monitor backup file sizes
- Verify backup completion
- Set up alerts for backup failures

## Troubleshooting

### ❌ **Common Issues**

#### **"Database file not found"**
- Ensure the application has been run at least once
- Check file permissions
- Verify database path in configuration

#### **"Excel export failed"**
- Check pandas installation: `pip install pandas`
- Verify openpyxl installation: `pip install openpyxl`
- Check available disk space

#### **"Permission denied"**
- Ensure write permissions on backup directory
- Run with appropriate user permissions
- Check file system permissions

#### **"Cron job not running"**
- Verify cron service is running
- Check cron job syntax
- Review cron logs: `grep CRON /var/log/syslog`

### 🔧 **Debug Commands**
```bash
# Test backup system
python3 backup_script.py info

# Check backup directory
ls -la backups/

# View backup logs
tail -f backup.log

# Test Excel export
python3 backup_script.py excel
```

## Support

### 📞 **Getting Help**
1. Check backup logs in `backup.log`
2. Run `python3 backup_script.py info` for system status
3. Verify all dependencies are installed
4. Check file permissions and disk space

### 🆘 **Emergency Recovery**
1. Use the most recent full backup
2. Restore database file
3. Verify data integrity
4. Contact system administrator if needed

## Version Information

- **Backup System Version**: 1.0.1
- **Compatible with**: Lending Management System v1.0.1+
- **Last Updated**: 2025-09-08

---

**⚠️ Important**: Always test your backup and recovery procedures before relying on them for production data!
