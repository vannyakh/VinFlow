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

@shared_task
def sync_services_from_supplier(supplier='jap'):
    """Sync services from supplier API (JAP, Peakerr, etc.) - Celery task version"""
    from .models import Service, ServiceCategory
    from decimal import Decimal, InvalidOperation
    
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
    
    config = supplier_config.get(supplier)
    if not config or not config['key']:
        logger.error(f'{supplier.upper()} API key not configured')
        return {'status': 'error', 'message': f'{supplier.upper()} API key not configured'}
    
    try:
        # Fetch services from supplier API
        payload = {
            'key': config['key'],
            'action': 'services',
        }
        
        timeout = int(get_setting('supplier_timeout', '30'))
        response = requests.post(config['url'], data=payload, timeout=timeout)
        
        if response.status_code != 200:
            error_msg = f'Failed to fetch services from {supplier.upper()}: HTTP {response.status_code}'
            logger.error(error_msg)
            return {'status': 'error', 'message': error_msg}
        
        data = response.json()
        
        # Handle different response formats
        if isinstance(data, dict):
            if 'error' in data:
                error_msg = f'API Error: {data.get("error", "Unknown error")}'
                logger.error(error_msg)
                return {'status': 'error', 'message': error_msg}
            # Some APIs return services in a 'data' or 'services' key
            services_data = data.get('data', data.get('services', []))
        elif isinstance(data, list):
            services_data = data
        else:
            error_msg = f'Unexpected response format from {supplier.upper()} API'
            logger.error(error_msg)
            return {'status': 'error', 'message': error_msg}
        
        if not services_data:
            logger.warning(f'No services found from {supplier.upper()} API')
            return {'status': 'warning', 'message': f'No services found from {supplier.upper()} API', 'synced': 0, 'created': 0, 'updated': 0}
        
        # Category mapping from supplier categories to local categories
        category_mapping = {
            'Instagram': 'ig',
            'Facebook': 'fb',
            'TikTok': 'tt',
            'YouTube': 'yt',
            'Twitter': 'tw',
            'Shopee': 'sh',
            'Telegram': 'tg',
        }
        
        synced_count = 0
        updated_count = 0
        created_count = 0
        error_count = 0
        
        for service_data in services_data:
            try:
                # Extract service information (handle different API formats)
                service_id_raw = service_data.get('service') or service_data.get('id')
                if service_id_raw is None:
                    continue
                service_id = str(service_id_raw)
                
                name = service_data.get('name', service_data.get('service', 'Unknown Service'))
                if not name or name == 'Unknown Service':
                    name = str(service_data.get('service', 'Unknown Service'))
                
                category_name = service_data.get('category', service_data.get('type', 'Other'))
                rate_str = service_data.get('rate', service_data.get('price', '0'))
                min_order = int(service_data.get('min', service_data.get('min_order', 1)))
                max_order = int(service_data.get('max', service_data.get('max_order', 100000)))
                description = service_data.get('description', service_data.get('desc', ''))
                
                # Convert rate to Decimal (handle per 1000 pricing)
                try:
                    rate = Decimal(str(rate_str))
                except (InvalidOperation, ValueError):
                    rate = Decimal('0')
                
                # Map category
                service_type = category_mapping.get(category_name, 'other')
                
                # Get or create category
                category, _ = ServiceCategory.objects.get_or_create(
                    name=category_name,
                    defaults={'is_active': True, 'order': 0}
                )
                
                # Try to find existing service by external_service_id first
                try:
                    service = Service.objects.get(external_service_id=service_id, supplier_api=supplier)
                    created = False
                except Service.DoesNotExist:
                    # If not found, try to find by name and supplier
                    try:
                        service = Service.objects.get(name=name, supplier_api=supplier)
                        service.external_service_id = service_id
                        created = False
                    except Service.DoesNotExist:
                        # Create new service
                        service = Service(
                            external_service_id=service_id,
                            supplier_api=supplier,
                            name=name,
                            category=category,
                            service_type=service_type,
                            rate=rate,
                            min_order=min_order,
                            max_order=max_order,
                            description=description,
                            is_active=True,
                        )
                        created = True
                
                if not created:
                    # Update existing service
                    service.name = name
                    service.category = category
                    service.service_type = service_type
                    service.rate = rate
                    service.min_order = min_order
                    service.max_order = max_order
                    service.description = description
                    service.supplier_api = supplier
                    service.external_service_id = service_id
                    service.save()
                    updated_count += 1
                else:
                    service.save()
                    created_count += 1
                
                synced_count += 1
                
            except Exception as e:
                error_count += 1
                logger.error(f'Error syncing service {service_data}: {str(e)}')
                continue
        
        result = {
            'status': 'success',
            'message': f'Successfully synced {synced_count} services from {supplier.upper()}',
            'synced': synced_count,
            'created': created_count,
            'updated': updated_count,
            'errors': error_count
        }
        logger.info(f"Service sync completed: {result['message']} ({created_count} created, {updated_count} updated, {error_count} errors)")
        return result
        
    except requests.exceptions.RequestException as e:
        error_msg = f'Network error connecting to {supplier.upper()} API: {str(e)}'
        logger.error(error_msg)
        return {'status': 'error', 'message': error_msg}
    except Exception as e:
        error_msg = f'Error syncing services: {str(e)}'
        logger.exception(error_msg)
        return {'status': 'error', 'message': error_msg}