# Payment Methods Update

## Overview
This document describes the updates made to the payment system to support only **PayPal**, **Stripe**, and **KHQR Bakong** payment methods, with configurable enable/disable settings in the admin panel.

## Changes Made

### 1. Payment Model (`panel/models.py`)
Updated the `PAYMENT_METHODS` choices to include only:
- **PayPal**: Secure online payment gateway
- **Stripe**: Credit/Debit card processing
- **KHQR Bakong**: Cambodia's national QR payment system

```python
PAYMENT_METHODS = [
    ('paypal', 'PayPal'),
    ('stripe', 'Stripe'),
    ('khqr', 'KHQR Bakong'),
]
```

### 2. Payment Gateway Functions (`panel/payment_gateways.py`)
Added new KHQR Bakong payment gateway functions:

#### `create_khqr_payment(payment)`
- Creates a KHQR payment request
- Generates QR code for user to scan
- Returns QR data and payment reference

#### `check_khqr_payment_status(payment)`
- Checks the current status of a KHQR payment
- Updates payment record when completed
- Adds funds to user account automatically

### 3. Admin System Settings
Added three new boolean settings in the payment group:

| Setting Key | Label | Default | Description |
|------------|-------|---------|-------------|
| `payment_paypal_enabled` | Enable PayPal | `true` | Enable/disable PayPal payment gateway |
| `payment_stripe_enabled` | Enable Stripe | `true` | Enable/disable Stripe payment gateway |
| `payment_khqr_enabled` | Enable KHQR Bakong | `false` | Enable/disable KHQR Bakong payment gateway |

These settings can be managed from **Admin Dashboard → Settings → Payment**.

### 4. Add Funds View (`panel/views.py`)
Updated to:
- Filter payment methods based on system settings
- Only show enabled payment methods to users
- Handle KHQR payment flow
- Added `check_payment_status()` view for async payment verification

### 5. Add Funds Template (`templates/panel/add_funds.html`)
- Updated to dynamically display only enabled payment methods
- Added KHQR Bakong payment card with QR code icon
- Removed hardcoded payment method dropdown

### 6. KHQR Payment Template (`templates/panel/khqr_payment.html`)
New template for KHQR payment flow:
- Displays QR code for scanning
- Shows payment amount and transaction ID
- Auto-checks payment status every 5 seconds
- Provides manual payment status check button
- Shows instructions for completing payment

### 7. URL Routes (`panel/urls.py`)
Added new route:
```python
path('payment/<int:payment_id>/status/', views.check_payment_status, name='check_payment_status')
```

### 8. Database Migration (`panel/migrations/0008_update_payment_methods.py`)
Created migration to update the `Payment.method` field choices.

## Configuration

### Required Settings for KHQR Bakong
Add these settings to your `core/settings.py` or environment variables:

```python
# KHQR Bakong Configuration (NBC Official API)
KHQR_API_URL = 'https://api-bakong.nbc.gov.kh'  # NBC Bakong Open API
KHQR_MERCHANT_ID = 'your_merchant_md5_hash'  # Merchant MD5 hash
KHQR_API_KEY = 'your_api_bearer_token'  # API Bearer token
```

**API Documentation:** https://api-bakong.nbc.gov.kh/

**Endpoints Used:**
- `POST /v1/generate_deeplink_by_qr` - Generate KHQR payment
- `POST /v1/check_transaction_by_hash` - Check transaction status

### Required Settings for PayPal
```python
PAYPAL_MODE = 'sandbox'  # or 'live'
PAYPAL_CLIENT_ID = 'your_client_id'
PAYPAL_CLIENT_SECRET = 'your_client_secret'
PAYPAL_RETURN_URL = 'https://yourdomain.com/payment/paypal/return/'
PAYPAL_CANCEL_URL = 'https://yourdomain.com/payment/paypal/cancel/'
```

### Required Settings for Stripe
```python
STRIPE_PUBLISHABLE_KEY = 'your_publishable_key'
STRIPE_SECRET_KEY = 'your_secret_key'
STRIPE_WEBHOOK_SECRET = 'your_webhook_secret'
STRIPE_CURRENCY = 'usd'
```

## Deployment Steps

1. **Apply Database Migrations**
   ```bash
   python manage.py migrate panel
   ```

2. **Initialize Default Settings**
   ```bash
   python manage.py init_default_settings
   ```
   This will create the payment gateway enable/disable settings.

3. **Configure Payment Gateways**
   - Add the required configuration to your `settings.py` or environment variables
   - Update the admin settings via Admin Dashboard → Settings → Payment

4. **Enable/Disable Payment Methods**
   - Go to **Admin Dashboard → Settings**
   - Filter by **Payment** group
   - Toggle the enable/disable settings for each payment method:
     - Enable PayPal
     - Enable Stripe
     - Enable KHQR Bakong

5. **Test Payment Flow**
   - Test each enabled payment method
   - Verify payment status updates correctly
   - Confirm funds are added to user balance

## Admin Panel Features

### Managing Payment Methods
1. Navigate to **Admin Dashboard → Settings**
2. Click on **Payment** tab
3. Find the payment gateway settings:
   - **Enable PayPal**: Toggle to enable/disable PayPal
   - **Enable Stripe**: Toggle to enable/disable Stripe
   - **Enable KHQR Bakong**: Toggle to enable/disable KHQR

### Payment Method Visibility
- Only enabled payment methods will be shown on the **Add Funds** page
- Users cannot select disabled payment methods
- If all payment methods are disabled, all will be shown by default (fallback)

## User Experience

### Add Funds Page
Users will see payment method cards for enabled gateways:

1. **PayPal** - Secure payment with redirect to PayPal
2. **Stripe** - Credit/Debit card with embedded payment form
3. **KHQR Bakong** - QR code payment for Cambodian banks

### KHQR Payment Flow
1. User selects KHQR Bakong and enters amount
2. System generates QR code
3. User scans QR code with Bakong or any KHQR-enabled banking app
4. User completes payment in their banking app
5. System auto-checks payment status every 5 seconds
6. Upon successful payment, funds are added to account
7. User is redirected to dashboard

## API Integration

### KHQR Payment Status Check
The KHQR payment template automatically checks payment status via AJAX:

```javascript
fetch('/payment/<payment_id>/status/')
  .then(response => response.json())
  .then(data => {
    if (data.status === 'completed') {
      // Payment successful - redirect to dashboard
    }
  });
```

## Security Considerations

1. **Payment Gateway Credentials**: Store sensitive API keys in environment variables
2. **Webhook Verification**: Stripe webhook signature is verified
3. **User Authentication**: All payment endpoints require login
4. **CSRF Protection**: POST requests are CSRF protected (except webhooks)
5. **Payment Ownership**: Users can only check status of their own payments

## Troubleshooting

### Payment Methods Not Showing
- Check if payment methods are enabled in Admin Settings
- Verify settings are saved correctly
- Clear browser cache

### KHQR Payment Not Working
- Verify KHQR API credentials in settings
- Check KHQR_API_URL is accessible
- Review error logs for API response errors

### PayPal/Stripe Issues
- Verify API credentials are correct
- Check sandbox vs live mode settings
- Review webhook configuration

## Future Enhancements

Potential improvements for the payment system:

1. **Multi-currency Support**: Add support for KHR, THB, etc.
2. **Payment History Export**: Download payment reports
3. **Recurring Payments**: Subscription-based payments
4. **Refund System**: Automated refund processing
5. **Payment Analytics**: Dashboard with payment statistics
6. **Multiple KHQR Providers**: Support for different KHQR providers

## Notes

- Old payment methods (ABA, Wing, PiPay, USDT, TrueMoney, etc.) have been removed
- Existing payment records with old methods will remain in the database
- Migration only updates the model field choices, not existing data
- Admin can still view historical transactions with deprecated payment methods

## Support

For issues or questions:
- Review logs in Django admin
- Check payment gateway documentation
- Contact technical support team

