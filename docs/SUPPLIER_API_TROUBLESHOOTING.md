# 🔧 Supplier API Troubleshooting Guide

## Issue: Orders Not Getting Response from Supplier

If orders are stuck in "Pending" status and not getting responses from the supplier API, follow these steps:

---

## Step 1: Check Supplier API Configuration

Run the diagnostic command to check your configuration:

```bash
python3 manage.py check_supplier_config
```

This will show you:
- ✅ API URL configuration
- ✅ API Key status (configured or missing)
- ✅ Connection test results
- ✅ Supplier balance
- ✅ Pending order counts
- ✅ Recent API activity logs

---

## Step 2: Configure API Key (if missing)

### Method 1: Via Admin Panel (Recommended)
1. Log in to your admin account
2. Go to **Settings** → **API Settings**
3. Find **"JAP API Key"**
4. Enter your API key from [JustAnotherPanel.com](https://justanotherpanel.com/)
5. Click **Save**

### Method 2: Via Environment Variable
Add to your `.env` file:
```bash
JAP_API_KEY=your_actual_api_key_here
```

Then restart your Django server:
```bash
# Stop the server (Ctrl+C)
# Start it again
python3 manage.py runserver
```

---

## Step 3: Get Your API Key

If you don't have an API key yet:

1. Go to https://justanotherpanel.com/
2. Register or log in to your account
3. Navigate to **API** section
4. Copy your **API Key**
5. Add balance to your JAP account (this is your supplier account)

**Important:** 
- The JAP account is your **supplier account** (where you buy services wholesale)
- Your VinFlow SMM Panel is your **reseller platform** (where you sell to customers)
- Make sure your JAP account has sufficient balance

---

## Step 4: Retry Pending Orders

Once your API key is configured, retry pending orders:

### Retry all pending orders:
```bash
python3 manage.py retry_pending_orders --all
```

### Retry orders from last 24 hours:
```bash
python3 manage.py retry_pending_orders --recent 24
```

### Retry orders from last 1 hour:
```bash
python3 manage.py retry_pending_orders --recent 1
```

### Retry a specific order:
```bash
python3 manage.py retry_pending_orders --order-id ORD-12345
```

---

## Step 5: Monitor Order Logs

You can now view detailed order logs in the admin panel:

1. Go to **Admin Panel** → **Orders Management**
2. Click **"View Details"** button on any order
3. See complete activity timeline with:
   - 🟢 Order creation
   - 🔵 API calls
   - 🟣 API responses
   - 🔴 Errors
   - 🟡 Status changes
   - 💰 Balance deductions

---

## Common Issues & Solutions

### ❌ Issue: "API Key: NOT CONFIGURED"
**Solution:** Follow Step 2 above to configure your API key.

### ❌ Issue: "Connection timed out"
**Solution:** 
- Check your internet connection
- Check if JustAnotherPanel.com is accessible
- Increase timeout in Settings → API Settings → "Supplier API Timeout"

### ❌ Issue: "API Error: Invalid API key"
**Solution:**
- Verify your API key is correct
- Check if you copied the entire key without spaces
- Generate a new key from JAP dashboard

### ❌ Issue: "Insufficient balance"
**Solution:**
- Check your JAP supplier account balance
- Add funds to your JAP account
- Run: `python3 manage.py check_supplier_config` to see current balance

### ❌ Issue: Orders stay in "Pending" status
**Solution:**
1. Check if Celery/Redis is running (for background tasks)
2. If not using Celery, the system will run tasks synchronously
3. Check Django logs for errors
4. Retry orders using the retry command

---

## Testing the Integration

### Test 1: Check Configuration
```bash
python3 manage.py check_supplier_config
```
Should show: ✅ API Connection: SUCCESS

### Test 2: Create a Test Order
1. Log in as a user
2. Go to **New Order**
3. Select a cheap service (e.g., 100 Instagram followers)
4. Enter a test link
5. Submit order
6. Check order details in Admin Panel

### Test 3: View Order Logs
1. Go to Admin → Orders Management
2. Click "View Details" on the test order
3. Verify you see logs for:
   - Order Created
   - Balance Deducted
   - API Call Initiated
   - Supplier Response
   - Status Change

---

## Automated Status Sync

Your system is configured to automatically sync order status from the supplier every 5 minutes.

To manually sync all processing orders:
```bash
python3 manage.py sync_order_status
```

---

## Need Help?

If you're still experiencing issues:

1. **Check Django logs:**
   ```bash
   tail -f /path/to/your/django.log
   ```

2. **Check order logs in database:**
   - Look at the order details modal in admin panel
   - Check for error logs with red indicators

3. **Verify supplier services:**
   - Ensure services in your database have correct `external_service_id`
   - These IDs must match the service IDs from JAP

4. **Contact JAP Support:**
   - If the issue is with their API
   - Check their API documentation
   - Verify your account status

---

## Prevention Tips

✅ **Always keep supplier balance topped up**
✅ **Monitor order logs regularly**
✅ **Set up alerts for failed orders**
✅ **Test new services before offering to customers**
✅ **Keep API timeout reasonable (30 seconds recommended)**
✅ **Enable auto-sync for order status updates**

---

## Quick Reference Commands

```bash
# Check configuration
python3 manage.py check_supplier_config

# Retry pending orders
python3 manage.py retry_pending_orders --all

# Retry recent orders (last 24h)
python3 manage.py retry_pending_orders --recent 24

# Retry specific order
python3 manage.py retry_pending_orders --order-id ORD-12345

# Sync order status
python3 manage.py sync_order_status

# Run migrations (for OrderLog table)
python3 manage.py migrate panel

# Initialize default settings
python3 manage.py init_default_settings
```

---

**Last Updated:** December 2025
**Version:** 1.0

