# Daily Reports System - Setup Guide

## Overview

The Daily Reports System automatically generates and sends comprehensive business reports to admins twice daily (morning and evening). Reports include loan performance, tracker activity, cashback transactions, user activity, trends, and priority action items.

## Features

✅ **Automated Reports** - Twice daily delivery (morning & evening)  
✅ **On-Demand Generation** - Generate reports instantly from Settings  
✅ **Customizable Schedule** - Configure report times per admin  
✅ **Comprehensive Metrics** - Everything you need in one place  
✅ **Beautiful HTML Emails** - Professional, easy-to-read format  
✅ **Priority Alerts** - Urgent items highlighted at the top  
✅ **Trend Analysis** - Compare vs yesterday and weekly averages  

## Report Contents

### 📊 Executive Summary
- Today's collections (total amount)
- Pending approvals count
- Active users today
- Quick status overview

### 💵 Loan Performance
- Today's payments (count, amount, interest/principal breakdown)
- Pending payments and amounts
- New loans created
- Top paying customers (top 5)
- Awaiting approval

### 📅 Tracker Performance
- Today's entries (count and amount)
- Pending entries
- Active trackers count
- Completion rate percentage

### 🎁 Cashback Activity
- Automatic cashback distributed (loans & trackers)
- Manual admin awards
- Redeemed amounts
- Pending redemption requests
- Total system cashback balance
- Top cashback earners (top 5)

### ⚡ Actions Required
- **Urgent items** (red alerts):
  - Payments pending >2 days
  - Pending redemption requests
- **Review items** (yellow alerts):
  - Tracker entries awaiting approval

### 📈 Trends & Comparisons
- vs Yesterday (percentage change)
- Weekly average collections
- Growth indicators

### 🎯 Quick Stats
- Total active loans and principal
- Total active trackers and investment
- System overview

### 👥 User Activity
- Active users today
- New users created
- Total users

## Setup Instructions

### Step 1: Run Database Migration

```bash
cd /Users/rsk/Documents/GitHub/lms-dev

# Dry run first
python3 migrate_report_preferences.py --dry-run

# Apply migration
python3 migrate_report_preferences.py
```

Expected output:
```
✓ Successfully created report_preference table
✓ Successfully created report_history table
✓ Created report preferences for 1 admin user(s)
```

### Step 2: Configure Report Preferences

1. Navigate to Settings: `http://127.0.0.1:9090/dev/settings`
2. Click on "Daily Reports" tab
3. Configure:
   - ✅ Enable Daily Reports (toggle on)
   - ⏰ Set Morning Report Time (default: 08:00)
   - ⏰ Set Evening Report Time (default: 20:00)
   - ☑️ Select what to include:
     - Trends & Comparisons
     - User Activity Details
     - Priority Alerts & Action Items
4. Click "Save Report Settings"

### Step 3: Set Up Cron Jobs (Production)

On your production server, set up cron jobs to run the scheduler:

```bash
# Edit crontab
crontab -e
```

Add these lines:

```bash
# Morning report at 8:00 AM (adjust time as needed)
0 8 * * * cd /path/to/lms-production && python3 daily_report_scheduler.py morning >> logs/reports.log 2>&1

# Evening report at 8:00 PM (adjust time as needed)
0 20 * * * cd /path/to/lms-production && python3 daily_report_scheduler.py evening >> logs/reports.log 2>&1
```

**Important:** Adjust paths and times according to your setup.

### Step 4: Create Logs Directory

```bash
mkdir -p /path/to/lms-production/logs
```

### Step 5: Test the Scheduler

Test manually before relying on cron:

```bash
# Test morning report
python3 daily_report_scheduler.py morning

# Test evening report
python3 daily_report_scheduler.py evening

# Test specific instance only
python3 daily_report_scheduler.py morning prod
```

Check the output for:
```
✓ Sent morning report to admin (prod)
```

Check your email inbox for the report.

## Using On-Demand Reports

### From Settings Page

1. Go to: `http://127.0.0.1:9090/dev/settings`
2. Click "Daily Reports" tab
3. Click "Generate & Send Report Now" button
4. Confirm the dialog
5. Report is generated and sent to your email immediately

### Use Cases for On-Demand
- ✅ Quick business overview anytime
- ✅ Before important meetings
- ✅ End of busy day review
- ✅ Testing report configuration

## Email Configuration

Daily reports use the same email system as notifications.

**Requirements:**
- ✅ SMTP configured in Docker Compose (already done)
- ✅ Admin user has email address set
- ✅ Report preferences enabled

**SMTP Settings (already configured):**
```yaml
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=thesrsconsulting@gmail.com
SMTP_PASSWORD=vbmhddffmrdilbxk
SMTP_FROM_EMAIL=thesrsconsulting@gmail.com
```

## Cron Time Configuration

### Understanding Cron Syntax

```
* * * * * command
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, Sun=0 or 7)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

### Example Schedules

```bash
# Morning report at 8:00 AM
0 8 * * * python3 daily_report_scheduler.py morning

# Morning report at 7:30 AM
30 7 * * * python3 daily_report_scheduler.py morning

# Evening report at 8:00 PM (20:00)
0 20 * * * python3 daily_report_scheduler.py evening

# Evening report at 10:00 PM (22:00)
0 22 * * * python3 daily_report_scheduler.py evening

# Only run on weekdays (Mon-Fri)
0 8 * * 1-5 python3 daily_report_scheduler.py morning
```

## Monitoring & Logs

### Check Cron Logs

```bash
# View recent reports log
tail -f /path/to/lms/logs/reports.log

# Check if cron job ran
grep "daily_report_scheduler" /var/log/syslog

# Check last 10 report runs
tail -20 /path/to/lms/logs/reports.log
```

### Verify Reports Are Sending

```bash
# Run manual test
cd /path/to/lms-production
python3 daily_report_scheduler.py morning
```

Expected output:
```
============================================================
📊 Daily Report Scheduler - MORNING
🕐 2025-12-11 08:00:00
============================================================

📌 Processing instance: prod
----------------------------------------
  📊 Generating report for admin...
  📧 Sending to thesrsconsulting@gmail.com...
  ✓ Sent morning report to admin (prod)

============================================================
📊 Report Summary
============================================================
✓ Successfully sent:  1 reports
============================================================
```

## Troubleshooting

### Reports Not Being Sent

**Check 1: Cron Job Running?**
```bash
crontab -l  # List cron jobs
```

**Check 2: Python Path Correct?**
```bash
which python3  # Should show /usr/bin/python3 or similar
```

**Check 3: File Permissions**
```bash
chmod +x /path/to/lms/daily_report_scheduler.py
```

**Check 4: Report Preferences**
- Go to Settings → Daily Reports
- Ensure "Enable Daily Reports" is ON
- Verify email address is set

**Check 5: SMTP Configuration**
```bash
docker-compose logs web | grep -i smtp
```

**Check 6: Logs**
```bash
tail -50 /path/to/lms/logs/reports.log
```

### Email Not Received

1. **Check spam folder** in Gmail
2. **Verify admin email** is correct in database
3. **Test SMTP** manually:
   ```bash
   # Generate on-demand report from Settings page
   ```
4. **Check logs** for error messages

### Cron Job Not Running

1. **Verify cron service** is running:
   ```bash
   sudo systemctl status cron    # Ubuntu/Debian
   sudo systemctl status crond   # CentOS/RHEL
   ```

2. **Check cron permissions**:
   ```bash
   ls -l /var/spool/cron/crontabs/$(whoami)
   ```

3. **Test command manually** first:
   ```bash
   cd /path/to/lms && python3 daily_report_scheduler.py morning
   ```

## Report Schedule Best Practices

### Recommended Times

**Morning Report (8:00 AM):**
- Shows yesterday's activity
- Highlights today's priorities
- Perfect for daily planning

**Evening Report (8:00 PM):**
- Shows today's full activity
- End-of-day summary
- Identify items for tomorrow

### Timezone Considerations

Cron uses **server timezone**. To use IST (Indian Standard Time):

1. **Check server timezone:**
   ```bash
   timedatectl  # or: date +%Z
   ```

2. **If different from IST, adjust cron times accordingly**
   - Server in UTC: IST is UTC+5:30
   - 8:00 AM IST = 2:30 AM UTC
   - 8:00 PM IST = 2:30 PM UTC (14:30)

## Sample Report Output

```
================================================================
                   DAILY BUSINESS REPORT
                    December 11, 2025
                     MORNING REPORT
================================================================

EXECUTIVE SUMMARY
-----------------
Today's Collections:    ₹45,000.00
Pending Approvals:      5 items
Active Users Today:     23 users

================================================================
ACTIONS REQUIRED
================================================================

🔴 URGENT:
  - 3 payments pending approval (>2 days old)
  - 1 redemption request waiting

🟡 REVIEW:
  - 2 tracker entries pending approval

================================================================
LOAN PERFORMANCE
================================================================

[... detailed metrics ...]
```

## Advanced Configuration

### Per-Admin Customization

Each admin can configure their own:
- Report delivery times
- Included sections
- Enable/disable toggle

This allows flexibility for different admin roles or preferences.

### Multiple Recipients

To send reports to multiple admins:
1. Create admin users in the system
2. Set their email addresses
3. Enable reports for each admin in Settings

All admins with reports enabled will receive their own reports.

## Future Enhancements

Potential features for future versions:
- 📄 PDF report generation
- 📊 Charts and graphs in emails
- 🔔 Slack/WhatsApp integration
- 📅 Weekly/monthly summary reports
- 🎯 Custom metric selection
- 📈 Historical report archive
- 📤 Export to Excel
- 🔔 Threshold-based alerts

## Production Deployment Checklist

- [ ] Run database migration (`migrate_report_preferences.py`)
- [ ] Configure report preferences in Settings
- [ ] Set admin email addresses
- [ ] Add cron jobs to crontab
- [ ] Create logs directory
- [ ] Test manual report generation
- [ ] Verify first scheduled report received
- [ ] Monitor logs for first week

## Support

For issues or questions:
1. Check logs: `tail -f logs/reports.log`
2. Test manually: `python3 daily_report_scheduler.py morning`
3. Review this documentation
4. Check email configuration
5. Verify cron job syntax

---

**Implementation Date:** December 11, 2025  
**Version:** 1.0.0 - Daily Reports System

