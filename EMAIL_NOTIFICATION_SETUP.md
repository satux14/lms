# Email Notification System - Setup Guide

## Overview

The Lending Management System now includes an email notification system that sends alerts to admins when approval requests are received. The system is designed with a generic notification interface that can be extended to support multiple channels (email, SMS, Slack, etc.) in the future.

## Features Implemented

✅ **Generic Notification Interface** (`app_notifications.py`)
- Abstract base class for notification providers
- Support for multiple notification channels (email, SMS, Slack - extensible)
- Centralized notification sending logic

✅ **Email Notification Provider** (`app_notify_email.py`)
- Gmail SMTP integration (or any SMTP server)
- HTML and plain text email templates
- Fallback templates when custom templates are not available
- Development mode (console output) and production mode (actual email sending)

✅ **User Notification Preferences** (`templates/user_settings.html`)
- Settings page for all users to manage their notification preferences
- Admins can enable/disable notifications for:
  - Payment approval requests
  - Tracker entry approval requests
- Customers can enable/disable notifications for:
  - Payment status updates (future feature)
  - Tracker entry status updates (future feature)

✅ **Automatic Notifications**
- Sends email to admins when:
  - New payment is submitted (status='pending')
  - New tracker entry is submitted (status='pending')
- Only sends to admins who have email notifications enabled
- Graceful degradation: Failures don't block the main operation

✅ **Database Migration**
- Added `notification_preference` table
- Default preferences created for all admin users (notifications enabled by default)

## Configuration Steps

### Step 1: Update Gmail Settings

You already have the Gmail app password: `vbmhddffmrdilbxk`

You need to update the Docker environment variables or create a `.env` file with your Gmail credentials.

### Step 2: Update Docker Compose Files

**For `docker-compose.dev.yml` and `docker-compose.prod.yml`:**

Add these environment variables under the `web` service:

```yaml
services:
  web:
    environment:
      # ... existing environment variables ...
      
      # Email Notification Configuration
      - SMTP_HOST=smtp.gmail.com
      - SMTP_PORT=587
      - SMTP_USER=your.actual.email@gmail.com
      - SMTP_PASSWORD=vbmhddffmrdilbxk
      - SMTP_FROM_EMAIL=your.actual.email@gmail.com
      - SMTP_FROM_NAME=LMS Notification System
      - SMTP_USE_TLS=True
      - NOTIFICATIONS_ENABLED=True
```

**Important:** Replace `your.actual.email@gmail.com` with your actual Gmail address.

### Step 3: Restart the Application

After updating the Docker Compose files, restart the application:

```bash
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d
```

## Testing the System

### Test 1: Check Settings Page

1. Log in as an admin user
2. Navigate to: `http://127.0.0.1:9090/dev/settings`
3. Verify you can see the notification settings
4. Ensure "Email Notifications" is enabled
5. Ensure "Payment Approval Requests" and "Tracker Entry Approval Requests" are checked
6. Add/verify your email address

### Test 2: Test Payment Notification

1. Create a new payment (as admin or customer)
2. Check your email inbox for a notification
3. The email should have:
   - Subject: "Payment Approval Required - Loan: [Loan Name]"
   - Loan details
   - Link to review the payment

### Test 3: Test Tracker Entry Notification

1. Submit a new tracker entry (as moderator)
2. Check your email inbox for a notification
3. The email should have:
   - Subject: "Tracker Entry Approval Required - [Tracker Name]"
   - Tracker entry details
   - Link to review the entry

### Test 4: Development Mode (Optional)

If you want to test without sending actual emails, you can set:

```yaml
- NOTIFICATIONS_ENABLED=False
```

Or keep it enabled but don't configure SMTP credentials. The system will print emails to the console instead.

## File Structure

```
lms-dev/
├── app_notifications.py              # Generic notification interface
├── app_notify_email.py               # Email provider implementation
├── migrate_notification_preferences.py # Database migration script
├── EMAIL_NOTIFICATION_SETUP.md       # This file
├── templates/
│   ├── user_settings.html            # User settings page
│   └── emails/
│       ├── approval_request_payment.html  # Payment approval email (HTML)
│       ├── approval_request_payment.txt   # Payment approval email (text)
│       ├── approval_request_tracker.html  # Tracker approval email (HTML)
│       └── approval_request_tracker.txt   # Tracker approval email (text)
└── (modified files)
    ├── app_multi.py                  # Added user_settings route, NotificationPreference model
    ├── app_payments.py               # Added notification calls for payment creation
    └── app_moderator.py              # Added notification calls for tracker entry creation
```

## How It Works

### 1. When a Payment is Created (status='pending')

```
Customer/Admin creates payment
    ↓
Payment saved to database
    ↓
send_approval_notification() called
    ↓
System queries NotificationPreference table for admins with email enabled
    ↓
For each admin with notifications enabled:
    - Create Notification object
    - Render email template with payment details
    - Send via SMTP (Gmail)
    ↓
Admin receives email notification
```

### 2. When a Tracker Entry is Created (status='pending')

```
Moderator submits tracker entry
    ↓
TrackerEntry saved to database
    ↓
send_approval_notification() called
    ↓
System queries NotificationPreference table for admins with email enabled
    ↓
For each admin with notifications enabled:
    - Create Notification object
    - Render email template with tracker entry details
    - Send via SMTP (Gmail)
    ↓
Admin receives email notification
```

## Notification Preferences

Users can configure their preferences at: `/<instance_name>/settings`

### Admin Preferences
- **Master Switch:** Enable/Disable all email notifications
- **Payment Approvals:** Receive notifications for payment approval requests
- **Tracker Approvals:** Receive notifications for tracker entry approval requests
- **Email Address:** Required for receiving notifications

### Customer Preferences (Future)
- **Payment Status Updates:** Get notified when payments are approved/rejected
- **Tracker Status Updates:** Get notified when tracker entries are approved/rejected

## Troubleshooting

### Emails Not Being Sent

1. **Check SMTP Configuration**
   ```bash
   docker-compose logs web | grep -i smtp
   docker-compose logs web | grep -i notification
   ```

2. **Verify Gmail App Password**
   - Make sure the app password is correct: `vbmhddffmrdilbxk`
   - No spaces in the password
   - 16 characters total

3. **Check Notification Preferences**
   - Log in as admin
   - Go to Settings → Notifications
   - Ensure "Email Notifications" is enabled
   - Ensure specific notification types are checked
   - Ensure email address is set

4. **Check if Notifications are Enabled Globally**
   - Verify `NOTIFICATIONS_ENABLED=True` in Docker Compose

5. **Check Console Output (Development Mode)**
   - If SMTP credentials are not set, emails are printed to console
   - Check Docker logs: `docker-compose logs web`

### Emails Going to Spam

If emails are going to spam:
1. Check your Gmail spam folder
2. Mark the email as "Not Spam"
3. Add the sender to your contacts
4. For production, consider using a dedicated email service (SendGrid, AWS SES)

### Database Migration Issues

If you encounter errors related to the `notification_preference` table:

```bash
# Re-run the migration
cd /Users/rsk/Documents/GitHub/lms-dev
python3 migrate_notification_preferences.py
```

## Future Enhancements

The system is designed to be extensible. Future enhancements could include:

1. **SMS Notifications** (via Twilio, AWS SNS)
2. **Slack Notifications** (via webhooks)
3. **Push Notifications** (for mobile apps)
4. **Daily/Weekly Summary Emails**
5. **Customer Status Update Notifications** (when payments/entries are approved/rejected)
6. **Notification History/Audit Log**
7. **Bulk Notification Management**
8. **Custom Email Templates per User**

## Production Deployment

For production deployment:

1. **Update Production Gmail Address**
   - Use a dedicated email account for the LMS (e.g., `lms-noreply@yourdomain.com`)
   - Generate a new app password for the production Gmail account

2. **Update `docker-compose.prod.yml`**
   ```yaml
   - SMTP_USER=lms-noreply@yourdomain.com
   - SMTP_PASSWORD=your-production-app-password
   - SMTP_FROM_EMAIL=lms-noreply@yourdomain.com
   ```

3. **Run Migration on Production**
   ```bash
   python3 migrate_notification_preferences.py
   ```

4. **Restart Production Application**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. **Test Notifications**
   - Create a test payment in production
   - Verify admin receives email

## Support

For any issues or questions:
1. Check the Docker logs: `docker-compose logs web`
2. Review this setup guide
3. Check the notification preferences in Settings
4. Verify SMTP configuration in Docker Compose

---

**Implementation Date:** December 11, 2025  
**System Version:** 1.0.1 (with email notifications)

