"""
Payment Gateway Integration for PayPal, Stripe, and KHQR Bakong
"""
import stripe
import paypalrestsdk
import requests
from django.conf import settings
from django.utils import timezone
from .models import Payment, UserProfile

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Configure PayPal
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})


def create_paypal_payment(payment):
    """
    Create a PayPal payment and return approval URL
    """
    try:
        paypal_payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": settings.PAYPAL_RETURN_URL,
                "cancel_url": settings.PAYPAL_CANCEL_URL
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"Account Top-up - {payment.transaction_id}",
                        "sku": payment.transaction_id,
                        "price": str(payment.amount),
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(payment.amount),
                    "currency": "USD"
                },
                "description": f"Add funds to account - Transaction {payment.transaction_id}"
            }]
        })
        
        if paypal_payment.create():
            # Get approval URL
            for link in paypal_payment.links:
                if link.rel == "approval_url":
                    approval_url = link.href
                    payment.gateway_payment_id = paypal_payment.id
                    payment.gateway_response = {
                        'payment_id': paypal_payment.id,
                        'state': paypal_payment.state
                    }
                    payment.save()
                    return approval_url, None
        else:
            error_message = paypal_payment.error
            return None, error_message
            
    except Exception as e:
        return None, str(e)


def execute_paypal_payment(payment_id, payer_id):
    """
    Execute a PayPal payment after user approval
    """
    try:
        payment = Payment.objects.filter(gateway_payment_id=payment_id).first()
        if not payment:
            return False, None, "Payment not found"
        
        paypal_payment = paypalrestsdk.Payment.find(payment_id)
        
        if paypal_payment.execute({"payer_id": payer_id}):
            # Payment successful
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.gateway_response = {
                'payment_id': paypal_payment.id,
                'state': paypal_payment.state,
                'payer_id': payer_id,
                'transactions': paypal_payment.transactions
            }
            payment.save()
            
            # Add funds to user account
            payment.user.profile.balance += payment.amount
            payment.user.profile.save()
            
            return True, payment, None
        else:
            error_message = paypal_payment.error
            payment.status = 'failed'
            payment.gateway_response = {'error': error_message}
            payment.save()
            return False, payment, error_message
            
    except Payment.DoesNotExist:
        return False, None, "Payment not found"
    except Exception as e:
        return False, None, str(e)


def create_stripe_payment_intent(payment):
    """
    Create a Stripe Payment Intent
    """
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(payment.amount * 100),  # Convert to cents
            currency=settings.STRIPE_CURRENCY,
            metadata={
                'transaction_id': payment.transaction_id,
                'user_id': payment.user.id,
                'payment_id': payment.id
            },
            description=f"Account Top-up - {payment.transaction_id}",
        )
        
        payment.gateway_payment_id = intent.id
        payment.gateway_response = {
            'payment_intent_id': intent.id,
            'client_secret': intent.client_secret,
            'status': intent.status
        }
        payment.save()
        
        return intent.client_secret, None
        
    except Exception as e:
        return None, str(e)


def confirm_stripe_payment(payment_intent_id):
    """
    Confirm and process a Stripe payment
    """
    try:
        payment = Payment.objects.get(gateway_payment_id=payment_intent_id)
        
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status == 'succeeded':
            # Payment successful
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.gateway_response = {
                'payment_intent_id': intent.id,
                'status': intent.status,
                'charges': intent.charges.data[0].id if intent.charges.data else None
            }
            payment.save()
            
            # Add funds to user account
            payment.user.profile.balance += payment.amount
            payment.user.profile.save()
            
            return True, payment, None
        elif intent.status == 'canceled':
            payment.status = 'canceled'
            payment.save()
            return False, payment, "Payment was canceled"
        else:
            payment.status = 'failed'
            payment.gateway_response = {'status': intent.status}
            payment.save()
            return False, payment, f"Payment status: {intent.status}"
            
    except Payment.DoesNotExist:
        return False, None, "Payment not found"
    except Exception as e:
        return False, None, str(e)


def handle_stripe_webhook(event):
    """
    Handle Stripe webhook events
    """
    try:
        if event['type'] == 'payment_intent.succeeded':
            payment_intent_id = event['data']['object']['id']
            success, payment, error = confirm_stripe_payment(payment_intent_id)
            return success, payment, error
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent_id = event['data']['object']['id']
            try:
                payment = Payment.objects.get(gateway_payment_id=payment_intent_id)
                payment.status = 'failed'
                payment.gateway_response = {'webhook_event': event['type']}
                payment.save()
                return True, payment, None
            except Payment.DoesNotExist:
                return False, None, "Payment not found"
        else:
            return False, None, f"Unhandled event type: {event['type']}"
            
    except Exception as e:
        return False, None, str(e)


def _generate_khqr_string(merchant_id, amount, currency, transaction_id, description=None):
    """
    Generate KHQR QR code string based on EMV QR Code standard
    
    ⚠️ IMPORTANT: According to the API specification, the QR string MUST be generated by KHQR SDK.
    This is a TEMPORARY implementation that may not work with all banks.
    
    For production use, you MUST:
    1. Download the official KHQR SDK from: https://bakong.nbc.gov.kh/download/KHQR/integration/
    2. Install and use the official SDK to generate QR strings
    3. Replace this function with SDK-based generation
    
    The official SDK ensures compliance with KHQR specifications and bank compatibility.
    """
    
    def format_field(field_id, value):
        """Format EMV QR field: [ID][Length][Value]"""
        # Length is the byte length of the value (2 digits, zero-padded)
        length = len(value.encode('utf-8'))
        return f"{field_id:02d}{length:02d}{value}"
    
    def format_sub_field(sub_id, value):
        """Format sub-field within Merchant Account Information"""
        length = len(value.encode('utf-8'))
        return f"{sub_id:02d}{length:02d}{value}"
    
    # Currency code mapping
    currency_code = "840" if currency.upper() == "USD" else "116"  # KHR = 116
    
    # Format amount (2 decimal places)
    amount_str = f"{amount:.2f}"
    
    # Merchant name (use merchant_id or a readable name)
    merchant_name = merchant_id[:25]  # Max 25 characters for merchant name
    
    # Build Merchant Account Information (26)
    # Structure: 26[Length][00[Length][GUID][01-02[Length][Account Info]]]
    # For KHQR, merchant_id is typically the account identifier
    # GUID is usually required for KHQR - using merchant_id as placeholder
    guid = merchant_id  # In production, this should be a proper GUID
    account_info = merchant_id
    
    # Build Merchant Account Information sub-fields
    # Sub-field 00: GUID (Globally Unique Identifier)
    guid_field = format_sub_field(0, guid)
    # Sub-field 02: Account Information (merchant account)
    account_field = format_sub_field(2, account_info)
    
    # Combine sub-fields
    merchant_account_data = guid_field + account_field
    merchant_account_length = len(merchant_account_data.encode('utf-8'))
    merchant_account_info = f"26{merchant_account_length:02d}{merchant_account_data}"
    
    # Build Additional Data Field Template (62)
    # Sub-field 01: Bill Number (transaction reference)
    bill_number_field = format_sub_field(1, transaction_id)
    additional_data_content = bill_number_field
    additional_data_length = len(additional_data_content.encode('utf-8'))
    additional_data = f"62{additional_data_length:02d}{additional_data_content}"
    
    # Build the complete payload (without CRC)
    payload_parts = [
        format_field(0, "01"),  # Payload Format Indicator
        format_field(1, "12"),  # Point of Initiation Method (12 = static QR)
        merchant_account_info,  # Merchant Account Information (26)
        format_field(52, "0000"),  # Merchant Category Code
        format_field(53, currency_code),  # Transaction Currency
        format_field(54, amount_str),  # Transaction Amount
        format_field(58, "KH"),  # Country Code
        format_field(59, merchant_name),  # Merchant Name
        additional_data,  # Additional Data Field Template
    ]
    
    qr_payload = "".join(payload_parts)
    
    # Calculate CRC16-CCITT for EMV QR Code
    def calculate_crc16_ccitt(data):
        """
        Calculate CRC16-CCITT (polynomial 0x1021, initial value 0xFFFF)
        This is the standard CRC used in EMV QR Code
        """
        crc = 0xFFFF
        polynomial = 0x1021
        
        for byte in data.encode('utf-8'):
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ polynomial
                else:
                    crc <<= 1
                crc &= 0xFFFF
        
        return format(crc, '04X')
    
    # Calculate CRC for the payload (CRC field ID 63)
    # CRC is calculated on: payload + "6304" (without the CRC value itself)
    crc = calculate_crc16_ccitt(qr_payload + "6304")
    
    # Complete QR string: payload + CRC field (63) + CRC value
    # KHQR format includes "khqr://" prefix
    qr_string = f"khqr://{qr_payload}6304{crc}"
    
    return qr_string


def create_khqr_payment(payment):
    """
    Create a KHQR Bakong payment using NBC Bakong Open API
    Generates a deeplink from a KHQR QR code string
    Official API: https://api-bakong.nbc.gov.kh/
    API Endpoint: POST /v1/generate_deeplink_by_qr
    
    First tries to get QR string from API (if available), otherwise generates it manually.
    """
    try:
        # KHQR Bakong integration
        # Note: This requires KHQR API credentials configured in settings
        khqr_api_url = getattr(settings, 'KHQR_API_URL', 'https://api-bakong.nbc.gov.kh')
        khqr_merchant_id = getattr(settings, 'KHQR_MERCHANT_ID', '')
        khqr_api_key = getattr(settings, 'KHQR_API_KEY', '')
        khqr_callback_url = getattr(settings, 'KHQR_CALLBACK_URL', '')
        
        if not all([khqr_merchant_id, khqr_api_key]):
            return None, "KHQR payment gateway is not configured properly"
        
        # Try to get QR string from API first (if there's an endpoint for it)
        # Otherwise, generate it manually
        qr_string = None
        transaction_hash = None
        
        # Option 1: Try to get QR from API endpoint (if available)
        # Some APIs have an endpoint that generates the QR code
        try:
            generate_qr_payload = {
                'md5': khqr_merchant_id,
                'amount': float(payment.amount),
                'currency': 'USD',
                'info': f"VinFlow Top-up #{payment.transaction_id}",
                'bill_number': payment.transaction_id,
            }
            
            headers = {
                'Authorization': f'Bearer {khqr_api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Try the old endpoint format (if it exists)
            qr_response = requests.post(
                f"{khqr_api_url}/v1/generate_qr",  # This endpoint might not exist
                json=generate_qr_payload,
                headers=headers,
                timeout=10
            )
            
            if qr_response.status_code == 200:
                qr_data = qr_response.json()
                qr_string = qr_data.get('qr_string') or qr_data.get('qr')
                transaction_hash = qr_data.get('hash')
        except:
            # If API endpoint doesn't exist or fails, continue with manual generation
            pass
        
        # Option 2: Generate QR string manually if API didn't provide it
        if not qr_string:
            qr_string = _generate_khqr_string(
                merchant_id=khqr_merchant_id,
                amount=float(payment.amount),
                currency='USD',
                transaction_id=payment.transaction_id,
                description=f"VinFlow Top-up #{payment.transaction_id}"
            )
        
        # Build request payload according to API spec
        payload = {
            'qr': qr_string,
        }
        
        # Add sourceInfo if callback URL is configured
        if khqr_callback_url:
            # Get app info from settings or use defaults
            app_icon_url = getattr(settings, 'KHQR_APP_ICON_URL', 'https://bakong.nbc.gov.kh/images/logo.svg')
            app_name = getattr(settings, 'KHQR_APP_NAME', 'VinFlow')
            
            payload['sourceInfo'] = {
                'appIconUrl': app_icon_url,
                'appName': app_name,
                'appDeepLinkCallback': khqr_callback_url
            }
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Note: API spec doesn't mention Authorization header, but keeping it for compatibility
        # Remove if API doesn't require it
        if khqr_api_key:
            headers['Authorization'] = f'Bearer {khqr_api_key}'
        
        response = requests.post(
            f"{khqr_api_url}/v1/generate_deeplink_by_qr",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Handle new response structure according to API spec
            # Response format: { data: { shortLink: "..." }, errorCode, responseCode, responseMessage }
            if response_data.get('responseCode') == 0:
                data = response_data.get('data', {})
                short_link = data.get('shortLink', '')
                
                if not short_link:
                    return None, "No shortLink in API response"
                
                # Store the short link as deeplink
                # Also store the original QR string for QR code display
                payment.gateway_payment_id = payment.transaction_id  # Use transaction ID as reference
                payment.gateway_response = {
                    'qr_string': qr_string,  # Original QR string for display
                    'shortLink': short_link,  # Deeplink from API
                    'deeplink': short_link,  # Alias for compatibility
                    'response': response_data,
                    'merchant_id': khqr_merchant_id,
                    'amount': float(payment.amount),
                    'currency': 'USD',
                    'transaction_id': payment.transaction_id
                }
                payment.save()
                
                # Return data in format expected by template
                return {
                    'qr_string': qr_string,
                    'deeplink': short_link,
                    'shortLink': short_link,
                    'transaction_id': payment.transaction_id,
                    'amount': payment.amount
                }, None
            else:
                # API returned error
                error_message = response_data.get('responseMessage', 'KHQR payment creation failed')
                error_code = response_data.get('errorCode', 'UNKNOWN')
                return None, f"{error_message} (Error Code: {error_code})"
        else:
            try:
                error_data = response.json()
                # Handle both old and new error formats
                error_message = error_data.get('responseMessage') or error_data.get('message') or error_data.get('error', 'KHQR payment creation failed')
            except:
                error_message = f'KHQR payment creation failed with status {response.status_code}'
            return None, error_message
            
    except requests.exceptions.Timeout:
        return None, "KHQR API request timed out"
    except requests.exceptions.RequestException as e:
        return None, f"KHQR API request failed: {str(e)}"
    except Exception as e:
        return None, str(e)


def check_khqr_payment_status(payment):
    """
    Check KHQR Bakong payment status using NBC Bakong Open API
    Endpoint: POST /v1/check_transaction_by_hash
    Official API: https://api-bakong.nbc.gov.kh/
    """
    try:
        khqr_api_url = getattr(settings, 'KHQR_API_URL', 'https://api-bakong.nbc.gov.kh')
        khqr_api_key = getattr(settings, 'KHQR_API_KEY', '')
        
        # Get the transaction hash from gateway_payment_id
        transaction_hash = payment.gateway_payment_id
        
        if not transaction_hash:
            return False, None, "No transaction hash found"
        
        # Bakong API payload for checking transaction
        payload = {
            'hash': transaction_hash
        }
        
        headers = {
            'Authorization': f'Bearer {khqr_api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.post(
            f"{khqr_api_url}/v1/check_transaction_by_hash",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Check if transaction is found and paid
            # Bakong API returns transaction data if paid, or null/error if not found
            if response_data and isinstance(response_data, dict):
                # Check various possible status indicators
                is_paid = response_data.get('paid', False)
                transaction_status = response_data.get('status', '').lower()
                
                # If transaction exists and is paid
                if is_paid or transaction_status in ['completed', 'success', 'paid']:
                    payment.status = 'completed'
                    payment.completed_at = timezone.now()
                    payment.gateway_response.update({
                        'check_response': response_data,
                        'checked_at': timezone.now().isoformat()
                    })
                    payment.save()
                    
                    # Add funds to user account (only if not already added)
                    if payment.status != 'completed':  # Double-check to prevent duplicate credits
                        payment.user.profile.balance += payment.amount
                        payment.user.profile.save()
                    
                    return True, payment, None
                    
                elif transaction_status in ['failed', 'canceled', 'expired']:
                    payment.status = transaction_status
                    payment.gateway_response.update({
                        'check_response': response_data,
                        'checked_at': timezone.now().isoformat()
                    })
                    payment.save()
                    return False, payment, f"Payment {transaction_status}"
                else:
                    # Transaction exists but not yet paid (pending)
                    return False, payment, "Payment is still pending"
            else:
                # Transaction not found or not paid yet
                return False, payment, "Payment is still pending"
                
        elif response.status_code == 404:
            # Transaction not found yet (still pending)
            return False, payment, "Payment is still pending"
        else:
            try:
                error_data = response.json()
                error_message = error_data.get('message', error_data.get('error', 'Failed to check payment status'))
            except:
                error_message = f"Failed to check payment status (HTTP {response.status_code})"
            return False, None, error_message
            
    except requests.exceptions.Timeout:
        return False, None, "KHQR API request timed out"
    except requests.exceptions.RequestException as e:
        return False, None, f"KHQR API request failed: {str(e)}"
    except Exception as e:
        return False, None, str(e)

