# Common Issues and Solutions

This document tracks common issues encountered during development and their solutions.

## Modal Backdrop Issue with Flash Messages

**Issue**: When a form inside a Bootstrap modal is submitted, the page reloads to show a Flask flash message, but the modal backdrop (dark overlay) remains on the screen, making the page unresponsive.

**Symptoms**:
- Dark overlay remains after modal form submission
- Cannot click anything on the page
- Body scroll is disabled
- `modal-backdrop` and `modal-open` class persist after reload

**Root Cause**: 
When a form in a modal submits and the page reloads, Bootstrap's modal backdrop element and body classes are not automatically cleaned up because the page reload happens before Bootstrap can properly close the modal.

**Solution** (implemented in `templates/base.html`):

```javascript
// Fix modal backdrop issue when page reloads with flash messages
document.addEventListener('DOMContentLoaded', function() {
    // Check if there are flash messages
    var flashMessages = document.querySelectorAll('.alert');
    if (flashMessages.length > 0) {
        // Remove any lingering modal backdrops
        var backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(function(backdrop) {
            backdrop.remove();
        });
        
        // Remove modal-open class from body
        document.body.classList.remove('modal-open');
        
        // Reset body style
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    }
});
```

**When This Happens**:
- Email editing modal in user management
- Any form submission from within a Bootstrap modal that redirects with a flash message

**Prevention**:
Always include this JavaScript in the base template when using modals with forms that trigger page reloads.

**Alternative Solutions**:
1. Use AJAX form submission instead of regular form submission
2. Redirect to a different page after form submission
3. Use JavaScript to manually close modal before form submission

---

## Email Notification Not Sending

**Issue**: Emails are not being sent even though SMTP is configured.

**Common Causes**:
1. **SMTP credentials not set in Docker environment**
   - Check `docker-compose.dev.yml` or `docker-compose.prod.yml`
   - Verify all SMTP_* environment variables are present
   
2. **Gmail app password incorrect**
   - App password should be 16 characters (no spaces)
   - Regenerate if necessary at: https://myaccount.google.com/apppasswords

3. **Notifications disabled for user**
   - Check Settings → Notifications
   - Ensure "Email Notifications" toggle is ON
   - Verify specific notification types are checked

4. **User email not set**
   - Go to Admin → Users
   - Click "Edit Email" button for the user
   - Add valid email address

5. **NOTIFICATIONS_ENABLED is False**
   - Check environment variable in Docker Compose
   - Should be set to `True` for production

**Debugging Steps**:
```bash
# Check Docker logs for email-related errors
docker-compose logs web | grep -i "smtp\|email\|notification"

# Check if emails are being printed to console (development mode)
docker-compose logs web | grep "EMAIL NOTIFICATION"
```

**Solution**: See `EMAIL_NOTIFICATION_SETUP.md` for complete configuration guide.

---

## Database Migration Issues

**Issue**: New database columns or tables not appearing after code changes.

**Solution**: 
Run the appropriate migration script:
```bash
# For notification preferences
python3 migrate_notification_preferences.py

# For other migrations, check the migrate_*.py files
```

**Prevention**: Always create a migration script when adding new models or columns.

---

## Port Already in Use

**Issue**: `docker-compose up` fails with "port is already allocated" error.

**Solution**:
```bash
# Find and kill the process using the port
lsof -ti:9090 | xargs kill -9  # For dev (port 9090)
lsof -ti:8080 | xargs kill -9  # For prod (port 8080)

# Or use docker-compose down first
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d
```

---

## Changes Not Appearing After Code Update

**Issue**: Code changes don't appear after editing files.

**Solution**:
```bash
# Rebuild and restart Docker container
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d
```

For Python code changes only (no Dockerfile changes):
```bash
docker-compose -f docker-compose.dev.yml restart
```

---

## Session/Login Issues

**Issue**: Users get logged out randomly or can't log in.

**Common Causes**:
1. `SECRET_KEY` changed between restarts
2. Database instance mismatch
3. Cookie domain issues

**Solution**: Ensure `SECRET_KEY` is set consistently in the application.

---

## Last Updated
December 11, 2025

