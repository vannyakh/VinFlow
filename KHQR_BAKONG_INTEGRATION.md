# KHQR Bakong Integration Guide

## Overview
This document provides detailed information about integrating the NBC (National Bank of Cambodia) Bakong KHQR payment system into VinFlow.

**Official API Documentation:** https://api-bakong.nbc.gov.kh/

## API Endpoints

### Base URL
```
https://api-bakong.nbc.gov.kh
```

### 1. Generate KHQR Payment
**Endpoint:** `POST /v1/generate_deeplink_by_qr`

**Purpose:** Generate a KHQR payment QR code and deeplink

**Request Headers:**
```json
{
  "Authorization": "Bearer YOUR_API_KEY",
  "Content-Type": "application/json",
  "Accept": "application/json"
}
```

**Request Body:**
```json
{
  "md5": "your_merchant_md5_hash",
  "amount": 10.50,
  "currency": "USD",
  "info": "Payment description",
  "bill_number": "TXN123456789"
}
```

**Response (Success - 200):**
```json
{
  "hash": "be06d47899294df86270319b292ed0917bd0fe920ead1dc2bdf3078cf6c50158",
  "qr_string": "khqr://00020101021230820016your_qr_data_here...",
  "deeplink": "bakong://qr?qr=khqr://...",
  "amount": 10.50,
  "currency": "USD",
  "merchant_id": "merchant_123",
  "bill_number": "TXN123456789"
}
```

**Key Response Fields:**
- `hash`: Transaction hash used for checking payment status
- `qr_string`: QR code data string to generate QR image
- `deeplink`: Deep link to open Bakong app directly
- `amount`: Payment amount
- `currency`: Currency code (USD, KHR)

### 2. Check Transaction Status
**Endpoint:** `POST /v1/check_transaction_by_hash`

**Purpose:** Check if a transaction has been paid

**Request Headers:**
```json
{
  "Authorization": "Bearer YOUR_API_KEY",
  "Content-Type": "application/json",
  "Accept": "application/json"
}
```

**Request Body:**
```json
{
  "hash": "be06d47899294df86270319b292ed0917bd0fe920ead1dc2bdf3078cf6c50158"
}
```

**Response (Paid - 200):**
```json
{
  "hash": "be06d47899294df86270319b292ed0917bd0fe920ead1dc2bdf3078cf6c50158",
  "paid": true,
  "status": "completed",
  "amount": 10.50,
  "currency": "USD",
  "paid_at": "2024-12-02T10:30:45Z",
  "transaction_id": "BAK123456789",
  "bill_number": "TXN123456789"
}
```

**Response (Not Paid - 404 or null):**
```json
null
```
or
```json
{
  "message": "Transaction not found",
  "error": "not_found"
}
```

## Configuration

### Django Settings
Add these to your `core/settings.py`:

```python
# KHQR Bakong Payment Gateway
KHQR_API_URL = os.environ.get('KHQR_API_URL', 'https://api-bakong.nbc.gov.kh')
KHQR_MERCHANT_ID = os.environ.get('KHQR_MERCHANT_ID', '')  # Your merchant MD5 hash
KHQR_API_KEY = os.environ.get('KHQR_API_KEY', '')  # Your API Bearer token
```

### Environment Variables
Create a `.env` file or set environment variables:

```bash
KHQR_API_URL=https://api-bakong.nbc.gov.kh
KHQR_MERCHANT_ID=your_merchant_md5_hash
KHQR_API_KEY=your_api_bearer_token
```

## Implementation Details

### Payment Flow

1. **User Initiates Payment**
   - User selects KHQR Bakong payment method
   - User enters payment amount
   - System validates amount against min/max limits

2. **Generate KHQR Payment**
   - System calls `create_khqr_payment(payment)`
   - Sends request to `/v1/generate_deeplink_by_qr`
   - Receives QR string, deeplink, and transaction hash
   - Stores hash in `payment.gateway_payment_id`

3. **Display Payment Page**
   - Shows QR code generated from `qr_string`
   - Shows "Pay with Bakong App" button with deeplink
   - Auto-checks payment status every 5 seconds

4. **Check Payment Status**
   - System calls `check_khqr_payment_status(payment)`
   - Sends request to `/v1/check_transaction_by_hash`
   - Checks if transaction is paid
   - Updates payment status and adds funds if paid

5. **Payment Completion**
   - Marks payment as completed
   - Adds funds to user balance
   - Redirects user to dashboard

### QR Code Generation

The template uses QRCode.js library to generate QR code from the `qr_string`:

```javascript
new QRCode(document.getElementById("qrcode"), {
    text: "khqr://00020101021230820016...",
    width: 256,
    height: 256,
    colorDark: "#000000",
    colorLight: "#ffffff",
    correctLevel: QRCode.CorrectLevel.H
});
```

### Mobile Deeplink

For mobile users, a direct link opens the Bakong app:

```html
<a href="bakong://qr?qr=khqr://...">Pay with Bakong App</a>
```

## Testing

### Test Scenarios

1. **Successful Payment**
   - Generate KHQR payment
   - Scan QR code with Bakong app
   - Complete payment
   - Verify funds added to account

2. **Payment Timeout**
   - Generate KHQR payment
   - Wait without paying
   - Verify payment remains pending

3. **Payment Cancellation**
   - Generate KHQR payment
   - User closes page
   - Payment remains pending in database

### Test Data

Use Bakong sandbox/test environment for testing:
- Test merchant credentials
- Test amounts (e.g., $0.01, $1.00, $10.00)
- Test QR code scanning

## Error Handling

### Common Errors

1. **Configuration Error**
   ```
   "KHQR payment gateway is not configured properly"
   ```
   - Solution: Check KHQR_MERCHANT_ID and KHQR_API_KEY are set

2. **API Timeout**
   ```
   "KHQR API request timed out"
   ```
   - Solution: Check network connectivity, increase timeout

3. **Invalid Credentials**
   ```
   "Unauthorized" (HTTP 401)
   ```
   - Solution: Verify API key and merchant ID are correct

4. **Transaction Not Found**
   ```
   "Transaction not found" (HTTP 404)
   ```
   - Normal: Transaction not paid yet (still pending)

## Security Considerations

1. **API Key Protection**
   - Store API key in environment variables
   - Never commit API keys to version control
   - Use `.env` file for local development

2. **Transaction Hash**
   - Transaction hash is stored in `payment.gateway_payment_id`
   - Hash is used to check payment status
   - Hash is unique per transaction

3. **Payment Verification**
   - Always verify payment status before adding funds
   - Check for duplicate payments
   - Log all payment transactions

4. **Data Storage**
   - Store complete API responses in `payment.gateway_response`
   - Useful for debugging and reconciliation
   - Contains payment proof

## Monitoring

### Key Metrics to Monitor

1. **Payment Success Rate**
   - Track completed vs. pending payments
   - Monitor failed payment reasons

2. **API Response Times**
   - Monitor `/v1/generate_deeplink_by_qr` response time
   - Monitor `/v1/check_transaction_by_hash` response time

3. **Payment Verification Frequency**
   - Track how many status checks per payment
   - Optimize polling interval if needed

### Logging

All KHQR payment operations are logged:
- Payment creation requests
- Payment status checks
- Payment completions
- Errors and exceptions

## Troubleshooting

### QR Code Not Displaying
- Check if `qr_string` is in response
- Verify QRCode.js library is loaded
- Check browser console for errors

### Payment Status Not Updating
- Check if transaction hash is stored correctly
- Verify API key is valid
- Check network connectivity
- Review server logs for errors

### Funds Not Added
- Check if payment status is "completed"
- Verify balance update logic
- Check for duplicate payment prevention

## Admin Features

### Enable/Disable KHQR
Navigate to **Admin Dashboard → Settings → Payment**:
- Find "Enable KHQR Bakong" setting
- Toggle to enable/disable
- Users will see/hide KHQR payment option

### View KHQR Transactions
Navigate to **Admin Dashboard → Transactions**:
- Filter by payment method: KHQR
- View transaction details
- Check payment status
- View gateway responses

## Support

### Resources
- NBC Bakong API Documentation: https://api-bakong.nbc.gov.kh/
- NBC Bakong Support: Contact your account manager
- Technical Issues: Check server logs and error messages

### Contact
For technical support or questions about KHQR integration:
- Review this documentation
- Check error logs
- Contact NBC Bakong support for API issues
- Contact VinFlow technical team for integration issues

