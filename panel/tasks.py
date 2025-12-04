# panel/tasks.py
import requests
from celery import shared_task
from django.conf import settings
import logging
from .settings_utils import get_setting

logger = logging.getLogger(__name__)

# Helper to create order logs without circular imports
def create_log(order, log_type, message, details=None, old_value=None, new_value=None):
    """Create order log entry - helper function for tasks"""
    from .models import OrderLog
    try:
        return OrderLog.objects.create(
            order=order,
            log_type=log_type,
            message=message,
            details=details or {},
            old_value=old_value or '',
            new_value=new_value or '',
        )
    except Exception as e:
        logger.error(f"Failed to create order log: {str(e)}")
        return None

def execute_task_async_or_sync(task_func, *args, **kwargs):
    """
    Execute a Celery task asynchronously if Celery/Redis is available,
    otherwise execute it synchronously as a fallback.
    
    Args:
        task_func: The Celery task function
        *args: Positional arguments for the task
        **kwargs: Keyword arguments for the task
    
    Returns:
        The task result (AsyncResult if async, direct result if sync)
    """
    try:
        # Try to execute asynchronously
        return task_func.delay(*args, **kwargs)
    except (ConnectionError, OSError, IOError) as e:
        # If Celery/Redis is not available (connection refused, etc.), run synchronously
        error_code = getattr(e, 'errno', None)
        if error_code == 61 or 'Connection refused' in str(e) or 'Connection refused' in str(e.args):
            logger.warning(
                f"Celery broker unavailable (Connection refused). "
                f"Running task {task_func.__name__} synchronously."
            )
        else:
            logger.warning(
                f"Celery broker unavailable ({str(e)}). "
                f"Running task {task_func.__name__} synchronously."
            )
        # Execute the task function directly (not as a Celery task)
        return task_func(*args, **kwargs)
    except Exception as e:
        # Catch any other Celery-related errors and fall back to synchronous execution
        logger.warning(
            f"Celery task execution failed ({str(e)}). "
            f"Running task {task_func.__name__} synchronously."
        )
        # Execute the task function directly (not as a Celery task)
        return task_func(*args, **kwargs)

@shared_task
def place_order_to_supplier(order_id):
    from .models import Order, OrderLog
    
    try:
        order = Order.objects.get(id=order_id)
        service = order.service
        
        # JAP API configuration
        jap_url = get_setting('supplier_jap_url', 'https://justanotherpanel.com/api/v2')
        jap_key = get_setting('supplier_jap_key', getattr(settings, 'JAP_API_KEY', ''))
        
        # Build payload for JAP API
        payload = {
            'key': jap_key,
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
        
        # Log API call details
        create_log(
            order=order,
            log_type='api_call',
            message=f'Sending order to supplier API (Attempt 1/{retry_attempts})',
            details={
                'api_url': jap_url,
                'service_external_id': service.external_service_id,
                'quantity': order.quantity,
                'drip_feed': order.drip_feed,
                'timeout': timeout,
                'max_retries': retry_attempts,
            }
        )
        
        # Send request with retry logic
        response = None
        data = {}
        for attempt in range(retry_attempts):
            try:
                response = requests.post(jap_url, data=payload, timeout=timeout)
                data = response.json()
                
                # Log API response
                create_log(
                    order=order,
                    log_type='api_response',
                    message=f'Received response from supplier (Attempt {attempt + 1}/{retry_attempts})',
                    details={
                        'status_code': response.status_code,
                        'response_data': data,
                        'attempt': attempt + 1,
                    }
                )
                
                if response.status_code == 200 and 'order' in data:
                    old_status = order.status
                    order.external_order_id = str(data.get('order', ''))
                    order.status = 'Processing'
                    order.supplier_response = data
                    order.save()
                    
                    # Log successful order placement
                    create_log(
                        order=order,
                        log_type='status_change',
                        message='Order successfully placed with supplier',
                        details={
                            'external_order_id': order.external_order_id,
                            'supplier_response': data,
                        },
                        old_value=old_status,
                        new_value='Processing'
                    )
                    
                    logger.info(f"Order {order.order_id} placed successfully with supplier")
                    return
                elif attempt < retry_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed for order {order.order_id}, retrying...")
                    
                    # Log retry
                    create_log(
                        order=order,
                        log_type='system',
                        message=f'Retry attempt {attempt + 2}/{retry_attempts}',
                        details={
                            'reason': 'Previous attempt failed',
                            'response': data,
                        }
                    )
                    continue
                else:
                    break
            except Exception as e:
                # Log API error
                create_log(
                    order=order,
                    log_type='error',
                    message=f'API call failed (Attempt {attempt + 1}/{retry_attempts}): {str(e)}',
                    details={
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'attempt': attempt + 1,
                    }
                )
                
                if attempt < retry_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed for order {order.order_id}: {str(e)}, retrying...")
                    continue
                else:
                    logger.error(f"All retry attempts failed for order {order.order_id}: {str(e)}")
                    data = {'error': str(e)}
                    break
        
        # If we get here, all attempts failed
        old_status = order.status
        order.status = 'Canceled'
        order.supplier_response = data
        order.save()
        
        # Log order cancellation
        create_log(
            order=order,
            log_type='status_change',
            message=f'Order canceled after {retry_attempts} failed attempts',
            details={
                'reason': 'All API attempts failed',
                'last_error': data,
            },
            old_value=old_status,
            new_value='Canceled'
        )
        
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
    """Sync order status from JAP API"""
    from .models import Order
    
    try:
        order = Order.objects.get(id=order_id)
        if not order.external_order_id:
            return
        
        # JAP API configuration
        jap_url = get_setting('supplier_jap_url', 'https://justanotherpanel.com/api/v2')
        jap_key = get_setting('supplier_jap_key', getattr(settings, 'JAP_API_KEY', ''))
        
        payload = {
            'key': jap_key,
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
        
        response = requests.post(jap_url, data=payload, timeout=timeout)
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
            old_status = order.status
            old_start_count = order.start_count
            old_remains = order.remains
            
            order.status = status_map.get(supplier_status, order.status)
            order.start_count = int(data.get('start_count', order.start_count))
            order.remains = int(data.get('remains', order.remains))
            order.supplier_response = data
            order.save()
            
            # Log status sync
            status_changed = old_status != order.status
            counts_changed = (old_start_count != order.start_count or old_remains != order.remains)
            
            if status_changed or counts_changed:
                create_log(
                    order=order,
                    log_type='status_change' if status_changed else 'system',
                    message=f'Status synced from supplier: {order.status}',
                    details={
                        'supplier_status': supplier_status,
                        'start_count': order.start_count,
                        'remains': order.remains,
                        'supplier_data': data,
                        'changes': {
                            'status_changed': status_changed,
                            'start_count_changed': old_start_count != order.start_count,
                            'remains_changed': old_remains != order.remains,
                        }
                    },
                    old_value=old_status,
                    new_value=order.status
                )
            
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
        
        execute_task_async_or_sync(place_order_to_supplier, order.id)
        
        # Update next delivery
        subscription.last_delivery = now
        subscription.next_delivery = now + timedelta(days=1)
        subscription.save()

@shared_task
def sync_services_from_supplier():
    """Sync services from JAP API - Celery task version"""
    from .models import Service, ServiceCategory
    from decimal import Decimal, InvalidOperation
    
    # JAP API configuration
    jap_url = get_setting('supplier_jap_url', 'https://justanotherpanel.com/api/v2')
    jap_key = get_setting('supplier_jap_key', getattr(settings, 'JAP_API_KEY', ''))
    
    if not jap_key:
        logger.error('JAP API key not configured')
        return {'status': 'error', 'message': 'JAP API key not configured'}
    
    try:
        # Fetch services from JAP API
        payload = {
            'key': jap_key,
            'action': 'services',
        }
        
        timeout = int(get_setting('supplier_timeout', '30'))
        response = requests.post(jap_url, data=payload, timeout=timeout)
        
        if response.status_code != 200:
            error_msg = f'Failed to fetch services from JAP API: HTTP {response.status_code}'
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
            error_msg = f'Unexpected response format from JAP API'
            logger.error(error_msg)
            return {'status': 'error', 'message': error_msg}
        
        if not services_data:
            logger.warning(f'No services found from JAP API')
            return {'status': 'warning', 'message': f'No services found from JAP API', 'synced': 0, 'created': 0, 'updated': 0}
        
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
                    service = Service.objects.get(external_service_id=service_id, supplier_api='jap')
                    created = False
                except Service.DoesNotExist:
                    # If not found, try to find by name and supplier
                    try:
                        service = Service.objects.get(name=name, supplier_api='jap')
                        service.external_service_id = service_id
                        created = False
                    except Service.DoesNotExist:
                        # Create new service
                        service = Service(
                            external_service_id=service_id,
                            supplier_api='jap',
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
                    service.supplier_api = 'jap'
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
            'message': f'Successfully synced {synced_count} services from JAP API',
            'synced': synced_count,
            'created': created_count,
            'updated': updated_count,
            'errors': error_count
        }
        logger.info(f"Service sync completed: {result['message']} ({created_count} created, {updated_count} updated, {error_count} errors)")
        return result
        
    except requests.exceptions.RequestException as e:
        error_msg = f'Network error connecting to JAP API: {str(e)}'
        logger.error(error_msg)
        return {'status': 'error', 'message': error_msg}
    except Exception as e:
        error_msg = f'Error syncing services: {str(e)}'
        logger.exception(error_msg)
        return {'status': 'error', 'message': error_msg}


# ============================================
# Marketing Promotion Automation Tasks
# ============================================

@shared_task
def check_and_expire_promotions():
    """
    Check for promotions that have ended and automatically expire them
    Runs periodically (e.g., every hour)
    """
    from django.utils import timezone
    from .models import MarketingPromotion, Notification
    
    logger.info('Starting promotion expiration check...')
    
    try:
        now = timezone.now()
        
        # Find promotions that should be expired
        expired_promotions = MarketingPromotion.objects.filter(
            is_active=True,
            auto_expire=True,
            end_date__lt=now,
            status='active'
        )
        
        expired_count = 0
        for promotion in expired_promotions:
            promotion.status = 'completed'
            promotion.is_active = False
            promotion.save()
            expired_count += 1
            
            # Notify admin
            try:
                Notification.objects.create(
                    user=promotion.created_by,
                    notification_type='system',
                    title='Promotion Expired',
                    message=f'Promotion "{promotion.title}" ({promotion.promotion_id}) has expired and been completed.',
                )
            except:
                pass
            
            logger.info(f'Expired promotion: {promotion.promotion_id} - {promotion.title}')
        
        # Auto-activate scheduled promotions
        scheduled_promotions = MarketingPromotion.objects.filter(
            is_active=True,
            status='scheduled',
            start_date__lte=now,
            end_date__gte=now
        )
        
        activated_count = 0
        for promotion in scheduled_promotions:
            promotion.status = 'active'
            promotion.save()
            activated_count += 1
            
            # Notify admin
            try:
                Notification.objects.create(
                    user=promotion.created_by,
                    notification_type='system',
                    title='Promotion Activated',
                    message=f'Promotion "{promotion.title}" ({promotion.promotion_id}) is now active.',
                )
            except:
                pass
            
            logger.info(f'Activated promotion: {promotion.promotion_id} - {promotion.title}')
        
        result = {
            'status': 'success',
            'message': f'Expired {expired_count} promotions, activated {activated_count} promotions',
            'expired': expired_count,
            'activated': activated_count
        }
        logger.info(f"Promotion check completed: {result['message']}")
        return result
        
    except Exception as e:
        error_msg = f'Error checking promotions: {str(e)}'
        logger.exception(error_msg)
        return {'status': 'error', 'message': error_msg}


@shared_task
def send_promotional_notifications():
    """
    Send notifications about active promotions to targeted users
    Runs periodically (e.g., daily)
    """
    from django.utils import timezone
    from django.contrib.auth.models import User
    from .models import MarketingPromotion, Notification
    from datetime import timedelta
    
    logger.info('Starting promotional notifications...')
    
    try:
        # Check if promotional emails are enabled
        promotional_enabled = get_setting('promotional_email_enabled', True)
        if not promotional_enabled:
            logger.info('Promotional notifications are disabled')
            return {'status': 'skipped', 'message': 'Promotional notifications disabled'}
        
        now = timezone.now()
        notification_count = 0
        
        # Get active flash sales
        flash_sales = MarketingPromotion.objects.filter(
            is_active=True,
            status='active',
            promotion_type='flash_sale',
            start_date__lte=now,
            end_date__gte=now
        )
        
        flash_sale_notifications = get_setting('flash_sale_notification', True)
        
        for promotion in flash_sales:
            # Check if we've already sent notifications for this promotion
            # (To avoid spamming, we only send once when it becomes active)
            
            # Determine target users
            target_users = []
            
            if promotion.target_audience == 'all':
                target_users = User.objects.filter(is_active=True)
            elif promotion.target_audience == 'new_users':
                seven_days_ago = now - timedelta(days=7)
                target_users = User.objects.filter(
                    is_active=True, 
                    date_joined__gte=seven_days_ago
                )
            elif promotion.target_audience == 'active_users':
                target_users = User.objects.filter(
                    is_active=True, 
                    profile__total_spent__gt=0
                )
            elif promotion.target_audience == 'inactive_users':
                target_users = User.objects.filter(
                    is_active=True, 
                    profile__total_spent=0
                )
            elif promotion.target_audience == 'high_spenders':
                target_users = User.objects.filter(
                    is_active=True, 
                    profile__total_spent__gte=100
                )
            elif promotion.target_audience == 'resellers':
                target_users = User.objects.filter(
                    is_active=True, 
                    profile__is_reseller=True
                )
            elif promotion.target_audience == 'specific_users':
                target_users = promotion.specific_users.filter(is_active=True)
            
            # Send notifications to target users
            if flash_sale_notifications:
                for user in target_users[:100]:  # Limit to 100 users per batch
                    try:
                        # Check if user already has notification about this promotion
                        existing = Notification.objects.filter(
                            user=user,
                            notification_type='system',
                            title__icontains=promotion.promotion_id
                        ).exists()
                        
                        if not existing:
                            Notification.objects.create(
                                user=user,
                                notification_type='system',
                                title=f'🎉 {promotion.title}',
                                message=promotion.description or f'Check out our special promotion!',
                                link=promotion.cta_link or '/'
                            )
                            notification_count += 1
                    except Exception as e:
                        logger.error(f'Error sending notification to user {user.id}: {str(e)}')
                        continue
            
            logger.info(f'Sent {notification_count} notifications for promotion: {promotion.promotion_id}')
        
        result = {
            'status': 'success',
            'message': f'Sent {notification_count} promotional notifications',
            'count': notification_count
        }
        logger.info(f"Promotional notifications completed: {result['message']}")
        return result
        
    except Exception as e:
        error_msg = f'Error sending promotional notifications: {str(e)}'
        logger.exception(error_msg)
        return {'status': 'error', 'message': error_msg}


@shared_task
def apply_welcome_bonus_for_new_users():
    """
    Apply welcome bonus to newly registered users if enabled
    Runs periodically (e.g., every 10 minutes)
    """
    from django.utils import timezone
    from django.contrib.auth.models import User
    from .models import UserProfile, Payment, Notification
    from datetime import timedelta
    from decimal import Decimal
    
    logger.info('Starting welcome bonus application...')
    
    try:
        # Get welcome bonus amount from settings
        welcome_bonus = Decimal(get_setting('new_user_welcome_bonus', '0.00'))
        
        if welcome_bonus <= 0:
            logger.info('Welcome bonus is not enabled or is 0')
            return {'status': 'skipped', 'message': 'Welcome bonus disabled or 0'}
        
        # Find users registered in the last 24 hours who haven't received the bonus
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        
        new_users = User.objects.filter(
            is_active=True,
            date_joined__gte=twenty_four_hours_ago
        )
        
        bonus_count = 0
        for user in new_users:
            try:
                profile = user.profile
                
                # Check if user already received welcome bonus
                # (Check for payment record with 'welcome_bonus' in gateway_payment_id)
                existing_bonus = Payment.objects.filter(
                    user=user,
                    gateway_payment_id__icontains='welcome_bonus'
                ).exists()
                
                if existing_bonus:
                    continue
                
                # Check if user hasn't made any deposits yet (truly new)
                has_deposits = Payment.objects.filter(
                    user=user,
                    status='completed'
                ).exists()
                
                if has_deposits:
                    continue  # Don't give bonus if they already deposited
                
                # Apply welcome bonus
                profile.balance += welcome_bonus
                profile.save()
                
                # Create payment record for tracking
                Payment.objects.create(
                    transaction_id=f'BONUS_{user.id}_{timezone.now().strftime("%Y%m%d%H%M%S")}',
                    user=user,
                    amount=welcome_bonus,
                    method='khqr',  # Arbitrary method for tracking
                    status='completed',
                    gateway_payment_id=f'welcome_bonus_{user.id}',
                    completed_at=timezone.now()
                )
                
                # Send notification
                Notification.objects.create(
                    user=user,
                    notification_type='payment',
                    title='Welcome Bonus!',
                    message=f'Welcome to VinFlow! You have received ${welcome_bonus} as a welcome bonus. Start ordering now!',
                    link='/services/'
                )
                
                bonus_count += 1
                logger.info(f'Applied ${welcome_bonus} welcome bonus to user: {user.username}')
                
            except Exception as e:
                logger.error(f'Error applying welcome bonus to user {user.id}: {str(e)}')
                continue
        
        result = {
            'status': 'success',
            'message': f'Applied welcome bonus to {bonus_count} new users',
            'count': bonus_count,
            'amount': float(welcome_bonus)
        }
        logger.info(f"Welcome bonus application completed: {result['message']}")
        return result
        
    except Exception as e:
        error_msg = f'Error applying welcome bonus: {str(e)}'
        logger.exception(error_msg)
        return {'status': 'error', 'message': error_msg}


@shared_task
def generate_promotion_report():
    """
    Generate a summary report of all active promotions and their performance
    Runs periodically (e.g., weekly)
    """
    from django.utils import timezone
    from .models import MarketingPromotion, Notification, User
    from datetime import timedelta
    
    logger.info('Generating promotion performance report...')
    
    try:
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # Get all promotions from the last 30 days
        recent_promotions = MarketingPromotion.objects.filter(
            created_at__gte=thirty_days_ago
        ).order_by('-views_count')
        
        if not recent_promotions:
            return {'status': 'success', 'message': 'No promotions in the last 30 days'}
        
        # Generate report
        report_lines = [
            'PROMOTION PERFORMANCE REPORT (Last 30 Days)',
            '=' * 50,
            ''
        ]
        
        total_views = 0
        total_clicks = 0
        total_conversions = 0
        total_conversion_value = 0
        
        for promo in recent_promotions:
            total_views += promo.views_count
            total_clicks += promo.clicks_count
            total_conversions += promo.conversions_count
            
            # Get conversion value
            from django.db.models import Sum
            conversion_value = promo.conversions.aggregate(
                total=Sum('conversion_value')
            )['total'] or 0
            total_conversion_value += float(conversion_value)
            
            ctr = promo.get_ctr()
            conv_rate = promo.get_conversion_rate()
            
            report_lines.append(f"Promotion: {promo.promotion_id} - {promo.title}")
            report_lines.append(f"  Type: {promo.get_promotion_type_display()}")
            report_lines.append(f"  Status: {promo.get_status_display()}")
            report_lines.append(f"  Views: {promo.views_count}")
            report_lines.append(f"  Clicks: {promo.clicks_count}")
            report_lines.append(f"  CTR: {ctr:.2f}%")
            report_lines.append(f"  Conversions: {promo.conversions_count}")
            report_lines.append(f"  Conversion Rate: {conv_rate:.2f}%")
            report_lines.append(f"  Conversion Value: ${conversion_value:.2f}")
            report_lines.append('')
        
        report_lines.append('=' * 50)
        report_lines.append('TOTALS:')
        report_lines.append(f"  Total Views: {total_views}")
        report_lines.append(f"  Total Clicks: {total_clicks}")
        report_lines.append(f"  Total Conversions: {total_conversions}")
        report_lines.append(f"  Total Conversion Value: ${total_conversion_value:.2f}")
        
        overall_ctr = (total_clicks / total_views * 100) if total_views > 0 else 0
        overall_conv_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
        
        report_lines.append(f"  Overall CTR: {overall_ctr:.2f}%")
        report_lines.append(f"  Overall Conversion Rate: {overall_conv_rate:.2f}%")
        
        report_text = '\n'.join(report_lines)
        
        # Send report to all admin users
        admin_users = User.objects.filter(profile__role='admin', is_active=True)
        for admin in admin_users:
            try:
                Notification.objects.create(
                    user=admin,
                    notification_type='system',
                    title='Marketing Promotion Report - Last 30 Days',
                    message=f'Total Views: {total_views} | Clicks: {total_clicks} | Conversions: {total_conversions} | Value: ${total_conversion_value:.2f}'
                )
            except Exception as e:
                logger.error(f'Error sending report to admin {admin.id}: {str(e)}')
        
        logger.info(report_text)
        
        result = {
            'status': 'success',
            'message': 'Promotion report generated successfully',
            'summary': {
                'total_views': total_views,
                'total_clicks': total_clicks,
                'total_conversions': total_conversions,
                'total_conversion_value': total_conversion_value,
                'overall_ctr': overall_ctr,
                'overall_conversion_rate': overall_conv_rate
            }
        }
        
        return result
        
    except Exception as e:
        error_msg = f'Error generating promotion report: {str(e)}'
        logger.exception(error_msg)
        return {'status': 'error', 'message': error_msg}