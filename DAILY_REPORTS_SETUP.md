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

### Step 1: Install Dependencies

The Daily Reports system uses **APScheduler** for automated scheduling. This runs within your Flask application - no external cron jobs or configuration needed!

```bash
cd /Users/rsk/Documents/GitHub/lms-dev

# Install/update dependencies
pip install -r requirements.txt
```

### Step 2: Run Database Migration

```bash
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

### Step 3: Configure Report Preferences

1. Navigate to Settings: `http://127.0.0.1:9090/dev/settings`
2. Click on "Daily Reports" tab
3. Configure:
   - ✅ Enable Daily Reports (toggle on)
   - ⏰ Set Morning Report Time (default: 08:00 AM IST)
   - ⏰ Set Evening Report Time (default: 20:00 / 8:00 PM IST)
   - ☑️ Select what to include:
     - Trends & Comparisons
     - User Activity Details
     - Priority Alerts & Action Items
4. Click "Save Report Settings"

**⚠️ Important:** Schedule changes require a restart:
```bash
docker-compose restart web
```

### Step 4: Start/Restart Your Application

The scheduler starts automatically when the Flask application starts:

**For Development:**
```bash
python run_multi.py
```

**For Docker:**
```bash
docker-compose up -d --build
```

You'll see this in the logs:
```
============================================================
✅ Report Scheduler Initialized
============================================================
📊 Daily Reports Schedule (IST):
   🌅 Morning Report: 8:00 AM
   🌙 Evening Report: 8:00 PM
============================================================
```

### That's It! 🎉

The scheduler is now running. Reports will be sent automatically at:
- **8:00 AM IST** (Morning Report)
- **8:00 PM IST** (Evening Report)

**No cron jobs needed!** The scheduler runs within your Docker container.

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

## APScheduler Advantages

### Why APScheduler?

✅ **No External Dependencies** - Runs within Flask, no cron needed  
✅ **Docker-Friendly** - Works perfectly in containers  
✅ **Timezone-Aware** - Handles IST automatically  
✅ **Auto-Restart** - Starts when container starts  
✅ **Easy to Modify** - Change schedule in code, rebuild once  
✅ **Integrated Logging** - All logs in one place  
✅ **Misfire Handling** - Catches up if a job is missed  

### How It Works

1. **Scheduler initializes** when Flask app starts
2. **Two jobs registered**:
   - Morning report at 8:00 AM IST
   - Evening report at 8:00 PM IST
3. **Runs in background thread** - doesn't block Flask
4. **Auto-shuts down** gracefully when app stops

### Changing Schedule Times

To change report times, edit `app_scheduler.py`:

```python
# Change morning time (currently 8:00 AM)
scheduler.add_job(
    func=lambda: send_morning_reports_job(app),
    trigger=CronTrigger(hour=8, minute=0, timezone='Asia/Kolkata'),  # Change hour/minute here
    ...
)

# Change evening time (currently 8:00 PM)
scheduler.add_job(
    func=lambda: send_evening_reports_job(app),
    trigger=CronTrigger(hour=20, minute=0, timezone='Asia/Kolkata'),  # Change hour/minute here
    ...
)
```

Then rebuild Docker:
```bash
docker-compose up -d --build
```

## Monitoring & Logs

### Check Application Logs

The scheduler output appears in your Flask application logs.

**For Development:**
```bash
# Logs appear in terminal where you ran run_multi.py
```

**For Docker:**
```bash
# View live logs
docker-compose logs -f web

# View recent logs
docker-compose logs --tail=100 web

# Search for scheduler logs
docker-compose logs web | grep -i "report"
```

### Verify Reports Are Sending

Check your Docker logs around scheduled times (8:00 AM and 8:00 PM):

```bash
docker-compose logs web | grep "Scheduled"
```

Expected output:
```
============================================================
📊 Scheduled Morning Reports
🕐 2025-12-11 08:00:00
============================================================

✓ Sent morning report to admin (prod)

============================================================
✓ Successfully sent:  1 reports
============================================================
```

## Troubleshooting

### Reports Not Being Sent

**Check 1: Scheduler Running?**
```bash
# Check Docker logs for scheduler initialization
docker-compose logs web | grep "Scheduler Initialized"
```

You should see:
```
✅ Report Scheduler Initialized
📊 Daily Reports Schedule (IST):
   🌅 Morning Report: 8:00 AM
   🌙 Evening Report: 8:00 PM
```

**Check 2: Report Preferences**
- Go to Settings → Daily Reports
- Ensure "Enable Daily Reports" is ON
- Verify email address is set

**Check 3: SMTP Configuration**
```bash
docker-compose logs web | grep -i smtp
```

**Check 4: Application Running?**
```bash
docker-compose ps
# Should show 'web' service as 'Up'
```

**Check 5: Check Scheduler Logs**
```bash
# View all scheduler-related logs
docker-compose logs web | grep -E "(Scheduled|Report|APScheduler)"
```

### Email Not Received

1. **Check spam folder** in Gmail
2. **Verify admin email** is correct in database
3. **Test SMTP** manually:
   ```bash
   # Generate on-demand report from Settings page
   ```
4. **Check logs** for error messages

### Scheduler Not Running

1. **Restart Docker container**:
   ```bash
   docker-compose restart web
   ```

2. **Check for errors during startup**:
   ```bash
   docker-compose logs web | tail -50
   ```

3. **Verify APScheduler is installed**:
   ```bash
   docker-compose exec web pip list | grep APScheduler
   # Should show: APScheduler    3.10.4
   ```

4. **Test manually via On-Demand button**:
   - Go to Settings → Daily Reports
   - Click "Generate & Send Report Now"
   - Check if email arrives

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

### Timezone Handling

APScheduler is configured for **Asia/Kolkata (IST)** timezone:

```python
scheduler = BackgroundScheduler(daemon=True, timezone='Asia/Kolkata')
```

This means:
- Reports send at **8:00 AM IST** and **8:00 PM IST**
- No matter what timezone your server is in
- Handles DST automatically (though IST doesn't have DST)

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
- [ ] Update dependencies (`pip install -r requirements.txt` or rebuild Docker)
- [ ] Configure report preferences in Settings
- [ ] Set admin email addresses
- [ ] Restart application/Docker container
- [ ] Verify scheduler initialized (check logs for "✅ Report Scheduler Initialized")
- [ ] Test on-demand report generation
- [ ] Verify first scheduled report received
- [ ] Monitor Docker logs for first week

## Support

For issues or questions:
1. Check Docker logs: `docker-compose logs web | grep -i report`
2. Verify scheduler is running: Look for "✅ Report Scheduler Initialized" in logs
3. Test manually: Use "Generate & Send Report Now" button in Settings
4. Review this documentation
5. Check email configuration in Docker environment variables
6. Restart container: `docker-compose restart web`

---

**Implementation Date:** December 11, 2025  
**Version:** 2.0.0 - Daily Reports System (APScheduler)

