"""
Payment Gateway Integration for PayPal and Stripe
"""
import stripe
import paypalrestsdk
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

