"""
Payment Gateway Integration for PayPal, Stripe, and KHQR Bakong
"""
import stripe
import paypalrestsdk
import requests
from django.conf import settings
from django.utils import timezone
from .models import Payment, UserProfile
from bakong_khqr import KHQR


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
        
        khqr = KHQR(khqr_api_key)
        qr_string = None
        
        try:
            qr_string = khqr.create_qr(
                bank_account=khqr_merchant_id,  # Should be 'user_name@bank' from Bakong profile
                merchant_name=getattr(settings, 'KHQR_MERCHANT_NAME', 'VinFlow'),
                merchant_city=getattr(settings, 'KHQR_MERCHANT_CITY', 'Phnom Penh'),
                amount=float(payment.amount),
                currency='USD',  # Use 'USD' or 'KHR' as needed
                store_label=getattr(settings, 'KHQR_STORE_LABEL', 'VinFlow'),
                phone_number=getattr(settings, 'KHQR_PHONE_NUMBER', ''),  # Optional: can set to merchant/customer phone
                bill_number=payment.transaction_id,
                terminal_label=getattr(settings, 'KHQR_TERMINAL_LABEL', 'Cashier-01'),
                static=False  # Use dynamic QR by default
            )
            
        except Exception as e:
            return None, f"Failed to create KHQR: {str(e)}"
        
        if not qr_string:
            return None, "Failed to generate QR string"
        
        # Generate MD5 hash for transaction tracking
        md5_hash = khqr.generate_md5(qr_string)
        
        # Generate deeplink
        deeplink = None
        if khqr_callback_url:
            # Get app info from settings or use defaults
            app_icon_url = getattr(settings, 'KHQR_APP_ICON_URL', 'https://bakong.nbc.gov.kh/images/logo.svg')
            app_name = getattr(settings, 'KHQR_APP_NAME', 'VinFlow')
            
            deeplink = khqr.generate_deeplink(
                qr_string,
                callback=khqr_callback_url,
                appIconUrl=app_icon_url,
                appName=app_name
            )
        
        # Store MD5 hash as gateway_payment_id for transaction tracking
        payment.gateway_payment_id = md5_hash
        payment.gateway_response = {
            'qr_string': qr_string,
            'md5_hash': md5_hash,
            'deeplink': deeplink,
            'merchant_id': khqr_merchant_id,
            'amount': float(payment.amount),
            'currency': 'USD',
            'transaction_id': payment.transaction_id
        }
        payment.save()
        
        # Return data in format expected by template
        return {
            'qr_string': qr_string,
            'md5_hash': md5_hash,
            'deeplink': deeplink,
            'transaction_id': payment.transaction_id,
            'amount': payment.amount
        }, None
            
    except requests.exceptions.Timeout:
        return None, "KHQR API request timed out"
    except requests.exceptions.RequestException as e:
        return None, f"KHQR API request failed: {str(e)}"
    except Exception as e:
        return None, str(e)


def check_khqr_payment_status(payment):
    """
    Check KHQR Bakong payment status using KHQR library
    Uses MD5 hash to check payment status
    """
    try:
        khqr_api_key = getattr(settings, 'KHQR_API_KEY', '')
        
        if not khqr_api_key:
            return False, None, "KHQR API key not configured"
        
        # Get the MD5 hash from gateway_payment_id
        md5_hash = payment.gateway_payment_id
        
        if not md5_hash:
            return False, None, "No MD5 hash found for payment"
        
        # Initialize KHQR
        khqr = KHQR(khqr_api_key)
        
        # Check payment status
        payment_status = khqr.check_payment(md5_hash)
        
        if payment_status == "PAID":
            # Payment is successful
            # Get payment details for additional information
            try:
                payment_info = khqr.get_payment(md5_hash)
            except:
                payment_info = None
            
            # Update payment status
            old_status = payment.status
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            
            # Update gateway response with check results
            if payment.gateway_response:
                payment.gateway_response.update({
                    'payment_status': payment_status,
                    'payment_info': payment_info,
                    'checked_at': timezone.now().isoformat()
                })
            else:
                payment.gateway_response = {
                    'payment_status': payment_status,
                    'payment_info': payment_info,
                    'checked_at': timezone.now().isoformat()
                }
            payment.save()
            
            # Add funds to user account (only if not already completed)
            if old_status != 'completed':
                payment.user.profile.balance += payment.amount
                payment.user.profile.save()
            
            return True, payment, None
            
        elif payment_status == "UNPAID":
            # Payment is still pending
            return False, payment, "Payment is still pending"
            
        else:
            # Unknown status or error
            return False, payment, f"Payment status: {payment_status}"
            
    except Exception as e:
        return False, None, str(e)

