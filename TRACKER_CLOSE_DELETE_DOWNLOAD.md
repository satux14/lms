# Tracker Close, Delete & Download Features

## Overview

Three powerful new features have been added to the Daily Tracker system:
1. **Users can close/hide trackers** - Hide completed trackers from their view
2. **Admin can delete trackers** - Remove unnecessary or test trackers
3. **Admin can download Excel files** - Export tracker data

## Features

### 1. User: Close Tracker

**What it does:**
- User can close/hide their tracker from their dashboard
- Tracker becomes invisible to the user
- Admin can still see and manage it
- All data remains intact

**How to use:**
1. User goes to their tracker page
2. Click "Close Tracker" button (yellow/warning button)
3. Confirm the action
4. Tracker disappears from user's view

**User Experience:**
- Tracker no longer shows on dashboard
- "Daily Tracker" link disappears
- User sees message: "Contact admin if you need to reopen it"

**Admin Can:**
- Still see the tracker (marked as "Closed by User")
- Download the Excel file
- Add entries
- Reopen it for the user

---

### 2. Admin: Delete Tracker

**What it does:**
- Soft delete - marks tracker as deleted (`is_active = False`)
- Tracker disappears from admin lists
- Excel file remains on disk (not deleted)
- Can be recovered by manually setting `is_active = True` in database

**How to use:**
1. Admin goes to "All Trackers" page
2. Click red trash icon for a tracker
3. Confirm deletion in modal
4. Tracker is marked as deleted

**What happens:**
- Tracker removed from tracker lists
- User can't see it
- Admin can't see it in normal views
- Excel file remains in `instances/{instance}/daily-trackers/`

**Safety:**
- Confirmation modal prevents accidental deletion
- Soft delete allows recovery if needed
- Excel file preserved for auditing

---

### 3. Admin: Download Excel

**What it does:**
- Downloads the actual Excel file for a tracker
- Gets all formulas, calculations, and data
- File can be opened in Microsoft Excel
- Useful for offline analysis, backup, or sharing

**How to use:**

**From Tracker List:**
1. Go to "All Trackers"
2. Click green download icon
3. File downloads automatically

**From Tracker View:**
1. Open any tracker
2. Click "Download Excel" button (green)
3. File downloads automatically

**Downloaded filename format:**
```
{username}_{tracker_name}_{original_filename}
Example: john_Johns Q4 Investment_tracker_john_20241016_143025.xlsx
```

**What you can do with downloaded file:**
- Open in Excel for detailed analysis
- Share with user via email
- Create backups
- Generate reports
- Modify offline (then re-upload if needed)

---

### 4. Admin: Reopen Closed Tracker

**What it does:**
- Reopens a tracker that was closed by the user
- Makes tracker visible to user again
- Appears on user's dashboard

**How to use:**
1. Admin goes to "All Trackers"
2. See trackers with status "Closed by User"
3. Click orange "Reopen" icon (folder-open)
4. Tracker becomes visible to user again

**Use cases:**
- User accidentally closed it
- Tracker needs to continue
- User requests to see it again

---

## UI Elements

### User Daily Tracker Page

**New Button:**
```
[Back to Dashboard] [Close Tracker (⚠️)]
```

**Close Modal:**
- Warning about consequences
- Clear explanation
- Cancel or Confirm buttons

### Admin Tracker List

**Status Column:**
- 🟢 **Active** - Normal tracker
- ⚪ **Closed by User** - User has hidden it

**Action Buttons:**
- 👁️ **View** (Blue) - View tracker details
- ✏️ **Edit** (Purple) - Add entry
- ⬇️ **Download** (Green) - Download Excel file
- 📂 **Reopen** (Orange) - Only shown for closed trackers
- 🗑️ **Delete** (Red) - Delete tracker

### Admin Tracker View

**New Button:**
```
[Add Entry] [Download Excel] [Back]
```

---

## Database Changes

### New Column: `is_closed_by_user`

```sql
ALTER TABLE daily_tracker 
ADD COLUMN is_closed_by_user BOOLEAN DEFAULT 0;
```

**Values:**
- `False` (0) - Tracker is active for user (default)
- `True` (1) - User has closed/hidden it

**Query Logic:**

**For Users (show only active, not closed):**
```python
tracker = get_daily_tracker_query().filter_by(
    user_id=current_user.id,
    is_active=True,
    is_closed_by_user=False
).first()
```

**For Admin (show all active trackers, including closed):**
```python
trackers = get_daily_tracker_query().filter_by(
    is_active=True  # Only check is_active, not is_closed_by_user
).all()
```

---

## Migration

### For New Installations

Run the complete migration:
```bash
python3 migrate_daily_tracker.py
```

The `is_closed_by_user` column will be included automatically.

### For Existing Installations

Run the additional migration:
```bash
python3 migrate_tracker_features.py
```

This adds the `is_closed_by_user` column to existing tables.

**What it does:**
- Adds `is_closed_by_user` column
- Sets all existing trackers to `False` (active)
- Shows success/failure for each instance

---

## Routes Added

### User Routes

**Close Tracker:**
```
POST /<instance>/customer/daily-tracker/close
```

### Admin Routes

**Delete Tracker:**
```
POST /<instance>/admin/daily-trackers/<tracker_id>/delete
```

**Reopen Tracker:**
```
POST /<instance>/admin/daily-trackers/<tracker_id>/reopen
```

**Download Tracker:**
```
GET /<instance>/admin/daily-trackers/<tracker_id>/download
```

---

## Use Cases

### Use Case 1: User Completes Tracker

**Scenario:** User's 100-day investment scheme is complete

1. User views their tracker
2. All days are filled
3. User clicks "Close Tracker"
4. Tracker hidden from user's dashboard
5. Admin can still see it for record-keeping

### Use Case 2: Test Tracker Cleanup

**Scenario:** Admin created test trackers during setup

1. Admin goes to "All Trackers"
2. Identifies test trackers
3. Clicks delete for each
4. Trackers removed from system
5. Excel files remain for audit

### Use Case 3: Monthly Reporting

**Scenario:** Admin needs to create monthly reports

1. Admin goes to each user's tracker
2. Clicks "Download Excel"
3. Opens files in Excel
4. Compiles data for monthly report
5. Shares with management

### Use Case 4: User Requested Reopen

**Scenario:** User accidentally closed tracker, wants it back

1. User contacts admin
2. Admin goes to "All Trackers"
3. Sees tracker with "Closed by User" status
4. Clicks "Reopen" button
5. Tracker appears on user's dashboard again

---

## Best Practices

### For Users

✅ **Close trackers when:**
- Investment scheme is complete
- No longer need to check daily
- Want cleaner dashboard

❌ **Don't close if:**
- Scheme is ongoing
- Still making daily payments
- Need to track progress

### For Admin

✅ **Download trackers for:**
- Monthly/quarterly reports
- Backup before major changes
- Sharing with stakeholders
- Offline analysis

✅ **Delete trackers when:**
- Test/demo trackers no longer needed
- Duplicate entries created by mistake
- User account closed permanently

❌ **Don't delete:**
- Active user trackers
- Recent historical data
- Unless you have a backup

✅ **Reopen trackers when:**
- User requests it
- Accidentally closed
- Scheme extended

---

## Security

### Permissions

**Users can:**
- ✅ Close their own tracker
- ❌ Cannot reopen (must ask admin)
- ❌ Cannot delete
- ❌ Cannot download Excel

**Admin can:**
- ✅ View all trackers (including closed)
- ✅ Delete any tracker
- ✅ Download any Excel file
- ✅ Reopen closed trackers
- ✅ Add entries to any tracker

### Data Protection

- Soft delete preserves data
- Excel files never auto-deleted
- Close action is reversible
- All actions logged in `updated_at`

---

## Troubleshooting

### User can't find their tracker

**Possible causes:**
1. User closed it → Admin needs to reopen
2. Admin deleted it → Need to restore from backup
3. Not created yet → Admin needs to create

**Solution:**
- Admin checks "All Trackers"
- Look for "Closed by User" status
- Click "Reopen" if closed

### Download fails

**Possible causes:**
1. Excel file missing from disk
2. File permissions issue
3. Filename contains invalid characters

**Solution:**
- Check file exists in `instances/{instance}/daily-trackers/`
- Verify file permissions (should be readable)
- Check server logs for errors

### Delete doesn't work

**Possible causes:**
1. JavaScript not loaded
2. Modal library (Bootstrap) issue
3. Database connection error

**Solution:**
- Check browser console for errors
- Verify Bootstrap JavaScript is loaded
- Test database connection

---

## Summary

These three features complete the tracker lifecycle:

1. **Create** → Admin creates tracker for user
2. **Use** → User views and tracks progress
3. **Close** → User closes when done
4. **Manage** → Admin can reopen, download, or delete
5. **Archive** → Deleted trackers preserved as Excel files

**Result:** Clean, organized tracker management with full control! 🎉

