# Payment Gateway Integration Setup Guide

This document explains how to set up PayPal and Stripe payment gateways for the VinFlow SMM Panel.

## Installation

1. Install required packages:
```bash
pip install stripe paypalrestsdk
```

Or update requirements:
```bash
pip install -r requirements.txt
```

## Configuration

### 1. Update Settings

Edit `core/settings.py` and update the payment gateway credentials:

```python
# PayPal Settings
PAYPAL_CLIENT_ID = 'YOUR_PAYPAL_CLIENT_ID'
PAYPAL_CLIENT_SECRET = 'YOUR_PAYPAL_CLIENT_SECRET'
PAYPAL_MODE = 'sandbox'  # 'sandbox' for testing, 'live' for production
PAYPAL_RETURN_URL = 'https://yourdomain.com/panel/payment/paypal/return/'
PAYPAL_CANCEL_URL = 'https://yourdomain.com/panel/payment/paypal/cancel/'

# Stripe Settings
STRIPE_PUBLISHABLE_KEY = 'YOUR_STRIPE_PUBLISHABLE_KEY'
STRIPE_SECRET_KEY = 'YOUR_STRIPE_SECRET_KEY'
STRIPE_WEBHOOK_SECRET = 'YOUR_STRIPE_WEBHOOK_SECRET'
STRIPE_CURRENCY = 'usd'
```

### 2. Get PayPal Credentials

1. Go to [PayPal Developer Dashboard](https://developer.paypal.com/)
2. Create a new app or use existing one
3. Copy the Client ID and Secret
4. For production, switch to Live mode and update credentials

### 3. Get Stripe Credentials

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Get your API keys from Developers > API keys
3. Set up webhook endpoint:
   - Go to Developers > Webhooks
   - Add endpoint: `https://yourdomain.com/panel/payment/stripe/webhook/`
   - Select events: `payment_intent.succeeded`, `payment_intent.payment_failed`
   - Copy the webhook signing secret

### 4. Run Database Migration

Create and apply migration for the new `gateway_payment_id` field:

```bash
python manage.py makemigrations panel
python manage.py migrate
```

## Features

### PayPal Integration
- Users can pay via PayPal
- Redirects to PayPal for payment approval
- Returns to site after payment completion
- Automatically adds funds to user account on success

### Stripe Integration
- Users can pay via credit/debit card
- Secure card input using Stripe Elements
- Real-time card validation
- Webhook support for payment confirmation
- Automatically adds funds to user account on success

## Payment Flow

### PayPal Flow:
1. User selects amount and PayPal as payment method
2. System creates PayPal payment and redirects to PayPal
3. User approves payment on PayPal
4. PayPal redirects back to return URL
5. System executes payment and adds funds to account

### Stripe Flow:
1. User selects amount and Stripe as payment method
2. System creates Stripe Payment Intent
3. User enters card details on secure form
4. Payment is processed via Stripe
5. On success, funds are added to account
6. Webhook confirms payment (optional but recommended)

## Security Notes

- Never commit API keys to version control
- Use environment variables for sensitive data in production
- Enable webhook signature verification for Stripe
- Use HTTPS in production
- Test thoroughly in sandbox/test mode before going live

## Testing

### PayPal Sandbox:
- Use PayPal sandbox accounts for testing
- Test both success and cancel scenarios

### Stripe Test Mode:
- Use test card numbers: `4242 4242 4242 4242`
- Use any future expiry date and any CVC
- Test various scenarios (success, decline, etc.)

## Troubleshooting

### PayPal Issues:
- Check that return/cancel URLs are correctly configured
- Verify PayPal app credentials are correct
- Check PayPal mode (sandbox vs live)

### Stripe Issues:
- Verify API keys are correct
- Check webhook endpoint is accessible
- Verify webhook secret is correct
- Check Stripe dashboard for error logs

## Production Checklist

- [ ] Update all URLs to production domain
- [ ] Switch PayPal to live mode
- [ ] Switch Stripe to live mode
- [ ] Set up webhook endpoint
- [ ] Test all payment flows
- [ ] Set up error monitoring
- [ ] Configure proper logging
- [ ] Review security settings

