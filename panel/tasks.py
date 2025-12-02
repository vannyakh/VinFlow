# panel/tasks.py
import requests
from celery import shared_task
from django.conf import settings
import logging
from .settings_utils import get_setting

logger = logging.getLogger(__name__)

@shared_task
def place_order_to_supplier(order_id):
    from .models import Order
    try:
        order = Order.objects.get(id=order_id)
        service = order.service
        
        # Determine supplier API endpoint and key from settings
        supplier_config = {
            'jap': {
                'url': get_setting('supplier_jap_url', 'https://justanotherpanel.com/api/v2'),
                'key': get_setting('supplier_jap_key', getattr(settings, 'JAP_API_KEY', '')),
            },
            'peakerr': {
                'url': get_setting('supplier_peakerr_url', 'https://peakerr.com/api/v2'),
                'key': get_setting('supplier_peakerr_key', getattr(settings, 'PEAKERR_API_KEY', '')),
            },
            'smmkings': {
                'url': get_setting('supplier_smmkings_url', 'https://smmkings.com/api/v2'),
                'key': get_setting('supplier_smmkings_key', getattr(settings, 'SMMKINGS_API_KEY', '')),
            },
        }
        
        config = supplier_config.get(service.supplier_api, supplier_config['jap'])
        
        # Build payload based on supplier
        payload = {
            'key': config['key'],
            'action': 'add',
            'service': service.external_service_id or service.id,
            'link': order.link,
            'quantity': order.quantity,
        }
        
        # Add drip-feed if enabled
        if order.drip_feed and order.drip_feed_quantity and order.drip_feed_days:
            payload['runs'] = order.drip_feed_days
            payload['interval'] = order.drip_feed_quantity
        
        # Get timeout and retry attempts from settings
        timeout = int(get_setting('supplier_timeout', '30'))
        retry_attempts = int(get_setting('supplier_retry_attempts', '3'))
        
        # Send request with retry logic
        response = None
        data = {}
        for attempt in range(retry_attempts):
            try:
                response = requests.post(config['url'], data=payload, timeout=timeout)
                data = response.json()
                
                if response.status_code == 200 and 'order' in data:
                    order.external_order_id = str(data.get('order', ''))
                    order.status = 'Processing'
                    order.supplier_response = data
                    order.save()
                    logger.info(f"Order {order.order_id} placed successfully with supplier")
                    return
                elif attempt < retry_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed for order {order.order_id}, retrying...")
                    continue
                else:
                    break
            except Exception as e:
                if attempt < retry_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed for order {order.order_id}: {str(e)}, retrying...")
                    continue
                else:
                    logger.error(f"All retry attempts failed for order {order.order_id}: {str(e)}")
                    data = {'error': str(e)}
                    break
        
        # If we get here, all attempts failed
        order.status = 'Canceled'
        order.supplier_response = data
        order.save()
        logger.error(f"Failed to place order {order.order_id} after {retry_attempts} attempts: {data}")
            
    except Exception as e:
        logger.error(f"Error placing order {order_id}: {str(e)}")
        try:
            order = Order.objects.get(id=order_id)
            order.status = 'Canceled'
            order.save()
        except:
            pass

@shared_task
def sync_order_status(order_id):
    """Sync order status from supplier"""
    from .models import Order
    try:
        order = Order.objects.get(id=order_id)
        if not order.external_order_id:
            return
        
        supplier_config = {
            'jap': {
                'url': get_setting('supplier_jap_url', 'https://justanotherpanel.com/api/v2'),
                'key': get_setting('supplier_jap_key', getattr(settings, 'JAP_API_KEY', '')),
            },
            'peakerr': {
                'url': get_setting('supplier_peakerr_url', 'https://peakerr.com/api/v2'),
                'key': get_setting('supplier_peakerr_key', getattr(settings, 'PEAKERR_API_KEY', '')),
            },
            'smmkings': {
                'url': get_setting('supplier_smmkings_url', 'https://smmkings.com/api/v2'),
                'key': get_setting('supplier_smmkings_key', getattr(settings, 'SMMKINGS_API_KEY', '')),
            },
        }
        
        config = supplier_config.get(order.service.supplier_api, supplier_config['jap'])
        
        payload = {
            'key': config['key'],
            'action': 'status',
            'order': order.external_order_id,
        }
        
        # Check if auto sync is enabled
        auto_sync = get_setting('auto_sync_order_status', 'true').lower() == 'true'
        if not auto_sync:
            logger.info(f"Auto sync is disabled, skipping order {order_id}")
            return
        
        # Get timeout from settings
        timeout = int(get_setting('supplier_timeout', '30'))
        
        response = requests.post(config['url'], data=payload, timeout=timeout)
        data = response.json()
        
        if response.status_code == 200:
            # Update order status based on supplier response
            status_map = {
                'Pending': 'Pending',
                'Processing': 'Processing',
                'In progress': 'In Progress',
                'Completed': 'Completed',
                'Partial': 'Partial',
                'Canceled': 'Canceled',
            }
            
            supplier_status = data.get('status', '').title()
            order.status = status_map.get(supplier_status, order.status)
            order.start_count = int(data.get('start_count', order.start_count))
            order.remains = int(data.get('remains', order.remains))
            order.supplier_response = data
            order.save()
            logger.info(f"Order {order.order_id} status synced: {order.status}")
            
    except Exception as e:
        logger.error(f"Error syncing order {order_id}: {str(e)}")

@shared_task
def process_subscription_delivery():
    """Process daily subscription deliveries"""
    from .models import UserSubscription
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    now = timezone.now()
    subscriptions = UserSubscription.objects.filter(
        is_active=True,
        next_delivery__lte=now
    )
    
    for subscription in subscriptions:
        # Create order for subscription
        from .models import Order
        order = Order.objects.create(
            user=subscription.user,
            service=subscription.package.service,
            link=subscription.link,
            quantity=subscription.package.quantity_per_day,
            charge=0.00,  # Already paid via subscription
        )
        
        place_order_to_supplier.delay(order.id)
        
        # Update next delivery
        subscription.last_delivery = now
        subscription.next_delivery = now + timedelta(days=1)
        subscription.save()