# Maintenance Mode Setup Guide

## Quick Start

The maintenance mode feature has been fully implemented. Follow these steps to start using it:

### Step 1: Initialize Default Settings

Run this command to create the maintenance mode settings in your database:

```bash
python manage.py init_default_settings
```

This will create:
- `maintenance_mode` setting (default: disabled)
- `maintenance_message` setting (default message included)

### Step 2: Test the Feature

#### Option A: Enable from Admin Dashboard
1. Login as an admin user
2. Navigate to: Admin Dashboard (`/admin/`)
3. You'll see a "System is Online" card at the top
4. Click "Enable Maintenance" button
5. Confirm the action
6. The page will reload showing "Maintenance Mode is Active"

#### Option B: Enable from Settings Page
1. Login as an admin user
2. Navigate to: Admin → Settings (`/admin/settings/`)
3. Filter by "Maintenance" group
4. Toggle "Maintenance Mode" switch to ON
5. Click "Save" or "Update" button

### Step 3: Test User Experience

1. Open the site in an incognito window or different browser
2. Try to access any page (e.g., `/services/`, `/orders/`)
3. You should be redirected to the maintenance page
4. Verify your custom message appears
5. Verify you cannot access any other pages

### Step 4: Test Admin Access During Maintenance

1. While maintenance mode is active
2. Login as admin in incognito window
3. Verify you can access all features normally
4. You should see admin notices about maintenance being active

### Step 5: Disable Maintenance Mode

1. Click "Disable Maintenance" button on dashboard
2. Or toggle OFF in settings
3. Verify non-admin users can now access the site

## Customization

### Change the Maintenance Message

1. Go to: Admin → Settings → Maintenance group
2. Find "Maintenance Message" setting
3. Edit the textarea with your custom message
4. Save changes
5. The new message will appear immediately on the maintenance page

Example messages:
```
"We're upgrading our systems to serve you better. We'll be back in 2 hours!"

"Scheduled maintenance in progress. Expected completion: 11:00 PM UTC."

"Our team is working hard to improve your experience. Please check back soon!"
```

### Customize the Maintenance Page

Edit: `templates/panel/maintenance.html`

You can customize:
- Colors and styling
- Animations
- Layout
- Additional information
- Branding

## API Endpoints

### Toggle Maintenance Mode (AJAX)

**Endpoint**: `POST /admin/settings/toggle-maintenance/`

**Access**: Admin only

**Response**:
```json
{
    "success": true,
    "maintenance_mode": true,
    "message": "Maintenance mode enabled"
}
```

**Usage in JavaScript**:
```javascript
fetch('/admin/settings/toggle-maintenance/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    }
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        console.log(data.message);
        location.reload();
    }
});
```

## Files Changed

### New Files
- `panel/middleware.py` - Maintenance mode middleware
- `templates/panel/maintenance.html` - Maintenance page template
- `MAINTENANCE_MODE.md` - Full documentation
- `MAINTENANCE_MODE_SETUP.md` - This setup guide

### Modified Files
- `core/settings.py` - Added middleware
- `panel/views.py` - Added maintenance and toggle views
- `panel/urls.py` - Added maintenance routes
- `templates/panel/admin/dashboard.html` - Added toggle button and status

## Architecture

```
Request → Middleware Check → Is Maintenance Enabled?
                                    ↓
                          YES ←────────────→ NO
                           ↓                  ↓
                    Is User Admin?      Allow Access
                           ↓
                    YES ←───→ NO
                     ↓         ↓
               Allow Access   Redirect to
                             Maintenance Page
```

## Settings Structure

```python
# In database (SystemSetting model)
maintenance_mode = {
    'key': 'maintenance_mode',
    'value': 'false',  # 'true' or 'false'
    'setting_type': 'boolean',
    'group': 'maintenance'
}

maintenance_message = {
    'key': 'maintenance_message',
    'value': 'Your custom message here',
    'setting_type': 'textarea',
    'group': 'maintenance'
}
```

## Best Practices

### When to Use Maintenance Mode

✅ **Good Use Cases**:
- Database migrations
- Major system updates
- Server maintenance
- Critical bug fixes
- Data backups/restores
- Security patches

❌ **Avoid Using For**:
- Minor updates (use rolling deployments)
- Regular bug fixes (deploy without downtime)
- Testing (use staging environment)

### Communication

Before enabling maintenance mode:
1. Notify users in advance (if possible)
2. Set a clear maintenance message
3. Include estimated completion time
4. Provide contact information
5. Update social media/status page

### Duration

- Keep maintenance as short as possible
- Test changes in staging first
- Have a rollback plan
- Monitor admin access during maintenance
- Verify everything works before disabling

## Troubleshooting

### Problem: Settings Not Found

**Error**: `SystemSetting.DoesNotExist`

**Solution**:
```bash
python manage.py init_default_settings
```

### Problem: Middleware Not Working

**Check**:
1. Is `panel.middleware.MaintenanceModeMiddleware` in `MIDDLEWARE` list?
2. Is it placed after `AuthenticationMiddleware`?
3. Have you restarted the Django server?

**Restart Server**:
```bash
# Stop current server (Ctrl+C)
python manage.py runserver
```

### Problem: Can't Access Admin During Maintenance

**Solution**:
1. Go to `/login/`
2. Login with superuser credentials
3. You should now have full access
4. Navigate to settings and disable maintenance

### Problem: Maintenance Page Looks Broken

**Check**:
1. Are static files being served?
2. Is `DEBUG = True` or have you run `collectstatic`?
3. Check browser console for CSS/JS errors

**Solution**:
```bash
python manage.py collectstatic
```

## Security Notes

1. **Admin Only**: Only users with admin role or superuser flag can:
   - Access site during maintenance
   - Toggle maintenance mode
   - Edit maintenance settings

2. **CSRF Protection**: All POST requests use CSRF tokens

3. **No Backdoors**: There are no secret URLs to bypass maintenance (except login)

4. **Audit Trail**: Setting changes are tracked with `updated_by` field

## Testing Checklist

- [ ] Settings initialized successfully
- [ ] Can enable maintenance mode from dashboard
- [ ] Can enable maintenance mode from settings
- [ ] Non-admin users see maintenance page
- [ ] Admins can access site during maintenance
- [ ] Custom message displays correctly
- [ ] Can disable maintenance mode
- [ ] Toggle button works via AJAX
- [ ] Maintenance page is responsive (mobile-friendly)
- [ ] Multiple languages work (if applicable)

## Production Deployment

Before deploying to production:

1. **Test thoroughly in staging**
2. **Document maintenance procedures**
3. **Train team on toggle functionality**
4. **Set up monitoring**
5. **Prepare maintenance message templates**
6. **Plan communication strategy**

### Deployment Commands

```bash
# 1. Pull latest code
git pull origin main

# 2. Install dependencies (if needed)
pip install -r requirements.txt

# 3. Run migrations (if any new ones)
python manage.py migrate

# 4. Initialize settings
python manage.py init_default_settings

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Restart server
sudo systemctl restart gunicorn  # or your server
```

## Support

For issues or questions:
1. Check `MAINTENANCE_MODE.md` for detailed documentation
2. Review code in `panel/middleware.py`
3. Check Django logs for errors
4. Contact development team

---

**Setup Complete!** 🎉

Your maintenance mode system is ready to use.

