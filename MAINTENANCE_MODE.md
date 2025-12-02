# Maintenance Mode Feature

## Overview
The VinFlow panel now includes a comprehensive maintenance mode system that allows administrators to temporarily restrict access to the site while performing system updates or maintenance.

## Features

### 1. Middleware Protection
- Automatically redirects non-admin users to a maintenance page when enabled
- Admins can still access all features during maintenance
- Static and media files remain accessible
- Login/logout functionality remains available for admins

### 2. Admin Dashboard Toggle
- Quick toggle button on the admin dashboard
- Visual indicator showing current maintenance status
- One-click enable/disable functionality
- Real-time status updates

### 3. Customizable Maintenance Page
- Professional maintenance page with animated graphics
- Customizable maintenance message
- Contact information display
- Admin login link
- Admin notification when logged in during maintenance

### 4. System Settings Integration
- Two settings in the SystemSetting model:
  - `maintenance_mode` (boolean): Enable/disable maintenance mode
  - `maintenance_message` (textarea): Custom message to display

## How to Use

### For Administrators

#### Enable Maintenance Mode
1. **Via Admin Dashboard:**
   - Navigate to Admin Dashboard
   - Click "Enable Maintenance" button at the top
   - Confirm the action
   - Page will reload with maintenance mode active

2. **Via Settings Page:**
   - Navigate to Admin → Settings
   - Find "Maintenance" section
   - Toggle the "Maintenance Mode" switch
   - Save settings

#### Disable Maintenance Mode
- Follow the same steps as enabling, but click "Disable Maintenance" button
- Or toggle off the switch in Settings

#### Customize Maintenance Message
1. Navigate to Admin → Settings
2. Find "Maintenance" section
3. Edit the "Maintenance Message" textarea
4. Save settings

### For Users
When maintenance mode is enabled:
- All non-admin users are redirected to a maintenance page
- The maintenance page displays:
  - A professional animated maintenance message
  - The custom maintenance message set by admin
  - Contact email (if configured)
  - Admin login link (for administrators)
- Users cannot access any other pages until maintenance is disabled

## Technical Details

### Files Modified/Created

1. **panel/middleware.py** (NEW)
   - `MaintenanceModeMiddleware`: Checks maintenance mode status on every request
   - Allows admin access and essential pages
   - Redirects non-admins to maintenance page

2. **panel/views.py**
   - Added `maintenance()` view: Renders maintenance page
   - Added `toggle_maintenance_mode()` view: AJAX endpoint for quick toggle
   - Updated `admin_dashboard()`: Passes maintenance status to template

3. **panel/urls.py**
   - Added route for maintenance page
   - Added route for toggle endpoint

4. **core/settings.py**
   - Added `MaintenanceModeMiddleware` to MIDDLEWARE list

5. **templates/panel/maintenance.html** (NEW)
   - Beautiful, responsive maintenance page
   - Supports internationalization
   - Shows custom message and contact info
   - Admin-specific notices

6. **templates/panel/admin/dashboard.html**
   - Added maintenance mode status card
   - Added toggle button with AJAX functionality
   - Visual indicators for active/inactive status

### Settings Database

The feature uses two SystemSetting entries:

```python
# Maintenance Mode On/Off
{
    'key': 'maintenance_mode',
    'label': 'Maintenance Mode',
    'setting_type': 'boolean',
    'group': 'maintenance',
    'default_value': 'false',
    'description': 'Enable maintenance mode'
}

# Custom Message
{
    'key': 'maintenance_message',
    'label': 'Maintenance Message',
    'setting_type': 'textarea',
    'group': 'maintenance',
    'default_value': 'We are currently performing maintenance. Please check back soon.',
    'description': 'Message to display during maintenance'
}
```

### Middleware Logic

```python
1. Check if maintenance_mode setting is enabled
2. If disabled → Allow access to all
3. If enabled:
   - Allow static/media files
   - Allow maintenance page itself
   - Allow login/logout/language pages
   - Check if user is admin/superuser → Allow full access
   - Otherwise → Redirect to maintenance page
```

## Default Configuration

### Default Settings
- **Maintenance Mode**: Disabled (false)
- **Maintenance Message**: "We are currently performing maintenance. Please check back soon."
- **Site Name**: VinFlow (from general settings)
- **Contact Email**: From site_email setting

### Initializing Settings
Run the management command to initialize default settings:

```bash
python manage.py init_default_settings
```

This will create the maintenance mode settings if they don't exist.

## Security Considerations

1. **Admin Access**: Only users with:
   - `is_superuser = True`, OR
   - `profile.role = 'admin'`
   
   can access the site during maintenance.

2. **Login Protection**: Login page remains accessible so admins can authenticate during maintenance.

3. **Static Files**: CSS, JS, and media files remain accessible to render the maintenance page properly.

4. **CSRF Protection**: Toggle endpoint uses Django's CSRF protection.

## Internationalization

The maintenance page supports multiple languages:
- English (en)
- Khmer (km)

All text is translatable using Django's i18n framework.

## Testing

### Test Scenarios

1. **Enable Maintenance Mode**
   - Login as admin
   - Enable maintenance mode
   - Verify maintenance status shows as active
   - Verify you can still access all admin features

2. **Non-Admin Access**
   - Open site in incognito/different browser
   - Verify redirect to maintenance page
   - Verify custom message is displayed
   - Verify cannot access any other pages

3. **Admin Access During Maintenance**
   - Login as admin while maintenance is active
   - Verify full site access
   - Verify admin notice appears on maintenance page

4. **Disable Maintenance Mode**
   - Click disable maintenance button
   - Verify status changes to online
   - Test with non-admin user that site is accessible

5. **Custom Message**
   - Change maintenance message in settings
   - Enable maintenance mode
   - Verify new message appears on maintenance page

## Troubleshooting

### Issue: Can't access site after enabling maintenance
**Solution**: Access the admin panel at the login page. If you're an admin, you should still be able to log in and disable maintenance.

### Issue: Maintenance page not showing custom message
**Solution**: Check that the `maintenance_message` setting exists in SystemSetting model. Run `python manage.py init_default_settings`.

### Issue: Static files not loading on maintenance page
**Solution**: Ensure `STATIC_URL` and `MEDIA_URL` are properly configured in settings.py.

### Issue: Toggle button not working
**Solution**: Check browser console for JavaScript errors. Ensure CSRF token is present and valid.

## Future Enhancements

Possible improvements:
- Scheduled maintenance mode with start/end times
- Multiple maintenance messages for different languages
- Maintenance mode history/logs
- Email notifications to users when maintenance is scheduled
- Countdown timer on maintenance page
- IP whitelist for specific users during maintenance

## Support

For issues or questions about the maintenance mode feature, please:
1. Check this documentation
2. Review the code in `panel/middleware.py` and related files
3. Contact the development team

---

**Last Updated**: December 2025  
**Version**: 1.0

