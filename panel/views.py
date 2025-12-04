from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
import os
import json
from django.conf import settings as django_settings
from django.contrib.auth import login, authenticate
import urllib.parse
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import translation
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import timedelta
import json
import csv
import io
import pyotp
import qrcode
from io import BytesIO
import base64
import secrets
import stripe
import requests

from .models import (
    UserProfile, Service, ServiceCategory, Order, OrderLog, SubscriptionPackage,
    UserSubscription, Coupon, Payment, Ticket, TicketMessage,
    AffiliateCommission, BlogPost, BlacklistIP, BlacklistLink, BlacklistEmail,
    SystemSetting, Notification, MarketingPromotion, PromotionView,
    PromotionClick, PromotionConversion, SocialNetwork
)

# Create UserProfile on user creation
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Determine role: superuser gets 'admin', otherwise 'user'
        default_role = 'admin' if instance.is_superuser else 'user'
        # Use get_or_create to avoid duplicates if signal fires multiple times
        profile, _ = UserProfile.objects.get_or_create(
            user=instance,
            defaults={'role': default_role}
        )
        # If user is superuser but profile role is not admin, update it
        if instance.is_superuser and profile.role != 'admin':
            profile.role = 'admin'
            profile.save()
        # Save to generate api_key and referral_code
        elif not profile.api_key or not profile.referral_code:
            profile.save()

# Helper function to ensure user profile exists
def ensure_user_profile(user):
    """Ensure user has a profile, create one if missing. Superusers get admin role."""
    try:
        profile = user.profile
        # If user is superuser but profile role is not admin, update it
        if user.is_superuser and profile.role != 'admin':
            profile.role = 'admin'
            profile.save()
        return profile
    except UserProfile.DoesNotExist:
        # Determine role: superuser gets 'admin', otherwise 'user'
        role = 'admin' if user.is_superuser else 'user'
        profile = UserProfile.objects.create(user=user, role=role)
        return profile

# Helper function to create order logs
def create_order_log(order, log_type, message, details=None, old_value=None, new_value=None, user=None, request=None):
    """
    Create a detailed log entry for an order
    
    Args:
        order: Order instance
        log_type: Type of log (from OrderLog.LOG_TYPES)
        message: Human-readable message
        details: Dictionary with additional information
        old_value: Previous value (for status changes)
        new_value: New value (for status changes)
        user: User who performed the action (optional)
        request: HTTP request object to capture IP and user agent (optional)
    """
    log_data = {
        'order': order,
        'log_type': log_type,
        'message': message,
        'details': details or {},
        'old_value': old_value or '',
        'new_value': new_value or '',
        'performed_by': user,
    }
    
    # Extract IP and user agent from request if available
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            log_data['ip_address'] = x_forwarded_for.split(',')[0].strip()
        else:
            log_data['ip_address'] = request.META.get('REMOTE_ADDR')
        log_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    try:
        return OrderLog.objects.create(**log_data)
    except Exception as e:
        # Log the error but don't break the main flow
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create order log: {str(e)}")
        return None

# Language switching - Enhanced with Django i18n
@require_http_methods(["POST"])
def set_language(request):
    from django.utils.translation import get_language
    from django.conf import settings
    
    language = request.POST.get('language', 'en')
    next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))
    
    # Validate language
    if language in [lang[0] for lang in settings.LANGUAGES]:
        translation.activate(language)
        request.session['django_language'] = language
        
        # Save to user profile if authenticated
        if request.user.is_authenticated:
            try:
                request.user.profile.language = language
                request.user.profile.save()
            except:
                pass  # Profile might not exist yet
        
        # Set language in response
        response = redirect(next_url)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)
    else:
        response = redirect(next_url)
    
    return response

# Maintenance Mode View
def maintenance(request):
    """
    Display maintenance mode page with custom message.
    """
    from .settings_utils import get_setting
    
    maintenance_message = get_setting(
        'maintenance_message', 
        default='We are currently performing maintenance. Please check back soon.'
    )
    site_name = get_setting('site_name', default='VinFlow')
    contact_email = get_setting('site_email', default='')
    
    context = {
        'maintenance_message': maintenance_message,
        'site_name': site_name,
        'contact_email': contact_email,
    }
    
    return render(request, 'panel/maintenance.html', context)

# User Registration
def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        referral_code = request.POST.get('referral_code', '').strip()
        
        errors = []
        
        # Validate username
        if not username:
            errors.append('Username is required')
        elif len(username) < 3:
            errors.append('Username must be at least 3 characters')
        elif User.objects.filter(username=username).exists():
            errors.append('Username already exists')
        
        # Validate email
        if not email:
            errors.append('Email is required')
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append('Invalid email address')
            else:
                if User.objects.filter(email=email).exists():
                    errors.append('Email already registered')
        
        # Validate password
        if not password:
            errors.append('Password is required')
        elif len(password) < 8:
            errors.append('Password must be at least 8 characters')
        elif password != password_confirm:
            errors.append('Passwords do not match')
        
        # If no errors, create user
        if not errors:
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                
                # Ensure profile is created (should be done by signal, but double-check)
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={'role': 'user'}
                )
                
                # Handle referral code
                if referral_code:
                    try:
                        referrer = UserProfile.objects.get(referral_code=referral_code.upper())
                        profile.referred_by = referrer.user
                        profile.save()
                    except UserProfile.DoesNotExist:
                        pass  # Invalid referral code, ignore
                
                # Auto-login after registration
                user = authenticate(username=username, password=password)
                if user:
                    login(request, user)
                    messages.success(request, 'Registration successful! Welcome to VinFlow!')
                    return redirect('dashboard')
                else:
                    errors.append('Registration successful but login failed. Please try logging in.')
            except Exception as e:
                errors.append(f'Registration failed: {str(e)}')
        
        # Show errors
        for error in errors:
            messages.error(request, error)
    
    return render(request, 'auth/register.html')

# User Logout
def user_logout(request):
    from django.contrib.auth import logout
    from django.views.decorators.http import require_http_methods
    
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
    else:
        # Already logged out, just redirect
        return redirect('login')
    
    return redirect('login')

# User Login
def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username:
            messages.error(request, 'Username is required')
        elif not password:
            messages.error(request, 'Password is required')
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    # Ensure user profile exists (create if missing)
                    # Superusers get admin role, others get user role
                    default_role = 'admin' if user.is_superuser else 'user'
                    profile, created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults={'role': default_role}
                    )
                    # If user is superuser but profile role is not admin, update it
                    if user.is_superuser and profile.role != 'admin':
                        profile.role = 'admin'
                        profile.save()
                    elif created:
                        # Profile was just created, save it to generate api_key and referral_code
                        profile.save()
                    
                    # Check if 2FA is enabled
                    try:
                        if profile.two_factor_enabled:
                            # Store user ID in session for 2FA verification
                            request.session['2fa_user_id'] = user.id
                            request.session['2fa_verified'] = False
                            return redirect('verify_2fa')
                        else:
                            # No 2FA, proceed with normal login
                            login(request, user)
                            # Set language from user profile
                            try:
                                if profile.language:
                                    translation.activate(profile.language)
                                    request.session['django_language'] = profile.language
                            except:
                                pass
                            
                            messages.success(request, f'Welcome back, {user.username}!')
                            next_url = request.GET.get('next', 'dashboard')
                            return redirect(next_url)
                    except Exception as e:
                        # Fallback: proceed with normal login even if profile access fails
                        login(request, user)
                        messages.success(request, f'Welcome back, {user.username}!')
                        next_url = request.GET.get('next', 'dashboard')
                        return redirect(next_url)
                else:
                    messages.error(request, 'Your account has been disabled. Please contact support.')
            else:
                messages.error(request, 'Invalid username or password. Please try again.')
    
    return render(request, 'auth/login.html')

# Google OAuth Login
def google_login(request):
    """Initiate Google OAuth login flow"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    from django.conf import settings
    
    # Check if Google OAuth is configured
    if not settings.GOOGLE_OAUTH2_CLIENT_ID:
        messages.error(request, 'Google OAuth is not configured. Please contact administrator.')
        return redirect('login')
    
    # Generate state token for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)
    request.session['google_oauth_state'] = state
    request.session['google_oauth_next'] = request.GET.get('next', 'dashboard')
    
    # Build Google OAuth URL
    params = {
        'client_id': settings.GOOGLE_OAUTH2_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_OAUTH2_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'offline',
        'prompt': 'consent',
    }
    
    auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params)
    return redirect(auth_url)

# Google OAuth Callback
def google_callback(request):
    """Handle Google OAuth callback"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    from django.conf import settings
    
    # Verify state token
    state = request.GET.get('state')
    if not state or state != request.session.get('google_oauth_state'):
        messages.error(request, 'Invalid OAuth state. Please try again.')
        return redirect('login')
    
    # Get authorization code
    code = request.GET.get('code')
    if not code:
        error = request.GET.get('error', 'Unknown error')
        messages.error(request, f'Google authentication failed: {error}')
        return redirect('login')
    
    # Exchange code for access token
    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        'code': code,
        'client_id': settings.GOOGLE_OAUTH2_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        'redirect_uri': settings.GOOGLE_OAUTH2_REDIRECT_URI,
        'grant_type': 'authorization_code',
    }
    
    try:
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        token_json = token_response.json()
        access_token = token_json.get('access_token')
        
        if not access_token:
            messages.error(request, 'Failed to get access token from Google.')
            return redirect('login')
        
        # Get user info from Google
        user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        user_info_response = requests.get(user_info_url, headers=headers)
        user_info_response.raise_for_status()
        user_info = user_info_response.json()
        
        # Extract user information
        google_id = user_info.get('id')
        email = user_info.get('email')
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')
        full_name = user_info.get('name', '')
        picture = user_info.get('picture', '')
        
        if not email:
            messages.error(request, 'Unable to get email from Google account.')
            return redirect('login')
        
        # Check if user exists by email
        try:
            user = User.objects.get(email=email)
            # User exists, log them in
            if not user.is_active:
                messages.error(request, 'Your account has been disabled. Please contact support.')
                return redirect('login')
        except User.DoesNotExist:
            # Create new user
            # Generate username from email or use full name
            username_base = email.split('@')[0]
            username = username_base
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{username_base}{counter}"
                counter += 1
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.set_unusable_password()  # No password needed for OAuth users
            user.save()
        
        # Ensure profile exists
        default_role = 'admin' if user.is_superuser else 'user'
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'role': default_role}
        )
        
        # Update profile with Google info if available
        if picture and not profile.avatar:
            try:
                # Download and save avatar
                img_response = requests.get(picture)
                if img_response.status_code == 200:
                    img_name = f"avatars/google_{user.id}_{google_id}.jpg"
                    profile.avatar.save(img_name, ContentFile(img_response.content), save=False)
            except Exception:
                pass  # Ignore avatar download errors
        
        # Update user name if not set
        if not user.first_name and first_name:
            user.first_name = first_name
        if not user.last_name and last_name:
            user.last_name = last_name
        if user.first_name or user.last_name:
            user.save()
        
        # Check if 2FA is enabled
        if profile.two_factor_enabled:
            request.session['2fa_user_id'] = user.id
            request.session['2fa_verified'] = False
            # Clear OAuth state
            if 'google_oauth_state' in request.session:
                del request.session['google_oauth_state']
            return redirect('verify_2fa')
        else:
            # Log the user in
            login(request, user)
            
            # Set language from user profile
            try:
                if profile.language:
                    translation.activate(profile.language)
                    request.session['django_language'] = profile.language
            except:
                pass
            
            messages.success(request, f'Welcome, {user.get_full_name() or user.username}!')
            
            # Clear OAuth state
            if 'google_oauth_state' in request.session:
                del request.session['google_oauth_state']
            
            # Redirect to next URL or dashboard
            next_url = request.session.get('google_oauth_next', 'dashboard')
            if 'google_oauth_next' in request.session:
                del request.session['google_oauth_next']
            return redirect(next_url)
    
    except requests.exceptions.RequestException as e:
        messages.error(request, f'Error communicating with Google: {str(e)}')
        return redirect('login')
    except Exception as e:
        messages.error(request, f'An error occurred during Google authentication: {str(e)}')
        return redirect('login')


# Landing Page View
def landing_page(request):
    """
    Landing page view for visitors
    Redirects logged-in users to dashboard
    Displays service information and encourages sign-ups for visitors
    """
    # Redirect authenticated users to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    return render(request, 'landing/index.html')


# Home/Root View - Smart redirect
def home(request):
    """
    Smart home view that redirects based on authentication status
    - Not logged in: Show landing page
    - Logged in: Redirect to dashboard
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return render(request, 'landing/index.html')


# Dashboard
@login_required
def dashboard(request):
    user = request.user
    # Ensure profile exists
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': 'user'}
    )
    
    # Statistics
    total_orders = Order.objects.filter(user=user).count()
    completed_orders = Order.objects.filter(user=user, status='Completed').count()
    pending_orders = Order.objects.filter(user=user, status__in=['Pending', 'Processing']).count()
    total_spent = Order.objects.filter(user=user).aggregate(Sum('charge'))['charge__sum'] or 0
    
    # Recent orders
    recent_orders = Order.objects.select_related('service').filter(user=user).order_by('-created_at')[:5]
    
    # Active subscriptions
    active_subscriptions = UserSubscription.objects.filter(user=user, is_active=True).count()
    
    # Get active promotions for dashboard
    now = timezone.now()
    dashboard_promotions = MarketingPromotion.objects.filter(
        is_active=True,
        status='active',
        start_date__lte=now,
        end_date__gte=now,
        display_location__in=['dashboard', 'all_pages']
    ).order_by('-display_priority')[:3]
    
    # Filter by target audience
    filtered_dashboard_promotions = []
    for promo in dashboard_promotions:
        if promo.target_audience == 'all':
            filtered_dashboard_promotions.append(promo)
        elif promo.target_audience == 'new_users' and profile.created_at >= timezone.now() - timedelta(days=7):
            filtered_dashboard_promotions.append(promo)
        elif promo.target_audience == 'active_users' and profile.total_spent > 0:
            filtered_dashboard_promotions.append(promo)
        elif promo.target_audience == 'inactive_users' and profile.total_spent == 0:
            filtered_dashboard_promotions.append(promo)
        elif promo.target_audience == 'high_spenders' and profile.total_spent >= 100:
            filtered_dashboard_promotions.append(promo)
        elif promo.target_audience == 'resellers' and profile.is_reseller:
            filtered_dashboard_promotions.append(promo)
        elif promo.target_audience == 'specific_users' and promo.specific_users.filter(id=user.id).exists():
            filtered_dashboard_promotions.append(promo)
    
    context = {
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'total_spent': total_spent,
        'recent_orders': recent_orders,
        'active_subscriptions': active_subscriptions,
        'dashboard_promotions': filtered_dashboard_promotions,
    }
    return render(request, 'panel/dashboard.html', context)

# Services List
def services(request):
    categories = ServiceCategory.objects.filter(is_active=True).prefetch_related('service_set')
    services_list = Service.objects.filter(is_active=True).select_related('category')
    
    # Group by category
    services_by_category = {}
    for category in categories:
        services_by_category[category] = services_list.filter(category=category)
    
    context = {
        'services_by_category': services_by_category,
        'all_services': services_list,
    }
    return render(request, 'panel/services.html', context)

# New Order Page
@login_required
def new_order(request):
    """
    Optimized order creation page with lazy-loading services
    Services are loaded via AJAX when category is selected for better performance
    """
    categories = ServiceCategory.objects.filter(is_active=True).select_related('social_network').order_by('order')
    social_networks = SocialNetwork.objects.filter(is_active=True).order_by('display_order', 'name')
    
    # Check if user language is Khmer
    is_khmer = request.user.profile.language == 'km' if hasattr(request.user, 'profile') else False
    
    # Get user balance
    profile = ensure_user_profile(request.user)
    user_balance = profile.balance
    
    context = {
        'categories': categories,
        # Services are now loaded dynamically via AJAX - no initial load
        'social_networks': social_networks,
        'is_khmer': is_khmer,
        'user_balance': user_balance,
    }
    return render(request, 'panel/new_order.html', context)


@login_required
@require_http_methods(["GET"])
def get_services_by_category(request):
    """
    AJAX endpoint to fetch services for a specific category
    Returns JSON with service data for dynamic loading
    """
    category_id = request.GET.get('category_id')
    platform_code = request.GET.get('platform')
    search_term = request.GET.get('search', '').strip().lower()
    
    if not category_id:
        return JsonResponse({'error': 'Category ID is required'}, status=400)
    
    try:
        # Build query with optimized select_related
        services = Service.objects.filter(
            is_active=True,
            category_id=category_id
        ).select_related('category', 'category__social_network')
        
        # Apply platform filter if provided
        if platform_code and platform_code != 'all':
            services = services.filter(category__social_network__platform_code=platform_code)
        
        # Apply search filter if provided
        if search_term:
            services = services.filter(
                Q(name__icontains=search_term) | 
                Q(name_km__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        
        # Order by name
        services = services.order_by('name')
        
        # Check if user language is Khmer
        is_khmer = request.user.profile.language == 'km' if hasattr(request.user, 'profile') else False
        
        # Build service data
        services_data = []
        for service in services:
            social_network = service.category.social_network if service.category else None
            
            service_data = {
                'id': service.id,
                'external_service_id': service.external_service_id,
                'name': service.name_km if is_khmer and service.name_km else service.name,
                'description': (service.description_km if is_khmer and service.description_km else service.description)[:200] if service.description else '',
                'rate': float(service.rate),
                'min_order': service.min_order,
                'max_order': service.max_order,
                'drip_feed_enabled': service.drip_feed_enabled,
                'category_id': service.category.id if service.category else None,
                'platform_code': social_network.platform_code if social_network else '',
            }
            
            # Add social network info if available
            if social_network:
                service_data['social_network'] = {
                    'name': social_network.name,
                    'color': social_network.color,
                    'icon': social_network.icon,
                    'icon_image_url': social_network.icon_image.url if social_network.icon_image else None,
                }
            
            services_data.append(service_data)
        
        return JsonResponse({
            'success': True,
            'services': services_data,
            'count': len(services_data),
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# Create Order
@login_required
@require_http_methods(["POST"])
def create_order(request):
    try:
        # Safely get and validate service_id
        service_id = request.POST.get('service_id', '').strip()
        if not service_id:
            messages.error(request, 'Please select a service')
            return redirect('new_order')
        
        # Safely get other fields
        link = request.POST.get('link', '').strip()
        if not link:
            messages.error(request, 'Please provide a link')
            return redirect('new_order')
        
        # Safely convert quantity to int
        quantity_str = request.POST.get('quantity', '').strip()
        if not quantity_str:
            messages.error(request, 'Please enter a quantity')
            return redirect('new_order')
        
        try:
            quantity = int(quantity_str)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid quantity value')
            return redirect('new_order')
        
        # Drip feed settings
        drip_feed = request.POST.get('drip_feed') == 'on'
        
        # Safely convert drip feed values
        drip_feed_quantity = 0
        drip_feed_days = 0
        if drip_feed:
            drip_feed_quantity_str = request.POST.get('drip_feed_quantity', '').strip()
            drip_feed_days_str = request.POST.get('drip_feed_days', '').strip()
            
            try:
                if drip_feed_quantity_str:
                    drip_feed_quantity = int(drip_feed_quantity_str)
                if drip_feed_days_str:
                    drip_feed_days = int(drip_feed_days_str)
            except (ValueError, TypeError):
                messages.error(request, 'Invalid drip feed values')
                return redirect('new_order')
        
        coupon_code = request.POST.get('coupon_code', '').strip()
        
        # Get service
        service = get_object_or_404(Service, id=service_id, is_active=True)
        
        # Validate quantity
        if quantity < service.min_order or quantity > service.max_order:
            messages.error(request, f'Quantity must be between {service.min_order} and {service.max_order}')
            return redirect('new_order')
        
        # Calculate charge
        charge = (service.rate / 1000) * quantity
        
        # Apply coupon if provided
        discount = 0
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code.upper(), is_active=True)
                if coupon.valid_from <= timezone.now() <= coupon.valid_until:
                    if coupon.usage_limit is None or coupon.used_count < coupon.usage_limit:
                        if charge >= coupon.min_purchase:
                            if coupon.discount_type == 'percent':
                                discount = (charge * coupon.discount_value) / 100
                                if coupon.max_discount:
                                    discount = min(discount, coupon.max_discount)
                            else:
                                discount = coupon.discount_value
                            coupon.used_count += 1
                            coupon.save()
            except Coupon.DoesNotExist:
                pass
        
        final_charge = max(0, charge - discount)
        
        # Check balance
        profile = ensure_user_profile(request.user)
        if profile.balance < final_charge:
            messages.error(request, f'Insufficient balance. You need ${final_charge:.2f} but only have ${profile.balance:.2f}. Please top up your account.')
            return redirect('new_order')
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            service=service,
            link=link,
            quantity=quantity,
            charge=final_charge,
            drip_feed=drip_feed,
            drip_feed_quantity=drip_feed_quantity if drip_feed else 0,
            drip_feed_days=drip_feed_days if drip_feed else 0,
        )
        
        # Log order creation
        creation_details = {
            'service': service.name,
            'service_id': str(service.id),
            'link': link,
            'quantity': quantity,
            'rate': float(service.rate),
            'charge': float(charge),
            'discount': float(discount),
            'final_charge': float(final_charge),
            'drip_feed': drip_feed,
            'coupon_used': coupon_code if coupon_code else None,
        }
        create_order_log(
            order=order,
            log_type='created',
            message=f'Order created by {request.user.username}',
            details=creation_details,
            user=request.user,
            request=request
        )
        
        # Ensure profile exists and deduct balance
        profile = ensure_user_profile(request.user)
        old_balance = profile.balance
        profile.balance -= final_charge
        profile.total_spent += final_charge
        profile.save()
        
        # Log balance deduction
        create_order_log(
            order=order,
            log_type='balance_deducted',
            message=f'Balance deducted: ${final_charge:.2f}',
            details={
                'old_balance': float(old_balance),
                'amount_deducted': float(final_charge),
                'new_balance': float(profile.balance),
            },
            old_value=f'${old_balance:.2f}',
            new_value=f'${profile.balance:.2f}',
            user=request.user,
            request=request
        )
        
        # Place order to supplier (async)
        from .tasks import place_order_to_supplier, execute_task_async_or_sync
        
        # Log API call initiation
        create_order_log(
            order=order,
            log_type='api_call',
            message='Initiating API call to supplier',
            details={
                'service_external_id': service.external_service_id,
                'async': True,
            }
        )
        
        execute_task_async_or_sync(place_order_to_supplier, order.id)
        
        messages.success(request, f'Order #{order.order_id} created successfully!')
        return redirect('orders')
        
    except Exception as e:
        messages.error(request, f'Error creating order: {str(e)}')
        return redirect('new_order')

# Validate Coupon Code (AJAX)
@login_required
def validate_coupon(request):
    """AJAX endpoint to validate coupon code"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
    
    coupon_code = request.POST.get('coupon_code', '').strip().upper()
    charge = float(request.POST.get('charge', 0))
    
    if not coupon_code:
        return JsonResponse({
            'status': 'error',
            'message': 'Please enter a coupon code',
            'discount': 0,
            'final_charge': charge
        })
    
    try:
        coupon = Coupon.objects.get(code=coupon_code, is_active=True)
        now = timezone.now()
        
        # Check validity period
        if not (coupon.valid_from <= now <= coupon.valid_until):
            return JsonResponse({
                'status': 'error',
                'message': 'Coupon has expired or is not yet valid',
                'discount': 0,
                'final_charge': charge
            })
        
        # Check usage limit
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            return JsonResponse({
                'status': 'error',
                'message': 'Coupon has reached its usage limit',
                'discount': 0,
                'final_charge': charge
            })
        
        # Check minimum purchase
        if charge < coupon.min_purchase:
            return JsonResponse({
                'status': 'error',
                'message': f'Minimum purchase of ${coupon.min_purchase:.2f} required',
                'discount': 0,
                'final_charge': charge
            })
        
        # Calculate discount
        if coupon.discount_type == 'percent':
            discount = (charge * coupon.discount_value) / 100
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
        else:
            discount = min(coupon.discount_value, charge)
        
        final_charge = max(0, charge - discount)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Coupon applied! Discount: ${discount:.2f}',
            'discount': float(discount),
            'final_charge': float(final_charge),
            'discount_type': coupon.discount_type,
            'discount_value': float(coupon.discount_value)
        })
        
    except Coupon.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid coupon code',
            'discount': 0,
            'final_charge': charge
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error validating coupon: {str(e)}',
            'discount': 0,
            'final_charge': charge
        })

# Orders List
@login_required
def orders(request):
    orders_list = Order.objects.select_related('service').filter(user=request.user).order_by('-created_at')
    
    # Filtering
    status_filter = request.GET.get('status', '')
    platform_filter = request.GET.get('platform', '')
    
    if status_filter:
        orders_list = orders_list.filter(status=status_filter)
    
    if platform_filter:
        orders_list = orders_list.filter(platform=platform_filter)
    
    context = {
        'orders': orders_list,
        'status_filter': status_filter,
        'platform_filter': platform_filter,
        'platform_choices': Order.PLATFORM_CHOICES,
    }
    return render(request, 'panel/orders.html', context)

# Order Detail (HTMX)
@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('service').prefetch_related('logs__performed_by'),
        id=order_id,
        user=request.user
    )
    # Get all logs for this order
    logs = order.logs.all()
    
    return render(request, 'panel/partials/order_detail.html', {
        'order': order,
        'logs': logs
    })

# Real-time Order Status (HTMX polling)
@login_required
def order_status(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('service'),
        id=order_id,
        user=request.user
    )
    return render(request, 'panel/partials/order_status.html', {'order': order})

# Mass Order Upload
@login_required
@require_http_methods(["POST"])
def mass_order_upload(request):
    try:
        file = request.FILES.get('csv_file')
        if not file:
            messages.error(request, 'No file uploaded')
            return redirect('orders')
        
        # Read CSV
        decoded_file = file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        created_count = 0
        errors = []
        
        for row in reader:
            try:
                service_id = int(row.get('service_id', 0))
                link = row.get('link', '').strip()
                quantity = int(row.get('quantity', 0))
                
                if not link or not service_id or not quantity:
                    errors.append(f'Row {reader.line_num}: Missing required fields')
                    continue
                
                service = get_object_or_404(Service, id=service_id, is_active=True)
                charge = (service.rate / 1000) * quantity
                
                if request.user.profile.balance < charge:
                    errors.append(f'Row {reader.line_num}: Insufficient balance')
                    continue
                
                order = Order.objects.create(
                    user=request.user,
                    service=service,
                    link=link,
                    quantity=quantity,
                    charge=charge,
                )
                
                request.user.profile.balance -= charge
                request.user.profile.total_spent += charge
                
                from .tasks import place_order_to_supplier, execute_task_async_or_sync
                execute_task_async_or_sync(place_order_to_supplier, order.id)
                
                created_count += 1
                
            except Exception as e:
                errors.append(f'Row {reader.line_num}: {str(e)}')
        
        request.user.profile.save()
        
        if created_count > 0:
            messages.success(request, f'{created_count} orders created successfully!')
        if errors:
            messages.warning(request, f'{len(errors)} errors occurred')
        
        return redirect('orders')
        
    except Exception as e:
        messages.error(request, f'Error processing file: {str(e)}')
        return redirect('orders')

# Tickets
@login_required
def tickets(request):
    tickets_list = Ticket.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'panel/tickets.html', {'tickets': tickets_list})

@login_required
def create_ticket(request):
    if request.method == 'POST':
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        priority = request.POST.get('priority', 'medium')
        
        ticket = Ticket.objects.create(
            user=request.user,
            subject=subject,
            priority=priority,
        )
        
        TicketMessage.objects.create(
            ticket=ticket,
            user=request.user,
            message=message,
        )
        
        messages.success(request, 'Ticket created successfully!')
        return redirect('tickets')
    
    return render(request, 'panel/create_ticket.html')

@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    
    if request.method == 'POST':
        message = request.POST.get('message')
        profile = ensure_user_profile(request.user)
        is_admin = profile.role == 'admin'
        
        TicketMessage.objects.create(
            ticket=ticket,
            user=request.user,
            message=message,
            is_admin=is_admin,
        )
        
        if ticket.status == 'resolved':
            ticket.status = 'open'
            ticket.save()
        
        return redirect('ticket_detail', ticket_id=ticket_id)
    
    return render(request, 'panel/ticket_detail.html', {'ticket': ticket})

# Free Trial
@login_required
def free_trial(request):
    if request.method == 'POST':
        # Find a likes service
        likes_service = Service.objects.filter(
            name__icontains='likes',
            is_active=True
        ).first()
        
        if not likes_service:
            messages.error(request, 'Free trial service not available')
            return redirect('services')
        
        # Check if user already used free trial
        if Order.objects.filter(user=request.user, service=likes_service, charge=0).exists():
            messages.warning(request, 'You have already used your free trial')
            return redirect('services')
        
        link = request.POST.get('link', '')
        if not link:
            messages.error(request, 'Please provide a link')
            return redirect('services')
        
        # Create free order
        order = Order.objects.create(
            user=request.user,
            service=likes_service,
            link=link,
            quantity=100,
            charge=0.00,
        )
        
        from .tasks import place_order_to_supplier, execute_task_async_or_sync
        execute_task_async_or_sync(place_order_to_supplier, order.id)
        
        messages.success(request, 'Free 100 likes trial activated!')
        return redirect('orders')
    
    # GET request - show form
    likes_service = Service.objects.filter(
        name__icontains='likes',
        is_active=True
    ).first()
    
    if not likes_service:
        messages.error(request, 'Free trial service not available')
        return redirect('services')
    
    # Check if user already activated free trial
    has_used_trial = Order.objects.filter(
        user=request.user, 
        service=likes_service, 
        charge=0
    ).exists()
    
    return render(request, 'panel/free_trial.html', {
        'service': likes_service,
        'has_used_trial': has_used_trial
    })

# Profile
@login_required
def profile(request):
    # Ensure profile exists
    profile = ensure_user_profile(request.user)
    
    if request.method == 'POST':
        try:
            # Handle avatar upload
            if 'avatar' in request.FILES:
                avatar = request.FILES['avatar']
                # Validate file size (max 5MB)
                if avatar.size > 5 * 1024 * 1024:
                    messages.error(request, 'Avatar file size must be less than 5MB')
                else:
                    # Validate file type
                    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
                    if avatar.content_type in allowed_types:
                        # Delete old avatar if exists
                        if profile.avatar:
                            profile.avatar.delete(save=False)
                        profile.avatar = avatar
                        messages.success(request, 'Avatar updated successfully!')
                    else:
                        messages.error(request, 'Invalid file type. Please upload JPEG, PNG, GIF, or WebP image.')
            
            # Update language
            if 'language' in request.POST:
                language = request.POST.get('language', 'en')
                profile.language = language
                
                # Activate language and save to session
                translation.activate(language)
                request.session['django_language'] = language
                
                # Set language cookie
                from django.conf import settings
                response = redirect('profile')
                response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)
            else:
                response = redirect('profile')
            
            # Update email if provided
            if 'email' in request.POST:
                email = request.POST.get('email', '').strip()
                if email:
                    try:
                        validate_email(email)
                        request.user.email = email
                        request.user.save()
                    except ValidationError:
                        messages.error(request, 'Invalid email address')
            
            # Save profile
            profile.save()
            request.user.save()
            
            if 'language' not in request.POST:
                messages.success(request, 'Profile updated successfully!')
            
            return response
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            return redirect('profile')
    
    # Get order statistics for sidebar
    from .models import Order
    total_orders = Order.objects.filter(user=request.user).count()
    completed_orders = Order.objects.filter(user=request.user, status='Completed').count()
    pending_orders = Order.objects.filter(user=request.user, status__in=['Pending', 'Processing']).count()
    
    context = {
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
    }
    
    return render(request, 'panel/profile.html', context)

# 2FA Verification (for login)
def verify_2fa(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    user_id = request.session.get('2fa_user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('login')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Invalid session')
        del request.session['2fa_user_id']
        return redirect('login')
    
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        backup_code = request.POST.get('backup_code', '').strip()
        
        if backup_code:
            # Verify backup code
            if backup_code in user.profile.backup_codes:
                # Remove used backup code
                user.profile.backup_codes.remove(backup_code)
                user.profile.save()
                
                # Login user
                login(request, user)
                request.session['2fa_verified'] = True
                del request.session['2fa_user_id']
                
                # Set language
                try:
                    if user.profile.language:
                        translation.activate(user.profile.language)
                        request.session['django_language'] = user.profile.language
                except:
                    pass
                
                messages.success(request, f'Welcome back, {user.username}!')
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid backup code')
        elif code:
            # Verify TOTP code
            if user.profile.two_factor_secret:
                totp = pyotp.TOTP(user.profile.two_factor_secret)
                if totp.verify(code, valid_window=1):
                    # Login user
                    login(request, user)
                    request.session['2fa_verified'] = True
                    del request.session['2fa_user_id']
                    
                    # Set language
                    try:
                        if user.profile.language:
                            translation.activate(user.profile.language)
                            request.session['django_language'] = user.profile.language
                    except:
                        pass
                    
                    messages.success(request, f'Welcome back, {user.username}!')
                    next_url = request.GET.get('next', 'dashboard')
                    return redirect(next_url)
                else:
                    messages.error(request, 'Invalid verification code')
            else:
                messages.error(request, '2FA not properly configured')
        else:
            messages.error(request, 'Please enter a verification code')
    
    return render(request, 'auth/verify_2fa.html', {'user': user})

# 2FA Setup
@login_required
def setup_2fa(request):
    profile = ensure_user_profile(request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate':
            # Generate new secret
            secret = pyotp.random_base32()
            profile.two_factor_secret = secret
            profile.save()
            
            # Generate QR code
            totp = pyotp.TOTP(secret)
            issuer_name = "VinFlow"
            account_name = request.user.email or request.user.username
            otp_uri = totp.provisioning_uri(
                name=account_name,
                issuer_name=issuer_name
            )
            
            # Create QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(otp_uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_code_data = base64.b64encode(buffer.getvalue()).decode()
            
            context = {
                'secret': secret,
                'qr_code': qr_code_data,
                'otp_uri': otp_uri,
            }
            return render(request, 'panel/setup_2fa.html', context)
        
        elif action == 'verify':
            # Verify and enable 2FA
            code = request.POST.get('code', '').strip()
            if not code:
                messages.error(request, 'Please enter a verification code')
                return redirect('setup_2fa')
            
            if not profile.two_factor_secret:
                messages.error(request, 'Please generate a secret first')
                return redirect('setup_2fa')
            
            totp = pyotp.TOTP(profile.two_factor_secret)
            if totp.verify(code, valid_window=1):
                # Generate backup codes
                backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
                profile.backup_codes = backup_codes
                profile.two_factor_enabled = True
                profile.save()
                
                messages.success(request, '2FA has been enabled successfully!')
                return render(request, 'panel/setup_2fa.html', {
                    'backup_codes': backup_codes,
                    'enabled': True
                })
            else:
                messages.error(request, 'Invalid verification code. Please try again.')
                return redirect('setup_2fa')
    
    # Check if 2FA is already enabled
    if profile.two_factor_enabled:
        return redirect('profile')
    
    # Show setup page
    if profile.two_factor_secret:
        # Generate QR code for existing secret
        totp = pyotp.TOTP(profile.two_factor_secret)
        issuer_name = "VinFlow"
        account_name = request.user.email or request.user.username
        otp_uri = totp.provisioning_uri(
            name=account_name,
            issuer_name=issuer_name
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(otp_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()
        
        return render(request, 'panel/setup_2fa.html', {
            'secret': profile.two_factor_secret,
            'qr_code': qr_code_data,
            'otp_uri': otp_uri,
        })
    
    return render(request, 'panel/setup_2fa.html')

# Disable 2FA
@login_required
@require_http_methods(["POST"])
def disable_2fa(request):
    profile = ensure_user_profile(request.user)
    
    # Verify password or require 2FA code to disable
    code = request.POST.get('code', '').strip()
    password = request.POST.get('password', '')
    
    if not code and not password:
        messages.error(request, 'Please provide verification code or password')
        return redirect('profile')
    
    # Verify with 2FA code
    if code:
        if profile.two_factor_secret:
            totp = pyotp.TOTP(profile.two_factor_secret)
            if not totp.verify(code, valid_window=1):
                messages.error(request, 'Invalid verification code')
                return redirect('profile')
        else:
            messages.error(request, '2FA not properly configured')
            return redirect('profile')
    # Or verify with password
    elif password:
        if not request.user.check_password(password):
            messages.error(request, 'Invalid password')
            return redirect('profile')
    
    # Disable 2FA
    profile.two_factor_enabled = False
    profile.two_factor_secret = ''
    profile.backup_codes = []
    profile.save()
    
    messages.success(request, '2FA has been disabled successfully')
    return redirect('profile')

# Regenerate Backup Codes
@login_required
@require_http_methods(["POST"])
def regenerate_backup_codes(request):
    profile = ensure_user_profile(request.user)
    
    if not profile.two_factor_enabled:
        messages.error(request, '2FA is not enabled')
        return redirect('profile')
    
    # Verify with 2FA code
    code = request.POST.get('code', '').strip()
    if not code:
        messages.error(request, 'Please provide verification code')
        return redirect('profile')
    
    if profile.two_factor_secret:
        totp = pyotp.TOTP(profile.two_factor_secret)
        if not totp.verify(code, valid_window=1):
            messages.error(request, 'Invalid verification code')
            return redirect('profile')
    else:
        messages.error(request, '2FA not properly configured')
        return redirect('profile')
    
    # Generate new backup codes
    backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
    profile.backup_codes = backup_codes
    profile.save()
    
    messages.success(request, 'Backup codes regenerated successfully!')
    return render(request, 'panel/backup_codes.html', {
        'backup_codes': backup_codes
    })

# Admin Dashboard
@login_required
def admin_dashboard(request):
    # Ensure profile exists (superusers automatically get admin role)
    profile = ensure_user_profile(request.user)
    
    # Allow access if user is superuser OR has admin role
    if not (request.user.is_superuser or profile.role == 'admin'):
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    # Statistics
    total_users = User.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(Sum('charge'))['charge__sum'] or 0
    pending_orders = Order.objects.filter(status__in=['Pending', 'Processing']).count()
    
    # Daily stats (last 30 days)
    today = timezone.now().date()
    daily_stats = []
    for i in range(30):
        date = today - timedelta(days=i)
        orders_count = Order.objects.filter(created_at__date=date).count()
        revenue = Order.objects.filter(created_at__date=date).aggregate(Sum('charge'))['charge__sum'] or 0
        daily_stats.append({
            'date': date,
            'orders': orders_count,
            'revenue': float(revenue),
        })
    
    daily_stats.reverse()
    
    # Top services
    top_services = Service.objects.annotate(
        order_count=Count('order')
    ).order_by('-order_count')[:10]
    
    # Recent orders
    recent_orders = Order.objects.order_by('-created_at')[:10]
    
    # Pending tickets count for sidebar
    pending_tickets_count = Ticket.objects.filter(status__in=['open', 'in_progress']).count()
    
    # Get maintenance mode status
    from .settings_utils import get_setting_bool
    maintenance_mode = get_setting_bool('maintenance_mode', default=False)
    
    context = {
        'total_users': total_users,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_orders': pending_orders,
        'daily_stats': daily_stats,
        'top_services': top_services,
        'recent_orders': recent_orders,
        'pending_tickets_count': pending_tickets_count,
        'maintenance_mode': maintenance_mode,
    }
    return render(request, 'panel/admin/dashboard.html', context)

# Admin decorator
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # For AJAX requests, return JSON error instead of redirect
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.endswith('/details/'):
                return HttpResponse(
                    '<div class="text-center py-12">'
                    '<p class="text-red-400">Authentication required</p>'
                    '</div>',
                    status=401
                )
            messages.error(request, 'Access denied')
            return redirect('dashboard')
        
        # Ensure profile exists (superusers automatically get admin role)
        profile = ensure_user_profile(request.user)
        
        # Allow access if user is superuser OR has admin role
        if not (request.user.is_superuser or profile.role == 'admin'):
            # For AJAX requests, return error instead of redirect
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.endswith('/details/'):
                return HttpResponse(
                    '<div class="text-center py-12">'
                    '<p class="text-red-400">Admin access required</p>'
                    '</div>',
                    status=403
                )
            messages.error(request, 'Access denied')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

# Admin Statistics (same as dashboard)
@login_required
@admin_required
def admin_statistics(request):
    return admin_dashboard(request)

# Admin Reports
@login_required
@admin_required
def admin_reports(request):
    # Generate various reports
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    
    # Revenue reports
    revenue_7d = Order.objects.filter(created_at__date__gte=last_7_days).aggregate(Sum('charge'))['charge__sum'] or 0
    revenue_30d = Order.objects.filter(created_at__date__gte=last_30_days).aggregate(Sum('charge'))['charge__sum'] or 0
    
    # Order reports
    orders_7d = Order.objects.filter(created_at__date__gte=last_7_days).count()
    orders_30d = Order.objects.filter(created_at__date__gte=last_30_days).count()
    
    # User reports
    new_users_7d = User.objects.filter(date_joined__date__gte=last_7_days).count()
    new_users_30d = User.objects.filter(date_joined__date__gte=last_30_days).count()
    
    # Service performance
    service_performance = Service.objects.annotate(
        total_orders=Count('order'),
        total_revenue=Sum('order__charge')
    ).order_by('-total_revenue')[:20]
    
    context = {
        'revenue_7d': revenue_7d,
        'revenue_30d': revenue_30d,
        'orders_7d': orders_7d,
        'orders_30d': orders_30d,
        'new_users_7d': new_users_7d,
        'new_users_30d': new_users_30d,
        'service_performance': service_performance,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/reports.html', context)

# Admin Orders Management
@login_required
@admin_required
def admin_orders(request):
    status_filter = request.GET.get('status', '')
    platform_filter = request.GET.get('platform', '')
    search = request.GET.get('search', '')
    
    orders = Order.objects.select_related('service', 'user').all()
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if platform_filter:
        orders = orders.filter(platform=platform_filter)
    
    if search:
        orders = orders.filter(
            Q(order_id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(service__name__icontains=search) |
            Q(link__icontains=search)
        )
    
    orders = orders.order_by('-created_at')[:100]
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'platform_filter': platform_filter,
        'search': search,
        'platform_choices': Order.PLATFORM_CHOICES,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/orders.html', context)

# Admin Order Details with Logs
@login_required
@admin_required
def admin_order_details(request, order_id):
    """Admin view for detailed order information with activity logs"""
    try:
        order = get_object_or_404(
            Order.objects.select_related('service', 'user', 'service__category', 'service__category__social_network'),
            id=order_id
        )
        
        # Get all logs for this order, ordered by most recent first
        # Handle case where OrderLog table might not exist yet (migration not run)
        try:
            logs = order.logs.all().order_by('-created_at')
            
            # Calculate some statistics
            log_stats = {
                'total_logs': logs.count(),
                'api_calls': logs.filter(log_type='api_call').count(),
                'status_changes': logs.filter(log_type='status_change').count(),
                'errors': logs.filter(log_type='error').count(),
            }
        except Exception as e:
            # If logs table doesn't exist or there's an error, continue without logs
            logs = []
            log_stats = {
                'total_logs': 0,
                'api_calls': 0,
                'status_changes': 0,
                'errors': 0,
            }
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not fetch logs for order {order_id}: {str(e)}")
        
        context = {
            'order': order,
            'logs': logs,
            'log_stats': log_stats,
        }
        
        # Return partial template for AJAX request
        return render(request, 'panel/admin/partials/order_details_content.html', context)
        
    except Exception as e:
        # Return error response
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading order details for order {order_id}: {str(e)}")
        
        return HttpResponse(
            f'<div class="text-center py-12">'
            f'<svg class="w-16 h-16 mx-auto mb-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
            f'<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>'
            f'</svg>'
            f'<p class="text-red-400">Error loading order details</p>'
            f'<p class="text-gray-400 text-sm mt-2">{str(e)}</p>'
            f'</div>',
            status=500
        )

# Admin Dripfeed Management
@login_required
@admin_required
def admin_dripfeed(request):
    dripfeed_orders = Order.objects.select_related('service', 'user').filter(drip_feed=True).order_by('-created_at')
    
    context = {
        'dripfeed_orders': dripfeed_orders,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/dripfeed.html', context)

# Admin Subscriptions Management
@login_required
@admin_required
def admin_subscriptions(request):
    subscriptions = UserSubscription.objects.all().order_by('-created_at')
    active_count = subscriptions.filter(is_active=True).count()
    
    context = {
        'subscriptions': subscriptions,
        'active_count': active_count,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/subscriptions.html', context)

# Admin Cancel Orders
@login_required
@admin_required
def admin_cancel(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        reason = request.POST.get('reason', '')
        
        try:
            order = Order.objects.get(id=order_id)
            order.status = 'Canceled'
            order.save()
            messages.success(request, f'Order {order.order_id} has been canceled')
        except Order.DoesNotExist:
            messages.error(request, 'Order not found')
    
    canceled_orders = Order.objects.select_related('service', 'user').filter(status='Canceled').order_by('-updated_at')
    
    context = {
        'canceled_orders': canceled_orders,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/cancel.html', context)

# Admin Services Management
@login_required
@admin_required
def admin_services(request):
    services = Service.objects.all().select_related('category', 'category__social_network').order_by('category', 'name')
    categories = ServiceCategory.objects.all().order_by('order')
    social_networks = SocialNetwork.objects.all().order_by('display_order', 'name')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        services = services.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(category__name__icontains=search) |
            Q(external_service_id__icontains=search)
        )
    
    # Social Network filter (filters by category's social network)
    social_network_filter = request.GET.get('social_network', '')
    if social_network_filter:
        services = services.filter(category__social_network_id=social_network_filter)
    
    # Category filter (still available)
    category_filter = request.GET.get('category', '')
    if category_filter:
        services = services.filter(category_id=category_filter)
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        services = services.filter(is_active=True)
    elif status_filter == 'inactive':
        services = services.filter(is_active=False)
    
    # Supplier filter
    supplier_filter = request.GET.get('supplier', '')
    if supplier_filter:
        services = services.filter(supplier_api=supplier_filter)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        service_id = request.POST.get('service_id')
        
        try:
            service = Service.objects.get(id=service_id)
            if action == 'toggle_active':
                service.is_active = not service.is_active
                service.save()
                messages.success(request, f'Service {service.name} status updated')
            elif action == 'delete':
                service.delete()
                messages.success(request, f'Service {service.name} deleted')
        except Service.DoesNotExist:
            messages.error(request, 'Service not found')
        
        # Preserve query parameters when redirecting (including per_page)
        query_params = request.GET.urlencode()
        redirect_url = 'admin_services'
        if query_params:
            redirect_url += '?' + query_params
        return redirect(redirect_url)
    
    # Pagination - Get per_page from request, validate and set default
    per_page = request.GET.get('per_page', '25')
    valid_per_page_options = ['10', '25', '50', '100', '200']
    if per_page not in valid_per_page_options:
        per_page = '50'
    per_page_int = int(per_page)
    
    paginator = Paginator(services, per_page_int)
    page = request.GET.get('page', 1)
    
    try:
        services_page = paginator.page(page)
    except PageNotAnInteger:
        services_page = paginator.page(1)
    except EmptyPage:
        services_page = paginator.page(paginator.num_pages)
    
    context = {
        'services': services_page,
        'categories': categories,
        'social_networks': social_networks,
        'search': search,
        'category_filter': category_filter,
        'social_network_filter': social_network_filter,
        'status_filter': status_filter,
        'supplier_filter': supplier_filter,
        'per_page': per_page,
        'per_page_options': valid_per_page_options,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/services.html', context)

def sync_services_from_supplier(request):
    """Sync services from JAP API"""
    from .settings_utils import get_setting
    from django.conf import settings
    from decimal import Decimal, InvalidOperation
    
    # JAP API configuration
    jap_url = get_setting('supplier_jap_url', 'https://justanotherpanel.com/api/v2')
    jap_key = get_setting('supplier_jap_key', getattr(settings, 'JAP_API_KEY', ''))
    
    if not jap_key:
        messages.error(request, 'JAP API key not configured. Please set it in admin settings.')
        return redirect('admin_services')
    
    try:
        # Fetch services from JAP API
        payload = {
            'key': jap_key,
            'action': 'services',
        }
        
        timeout = int(get_setting('supplier_timeout', '30'))
        response = requests.post(jap_url, data=payload, timeout=timeout)
        
        if response.status_code != 200:
            messages.error(request, f'Failed to fetch services from JAP API: HTTP {response.status_code}')
            return redirect('admin_services')
        
        data = response.json()
        
        # Handle different response formats
        if isinstance(data, dict):
            if 'error' in data:
                messages.error(request, f'API Error: {data.get("error", "Unknown error")}')
                return redirect('admin_services')
            # Some APIs return services in a 'data' or 'services' key
            services_data = data.get('data', data.get('services', []))
        elif isinstance(data, list):
            services_data = data
        else:
            messages.error(request, f'Unexpected response format from JAP API')
            return redirect('admin_services')
        
        if not services_data:
            messages.warning(request, f'No services found from JAP API')
            return redirect('admin_services')
        
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
        
        # Get or create default category
        default_category, _ = ServiceCategory.objects.get_or_create(
            name='Other',
            defaults={'is_active': True, 'order': 999}
        )
        
        synced_count = 0
        updated_count = 0
        created_count = 0
        
        for service_data in services_data:
            try:
                # Extract service information (handle different API formats)
                # JAP API typically returns service ID as 'service' field (integer or string)
                service_id_raw = service_data.get('service') or service_data.get('id')
                if service_id_raw is None:
                    # Skip if no service ID found
                    continue
                service_id = str(service_id_raw)
                
                name = service_data.get('name', service_data.get('service', 'Unknown Service'))
                if not name or name == 'Unknown Service':
                    # Try to get name from other fields
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
                    # If not found, try to find by name and supplier (in case external_service_id wasn't set before)
                    try:
                        service = Service.objects.get(name=name, supplier_api='jap')
                        # Update external_service_id if it was missing
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
                    service.external_service_id = service_id  # Ensure it's set
                    service.save()
                    updated_count += 1
                else:
                    service.save()
                    created_count += 1
                
                synced_count += 1
                
            except Exception as e:
                # Log error but continue with other services
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Error syncing service {service_data}: {str(e)}')
                continue
        
        messages.success(
            request, 
            f'Successfully synced {synced_count} services from JAP API: '
            f'{created_count} created, {updated_count} updated'
        )
        
    except requests.exceptions.RequestException as e:
        messages.error(request, f'Network error connecting to JAP API: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error syncing services: {str(e)}')
        import logging
        logger = logging.getLogger(__name__)
        logger.exception('Service sync error')
    
    return redirect('admin_services')

# Admin Transaction Logs
@login_required
@admin_required
def admin_transactions(request):
    transactions = Payment.objects.all().select_related('user')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        transactions = transactions.filter(
            Q(transaction_id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(gateway_payment_id__icontains=search)
        )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    
    # Sort functionality
    sort_by = request.GET.get('sort', '-created_at')
    valid_sort_fields = ['created_at', '-created_at', 'amount', '-amount', 'transaction_id', '-transaction_id', 'user__username', '-user__username']
    if sort_by not in valid_sort_fields:
        sort_by = '-created_at'
    transactions = transactions.order_by(sort_by)
    
    # Pagination - Get per_page from request, validate and set default
    per_page = request.GET.get('per_page', '25')
    valid_per_page_options = ['10', '25', '50', '100', '200']
    if per_page not in valid_per_page_options:
        per_page = '25'
    per_page_int = int(per_page)
    
    paginator = Paginator(transactions, per_page_int)
    page = request.GET.get('page', 1)
    
    try:
        transactions_page = paginator.page(page)
    except PageNotAnInteger:
        transactions_page = paginator.page(1)
    except EmptyPage:
        transactions_page = paginator.page(paginator.num_pages)
    
    context = {
        'transactions': transactions_page,
        'status_filter': status_filter,
        'search': search,
        'sort_by': sort_by,
        'per_page': per_page,
        'per_page_options': valid_per_page_options,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/transactions.html', context)

# Admin Transaction Logs Export
@login_required
@admin_required
def admin_transactions_export(request):
    transactions = Payment.objects.all().select_related('user')
    
    # Apply same filters as main view
    search = request.GET.get('search', '')
    if search:
        transactions = transactions.filter(
            Q(transaction_id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(gateway_payment_id__icontains=search)
        )
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    
    # Sort
    sort_by = request.GET.get('sort', '-created_at')
    valid_sort_fields = ['created_at', '-created_at', 'amount', '-amount', 'transaction_id', '-transaction_id', 'user__username', '-user__username']
    if sort_by not in valid_sort_fields:
        sort_by = '-created_at'
    transactions = transactions.order_by(sort_by)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Transaction ID', 'User', 'Email', 'Amount', 'Method', 'Status', 'Created At', 'Completed At', 'Gateway Payment ID'])
    
    for transaction in transactions:
        writer.writerow([
            transaction.transaction_id,
            transaction.user.username,
            transaction.user.email,
            f"${transaction.amount:.2f}",
            transaction.get_method_display(),
            transaction.get_status_display(),
            transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            transaction.completed_at.strftime('%Y-%m-%d %H:%M:%S') if transaction.completed_at else '',
            transaction.gateway_payment_id or '',
        ])
    
    return response

# Admin Categories Management
@login_required
@admin_required
def admin_categories(request):
    categories = ServiceCategory.objects.all().order_by('order')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        categories = categories.filter(
            Q(name__icontains=search) |
            Q(name_km__icontains=search)
        )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        categories = categories.filter(is_active=True)
    elif status_filter == 'inactive':
        categories = categories.filter(is_active=False)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            name = request.POST.get('name')
            name_km = request.POST.get('name_km', '')
            order = int(request.POST.get('order', 0))
            social_network_id = request.POST.get('social_network_id')
            
            category = ServiceCategory(name=name, name_km=name_km, order=order)
            if social_network_id:
                try:
                    category.social_network_id = int(social_network_id)
                except (ValueError, TypeError):
                    pass
            category.save()
            messages.success(request, 'Category created successfully')
        elif action == 'update':
            category_id = request.POST.get('category_id')
            try:
                category = ServiceCategory.objects.get(id=category_id)
                category.name = request.POST.get('name')
                category.name_km = request.POST.get('name_km', '')
                category.order = int(request.POST.get('order', 0))
                category.is_active = request.POST.get('is_active') == 'on'
                
                social_network_id = request.POST.get('social_network_id')
                if social_network_id:
                    try:
                        category.social_network_id = int(social_network_id)
                    except (ValueError, TypeError):
                        category.social_network = None
                else:
                    category.social_network = None
                    
                category.save()
                messages.success(request, 'Category updated successfully')
            except ServiceCategory.DoesNotExist:
                messages.error(request, 'Category not found')
        elif action == 'delete':
            category_id = request.POST.get('category_id')
            try:
                category = ServiceCategory.objects.get(id=category_id)
                category.delete()
                messages.success(request, 'Category deleted successfully')
            except ServiceCategory.DoesNotExist:
                messages.error(request, 'Category not found')
        
        # Preserve query parameters when redirecting
        query_params = request.GET.urlencode()
        redirect_url = 'admin_categories'
        if query_params:
            redirect_url += '?' + query_params
        return redirect(redirect_url)
    
    # Pagination - Get per_page from request, validate and set default
    per_page = request.GET.get('per_page', '25')
    valid_per_page_options = ['10', '25', '50', '100', '200']
    if per_page not in valid_per_page_options:
        per_page = '25'
    per_page_int = int(per_page)
    
    paginator = Paginator(categories, per_page_int)
    page = request.GET.get('page', 1)
    
    try:
        categories_page = paginator.page(page)
    except PageNotAnInteger:
        categories_page = paginator.page(1)
    except EmptyPage:
        categories_page = paginator.page(paginator.num_pages)
    
    context = {
        'categories': categories_page,
        'social_networks': SocialNetwork.objects.all().order_by('display_order', 'name'),
        'search': search,
        'status_filter': status_filter,
        'per_page': per_page,
        'per_page_options': valid_per_page_options,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/categories.html', context)

# Admin Social Networks Management
@login_required
@admin_required
def admin_social_networks(request):
    social_networks = SocialNetwork.objects.all()
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        social_networks = social_networks.filter(
            Q(name__icontains=search) |
            Q(name_km__icontains=search) |
            Q(platform_code__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        social_networks = social_networks.filter(status=status_filter)
    
    # Active filter
    active_filter = request.GET.get('active', '')
    if active_filter == 'true':
        social_networks = social_networks.filter(is_active=True)
    elif active_filter == 'false':
        social_networks = social_networks.filter(is_active=False)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            platform_code = request.POST.get('platform_code')
            name = request.POST.get('name')
            name_km = request.POST.get('name_km', '')
            description = request.POST.get('description', '')
            description_km = request.POST.get('description_km', '')
            icon = request.POST.get('icon', '')
            color = request.POST.get('color', '#000000')
            status = request.POST.get('status', 'active')
            is_active = request.POST.get('is_active') == 'on'
            is_featured = request.POST.get('is_featured') == 'on'
            display_order = int(request.POST.get('display_order', 0))
            website_url = request.POST.get('website_url', '')
            documentation_url = request.POST.get('documentation_url', '')
            
            # Check if platform_code already exists
            if SocialNetwork.objects.filter(platform_code=platform_code).exists():
                messages.error(request, f'Social network with platform code "{platform_code}" already exists')
            else:
                social_network = SocialNetwork.objects.create(
                    platform_code=platform_code,
                    name=name,
                    name_km=name_km,
                    description=description,
                    description_km=description_km,
                    icon=icon,
                    color=color,
                    status=status,
                    is_active=is_active,
                    is_featured=is_featured,
                    display_order=display_order,
                    website_url=website_url,
                    documentation_url=documentation_url
                )
                
                # Handle file uploads
                if 'icon_image' in request.FILES:
                    social_network.icon_image = request.FILES['icon_image']
                if 'logo' in request.FILES:
                    social_network.logo = request.FILES['logo']
                social_network.save()
                
                messages.success(request, 'Social network created successfully')
        elif action == 'update':
            network_id = request.POST.get('network_id')
            try:
                social_network = SocialNetwork.objects.get(id=network_id)
                social_network.name = request.POST.get('name')
                social_network.name_km = request.POST.get('name_km', '')
                social_network.description = request.POST.get('description', '')
                social_network.description_km = request.POST.get('description_km', '')
                social_network.icon = request.POST.get('icon', '')
                social_network.color = request.POST.get('color', '#000000')
                social_network.status = request.POST.get('status', 'active')
                social_network.is_active = request.POST.get('is_active') == 'on'
                social_network.is_featured = request.POST.get('is_featured') == 'on'
                social_network.display_order = int(request.POST.get('display_order', 0))
                social_network.website_url = request.POST.get('website_url', '')
                social_network.documentation_url = request.POST.get('documentation_url', '')
                
                # Handle file uploads
                if 'icon_image' in request.FILES:
                    social_network.icon_image = request.FILES['icon_image']
                if 'logo' in request.FILES:
                    social_network.logo = request.FILES['logo']
                
                social_network.save()
                messages.success(request, 'Social network updated successfully')
            except SocialNetwork.DoesNotExist:
                messages.error(request, 'Social network not found')
        elif action == 'delete':
            network_id = request.POST.get('network_id')
            try:
                social_network = SocialNetwork.objects.get(id=network_id)
                social_network.delete()
                messages.success(request, 'Social network deleted successfully')
            except SocialNetwork.DoesNotExist:
                messages.error(request, 'Social network not found')
        
        # Preserve query parameters when redirecting
        query_params = request.GET.urlencode()
        redirect_url = 'admin_social_networks'
        if query_params:
            redirect_url += '?' + query_params
        return redirect(redirect_url)
    
    # Sort by display_order, then name
    social_networks = social_networks.order_by('display_order', 'name')
    
    # Pagination
    per_page = request.GET.get('per_page', '25')
    valid_per_page_options = ['10', '25', '50', '100', '200']
    if per_page not in valid_per_page_options:
        per_page = '25'
    per_page_int = int(per_page)
    
    paginator = Paginator(social_networks, per_page_int)
    page = request.GET.get('page', 1)
    
    try:
        networks_page = paginator.page(page)
    except PageNotAnInteger:
        networks_page = paginator.page(1)
    except EmptyPage:
        networks_page = paginator.page(paginator.num_pages)
    
    context = {
        'social_networks': networks_page,
        'search': search,
        'status_filter': status_filter,
        'active_filter': active_filter,
        'per_page': per_page,
        'per_page_options': valid_per_page_options,
        'platform_choices': SocialNetwork.PLATFORM_CHOICES,
        'status_choices': SocialNetwork.STATUS_CHOICES,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/social_networks.html', context)

# Admin Settings Management
@login_required
@admin_required
def admin_settings(request):
    group_filter = request.GET.get('group', '')
    settings = SystemSetting.objects.all()
    
    if group_filter:
        settings = settings.filter(group=group_filter)
    
    settings = settings.order_by('group', 'order', 'key')
    
    # Group settings by category
    grouped_settings = {}
    for setting in settings:
        if setting.group not in grouped_settings:
            grouped_settings[setting.group] = []
        grouped_settings[setting.group].append(setting)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update':
            # Update multiple settings
            updated_count = 0
            for setting in settings:
                field_name = f'setting_{setting.id}'
                
                # Handle file uploads for images
                if setting.setting_type == 'image':
                    file_field_name = f'image_{setting.id}'
                    if file_field_name in request.FILES:
                        uploaded_file = request.FILES[file_field_name]
                        # Save file to media/settings/ directory
                        upload_path = os.path.join('settings', uploaded_file.name)
                        full_path = os.path.join(django_settings.MEDIA_ROOT, upload_path)
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)
                        
                        with open(full_path, 'wb+') as destination:
                            for chunk in uploaded_file.chunks():
                                destination.write(chunk)
                        
                        # Store relative path in setting value
                        setting.value = upload_path
                        setting.updated_by = request.user
                        setting.save()
                        updated_count += 1
                    elif field_name in request.POST:
                        # Allow text input for image URL/path
                        new_value = request.POST.get(field_name, '')
                        if new_value != setting.value:
                            setting.value = new_value
                            setting.updated_by = request.user
                            setting.save()
                            updated_count += 1
                
                elif setting.setting_type == 'image_list':
                    # Handle multiple image uploads
                    file_field_name = f'images_{setting.id}'
                    if file_field_name in request.FILES:
                        uploaded_files = request.FILES.getlist(file_field_name)
                        image_paths = []
                        
                        for uploaded_file in uploaded_files:
                            upload_path = os.path.join('settings', uploaded_file.name)
                            full_path = os.path.join(django_settings.MEDIA_ROOT, upload_path)
                            os.makedirs(os.path.dirname(full_path), exist_ok=True)
                            
                            with open(full_path, 'wb+') as destination:
                                for chunk in uploaded_file.chunks():
                                    destination.write(chunk)
                            
                            image_paths.append(upload_path)
                        
                        # Store as JSON array
                        if image_paths:
                            # Merge with existing images if any
                            existing_images = []
                            if setting.value:
                                try:
                                    existing_images = json.loads(setting.value)
                                except:
                                    pass
                            existing_images.extend(image_paths)
                            setting.value = json.dumps(existing_images)
                            setting.updated_by = request.user
                            setting.save()
                            updated_count += 1
                    
                    # Handle removal of images
                    remove_field_name = f'remove_images_{setting.id}'
                    if remove_field_name in request.POST:
                        remove_indices = request.POST.getlist(remove_field_name)
                        if setting.value:
                            try:
                                image_list = json.loads(setting.value)
                                # Remove images by index (in reverse to maintain indices)
                                for idx in sorted([int(i) for i in remove_indices], reverse=True):
                                    if 0 <= idx < len(image_list):
                                        # Optionally delete the file
                                        old_path = os.path.join(django_settings.MEDIA_ROOT, image_list[idx])
                                        if os.path.exists(old_path):
                                            os.remove(old_path)
                                        image_list.pop(idx)
                                setting.value = json.dumps(image_list) if image_list else ''
                                setting.updated_by = request.user
                                setting.save()
                                updated_count += 1
                            except:
                                pass
                
                elif field_name in request.POST:
                    new_value = request.POST.get(field_name, '')
                    
                    # Handle boolean values
                    if setting.setting_type == 'boolean':
                        new_value = 'true' if new_value == 'on' or new_value == 'true' else 'false'
                    
                    if new_value != setting.value:
                        setting.value = new_value
                        setting.updated_by = request.user
                        setting.save()
                        updated_count += 1
            
            if updated_count > 0:
                messages.success(request, f'{updated_count} setting(s) updated successfully')
            else:
                messages.info(request, 'No changes detected')
            
            url = reverse('admin_settings')
            if group_filter:
                url += f'?group={group_filter}'
            return redirect(url)
        
        elif action == 'create':
            key = request.POST.get('key', '').strip()
            label = request.POST.get('label', '').strip()
            setting_type = request.POST.get('setting_type', 'text')
            group = request.POST.get('group', 'general')
            default_value = request.POST.get('default_value', '')
            description = request.POST.get('description', '')
            order = int(request.POST.get('order', 0))
            is_public = request.POST.get('is_public') == 'on'
            is_encrypted = request.POST.get('is_encrypted') == 'on'
            
            if not key or not label:
                messages.error(request, 'Key and label are required')
            elif SystemSetting.objects.filter(key=key).exists():
                messages.error(request, f'Setting with key "{key}" already exists')
            else:
                SystemSetting.objects.create(
                    key=key,
                    label=label,
                    setting_type=setting_type,
                    group=group,
                    default_value=default_value,
                    value=default_value,
                    description=description,
                    order=order,
                    is_public=is_public,
                    is_encrypted=is_encrypted,
                    updated_by=request.user
                )
                messages.success(request, 'Setting created successfully')
            
            url = reverse('admin_settings')
            if group_filter:
                url += f'?group={group_filter}'
            return redirect(url)
        
        elif action == 'delete':
            setting_id = request.POST.get('setting_id')
            try:
                setting = SystemSetting.objects.get(id=setting_id)
                setting.delete()
                messages.success(request, 'Setting deleted successfully')
            except SystemSetting.DoesNotExist:
                messages.error(request, 'Setting not found')
            
            url = reverse('admin_settings')
            if group_filter:
                url += f'?group={group_filter}'
            return redirect(url)
    
    # Parse image lists for template rendering
    for group, settings_list in grouped_settings.items():
        for setting in settings_list:
            if setting.setting_type == 'image_list':
                setting.image_list = setting.get_image_list()
            else:
                setting.image_list = []
    
    context = {
        'grouped_settings': grouped_settings,
        'group_filter': group_filter,
        'setting_groups': SystemSetting.SETTING_GROUPS,
        'setting_types': SystemSetting.SETTING_TYPES,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/settings.html', context)

# Toggle Maintenance Mode (AJAX)
@login_required
@admin_required
@require_http_methods(["POST"])
def toggle_maintenance_mode(request):
    """
    Toggle maintenance mode on/off via AJAX
    """
    from .settings_utils import get_setting_bool, set_setting
    
    current_status = get_setting_bool('maintenance_mode', default=False)
    new_status = not current_status
    
    set_setting('maintenance_mode', 'true' if new_status else 'false', user=request.user)
    
    return JsonResponse({
        'success': True,
        'maintenance_mode': new_status,
        'message': 'Maintenance mode ' + ('enabled' if new_status else 'disabled')
    })

# Admin Tickets Management
@login_required
@admin_required
def admin_tickets(request):
    status_filter = request.GET.get('status', '')
    tickets = Ticket.objects.all()
    
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    
    tickets = tickets.order_by('-created_at')
    
    context = {
        'tickets': tickets,
        'status_filter': status_filter,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/tickets.html', context)

# Admin Users Management
@login_required
@admin_required
def admin_users(request):
    from django.contrib.auth.models import Group
    
    search = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    
    users = User.objects.all().prefetch_related('groups', 'profile')
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search)
        )
    
    if role_filter:
        users = users.filter(profile__role=role_filter)
    
    users = users.order_by('-date_joined')
    
    # Pagination - Get per_page from request, validate and set default
    per_page = request.GET.get('per_page', '25')
    valid_per_page_options = ['10', '25', '50', '100', '200']
    if per_page not in valid_per_page_options:
        per_page = '25'
    per_page_int = int(per_page)
    
    paginator = Paginator(users, per_page_int)
    page = request.GET.get('page', 1)
    
    try:
        users_page = paginator.page(page)
    except PageNotAnInteger:
        users_page = paginator.page(1)
    except EmptyPage:
        users_page = paginator.page(paginator.num_pages)
    
    # Get all groups for the modal
    all_groups = Group.objects.all().prefetch_related('permissions')
    
    context = {
        'users': users_page,
        'all_groups': all_groups,
        'search': search,
        'role_filter': role_filter,
        'per_page': per_page,
        'per_page_options': valid_per_page_options,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/users.html', context)

# Admin Create User (AJAX endpoint)
@login_required
@admin_required
def admin_create_user(request):
    from django.contrib.auth.models import Group
    
    if request.method == 'POST':
        try:
            # Get form data
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()
            password_confirm = request.POST.get('password_confirm', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            role = request.POST.get('role', 'user').strip()
            balance = request.POST.get('balance', '').strip()
            is_active = request.POST.get('is_active') == 'true'
            selected_groups = request.POST.getlist('groups')
            
            # Validation
            if not username or not email or not password:
                return JsonResponse({'status': 'error', 'message': 'Username, email, and password are required'}, status=400)
            
            if len(username) < 3:
                return JsonResponse({'status': 'error', 'message': 'Username must be at least 3 characters'}, status=400)
            
            if len(password) < 8:
                return JsonResponse({'status': 'error', 'message': 'Password must be at least 8 characters'}, status=400)
            
            if password != password_confirm:
                return JsonResponse({'status': 'error', 'message': 'Passwords do not match'}, status=400)
            
            # Check if username/email already exists
            if User.objects.filter(username=username).exists():
                return JsonResponse({'status': 'error', 'message': 'Username already exists'}, status=400)
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'Email already exists'}, status=400)
            
            # Validate email format
            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse({'status': 'error', 'message': 'Invalid email format'}, status=400)
            
            # Validate role
            if role not in ['admin', 'reseller', 'user']:
                role = 'user'
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=is_active
            )
            
            # Ensure profile is created and set role
            profile = ensure_user_profile(user)
            profile.role = role
            
            # Set initial balance if provided
            try:
                if balance:
                    profile.balance = float(balance)
            except (ValueError, TypeError):
                pass
            
            profile.save()
            
            # Assign groups if provided
            if selected_groups:
                selected_group_ids = [int(gid) for gid in selected_groups if gid.isdigit()]
                groups = Group.objects.filter(id__in=selected_group_ids)
                user.groups.set(groups)
            
            return JsonResponse({
                'status': 'success',
                'message': f'User {user.username} created successfully',
                'user_id': user.id
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

# Admin Edit User (AJAX endpoint)
@login_required
@admin_required
def admin_edit_user(request, user_id):
    from django.contrib.auth.models import Group
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'GET':
        # Ensure user has a profile
        profile = ensure_user_profile(user)
        
        # Return user data as JSON
        user_groups = list(user.groups.values_list('id', flat=True))
        return JsonResponse({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_superuser': user.is_superuser,
            'role': profile.role,
            'balance': str(profile.balance),
            'total_spent': str(profile.total_spent),
            'groups': user_groups,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
        })
    
    elif request.method == 'POST':
        # Update user data
        try:
            # Get form data
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            role = request.POST.get('role', '').strip()
            balance = request.POST.get('balance', '').strip()
            total_spent = request.POST.get('total_spent', '').strip()
            is_active = request.POST.get('is_active') == 'true'
            selected_groups = request.POST.getlist('groups')
            
            # Validation
            if not username or not email:
                return JsonResponse({'status': 'error', 'message': 'Username and email are required'}, status=400)
            
            # Check if username/email already exists (excluding current user)
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                return JsonResponse({'status': 'error', 'message': 'Username already exists'}, status=400)
            
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return JsonResponse({'status': 'error', 'message': 'Email already exists'}, status=400)
            
            # Validate email format
            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse({'status': 'error', 'message': 'Invalid email format'}, status=400)
            
            # Prevent admin from removing their own admin role
            if user.id == request.user.id and role != 'admin':
                return JsonResponse({'status': 'error', 'message': 'You cannot remove your own admin role'}, status=400)
            
            # Update user fields
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = is_active
            user.save()
            
            # Ensure user has a profile and update it
            profile = ensure_user_profile(user)
            if role in ['admin', 'reseller', 'user']:
                profile.role = role
            
            try:
                if balance:
                    profile.balance = float(balance)
            except (ValueError, TypeError):
                pass
            
            try:
                if total_spent:
                    profile.total_spent = float(total_spent)
            except (ValueError, TypeError):
                pass
            
            profile.save()
            
            # Update groups
            if selected_groups:
                selected_group_ids = [int(gid) for gid in selected_groups if gid.isdigit()]
                groups = Group.objects.filter(id__in=selected_group_ids)
                user.groups.set(groups)
            else:
                user.groups.clear()
            
            return JsonResponse({
                'status': 'success',
                'message': f'User {user.username} updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

# Admin Edit User Role
@login_required
@admin_required
@require_http_methods(["POST"])
def admin_edit_user_role(request, user_id):
    user = get_object_or_404(User, id=user_id)
    new_role = request.POST.get('role', '').strip()
    
    if new_role not in ['admin', 'reseller', 'user']:
        messages.error(request, 'Invalid role selected')
        return redirect('admin_users')
    
    # Prevent admin from removing their own admin role
    if user.id == request.user.id and new_role != 'admin':
        messages.error(request, 'You cannot remove your own admin role')
        return redirect('admin_users')
    
    try:
        user.profile.role = new_role
        user.profile.save()
        messages.success(request, f'Role updated successfully for {user.username}')
    except Exception as e:
        messages.error(request, f'Error updating role: {str(e)}')
    
    return redirect('admin_users')

# Admin User Groups Management
@login_required
@admin_required
def admin_user_groups(request):
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType
    
    groups = Group.objects.all().prefetch_related('permissions', 'user_set')
    search = request.GET.get('search', '')
    
    if search:
        groups = groups.filter(name__icontains=search)
    
    # Get all permissions organized by content type for the modal
    all_permissions = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'content_type__model', 'codename')
    permissions_by_app = {}
    for perm in all_permissions:
        app_label = perm.content_type.app_label
        if app_label not in permissions_by_app:
            permissions_by_app[app_label] = {}
        model_name = perm.content_type.model
        if model_name not in permissions_by_app[app_label]:
            permissions_by_app[app_label][model_name] = []
        permissions_by_app[app_label][model_name].append({
            'id': perm.id,
            'name': perm.name,
            'codename': perm.codename,
        })
    
    context = {
        'groups': groups,
        'search': search,
        'permissions_by_app': permissions_by_app,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/user_groups.html', context)

# Admin Create Group (AJAX endpoint)
@login_required
@admin_required
def admin_create_group(request):
    from django.contrib.auth.models import Group, Permission
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            selected_permissions = request.POST.getlist('permissions')
            
            if not name:
                return JsonResponse({'status': 'error', 'message': 'Group name is required'}, status=400)
            
            # Check if group name already exists
            if Group.objects.filter(name=name).exists():
                return JsonResponse({'status': 'error', 'message': 'Group name already exists'}, status=400)
            
            # Create group
            group = Group.objects.create(name=name)
            
            # Assign permissions if provided
            if selected_permissions:
                permission_ids = [int(pid) for pid in selected_permissions if pid.isdigit()]
                permissions = Permission.objects.filter(id__in=permission_ids)
                group.permissions.set(permissions)
            
            return JsonResponse({
                'status': 'success',
                'message': f'Group "{group.name}" created successfully',
                'group_id': group.id
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

# Admin Edit Group (AJAX endpoint)
@login_required
@admin_required
def admin_edit_group(request, group_id):
    from django.contrib.auth.models import Group, Permission
    
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'GET':
        # Return group data as JSON
        group_permissions = list(group.permissions.values_list('id', flat=True))
        return JsonResponse({
            'id': group.id,
            'name': group.name,
            'permissions': group_permissions,
            'user_count': group.user_set.count(),
        })
    
    elif request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            selected_permissions = request.POST.getlist('permissions')
            
            if not name:
                return JsonResponse({'status': 'error', 'message': 'Group name is required'}, status=400)
            
            # Check if group name already exists (excluding current group)
            if Group.objects.filter(name=name).exclude(id=group.id).exists():
                return JsonResponse({'status': 'error', 'message': 'Group name already exists'}, status=400)
            
            # Update group name
            group.name = name
            group.save()
            
            # Update permissions
            if selected_permissions:
                permission_ids = [int(pid) for pid in selected_permissions if pid.isdigit()]
                permissions = Permission.objects.filter(id__in=permission_ids)
                group.permissions.set(permissions)
            else:
                group.permissions.clear()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Group "{group.name}" updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

# Admin Delete Group (AJAX endpoint)
@login_required
@admin_required
@require_http_methods(["POST"])
def admin_delete_group(request, group_id):
    from django.contrib.auth.models import Group
    
    group = get_object_or_404(Group, id=group_id)
    group_name = group.name
    
    try:
        # Check if group has users
        user_count = group.user_set.count()
        if user_count > 0:
            return JsonResponse({
                'status': 'error',
                'message': f'Cannot delete group. It has {user_count} user(s) assigned. Please remove users first.'
            }, status=400)
        
        group.delete()
        return JsonResponse({
            'status': 'success',
            'message': f'Group "{group_name}" deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# Admin Assign User to Group
@login_required
@admin_required
@require_http_methods(["POST"])
def admin_assign_user_group(request, user_id):
    from django.contrib.auth.models import Group
    
    user = get_object_or_404(User, id=user_id)
    action = request.POST.get('action', 'update')
    
    try:
        if action == 'update':
            # Get selected groups from checkbox inputs
            selected_group_ids = request.POST.getlist('groups')
            selected_groups = Group.objects.filter(id__in=selected_group_ids)
            
            # Update user's groups
            user.groups.set(selected_groups)
            messages.success(request, f'Groups updated successfully for {user.username}')
        else:
            messages.error(request, 'Invalid action')
    except Exception as e:
        messages.error(request, f'Error updating groups: {str(e)}')
    
    return redirect('admin_users')

# Admin Subscribers Management
@login_required
@admin_required
def admin_subscribers(request):
    from django.db.models import Count
    subscribers = User.objects.annotate(
        subscription_count=Count('subscriptions'),
        active_subscription_count=Count('subscriptions', filter=Q(subscriptions__is_active=True))
    ).filter(subscription_count__gt=0)
    
    context = {
        'subscribers': subscribers,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/subscribers.html', context)

# Admin User Activity Log (placeholder - would need ActivityLog model)
@login_required
@admin_required
def admin_user_activity(request):
    # This would typically use an ActivityLog model
    # For now, we'll show recent orders and tickets as activity
    recent_orders = Order.objects.order_by('-created_at')[:50]
    recent_tickets = Ticket.objects.order_by('-created_at')[:50]
    
    context = {
        'recent_orders': recent_orders,
        'recent_tickets': recent_tickets,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/user_activity.html', context)

# Admin Blacklist IP
@login_required
@admin_required
def admin_blacklist_ip(request):
    blacklist_ips = BlacklistIP.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            ip_address = request.POST.get('ip_address')
            reason = request.POST.get('reason', '')
            BlacklistIP.objects.create(
                ip_address=ip_address,
                reason=reason,
                created_by=request.user
            )
            messages.success(request, f'IP {ip_address} added to blacklist')
        elif action == 'delete':
            ip_id = request.POST.get('ip_id')
            try:
                blacklist_ip = BlacklistIP.objects.get(id=ip_id)
                blacklist_ip.delete()
                messages.success(request, 'IP removed from blacklist')
            except BlacklistIP.DoesNotExist:
                messages.error(request, 'IP not found')
        elif action == 'toggle':
            ip_id = request.POST.get('ip_id')
            try:
                blacklist_ip = BlacklistIP.objects.get(id=ip_id)
                blacklist_ip.is_active = not blacklist_ip.is_active
                blacklist_ip.save()
                messages.success(request, 'IP status updated')
            except BlacklistIP.DoesNotExist:
                messages.error(request, 'IP not found')
        
        return redirect('admin_blacklist_ip')
    
    context = {
        'blacklist_ips': blacklist_ips,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/blacklist_ip.html', context)

# Admin Blacklist Link
@login_required
@admin_required
def admin_blacklist_link(request):
    blacklist_links = BlacklistLink.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            link = request.POST.get('link')
            reason = request.POST.get('reason', '')
            BlacklistLink.objects.create(
                link=link,
                reason=reason,
                created_by=request.user
            )
            messages.success(request, 'Link added to blacklist')
        elif action == 'delete':
            link_id = request.POST.get('link_id')
            try:
                blacklist_link = BlacklistLink.objects.get(id=link_id)
                blacklist_link.delete()
                messages.success(request, 'Link removed from blacklist')
            except BlacklistLink.DoesNotExist:
                messages.error(request, 'Link not found')
        elif action == 'toggle':
            link_id = request.POST.get('link_id')
            try:
                blacklist_link = BlacklistLink.objects.get(id=link_id)
                blacklist_link.is_active = not blacklist_link.is_active
                blacklist_link.save()
                messages.success(request, 'Link status updated')
            except BlacklistLink.DoesNotExist:
                messages.error(request, 'Link not found')
        
        return redirect('admin_blacklist_link')
    
    context = {
        'blacklist_links': blacklist_links,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/blacklist_link.html', context)

# Admin Blacklist Email
@login_required
@admin_required
def admin_blacklist_email(request):
    blacklist_emails = BlacklistEmail.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            email = request.POST.get('email')
            reason = request.POST.get('reason', '')
            BlacklistEmail.objects.create(
                email=email,
                reason=reason,
                created_by=request.user
            )
            messages.success(request, f'Email {email} added to blacklist')
        elif action == 'delete':
            email_id = request.POST.get('email_id')
            try:
                blacklist_email = BlacklistEmail.objects.get(id=email_id)
                blacklist_email.delete()
                messages.success(request, 'Email removed from blacklist')
            except BlacklistEmail.DoesNotExist:
                messages.error(request, 'Email not found')
        elif action == 'toggle':
            email_id = request.POST.get('email_id')
            try:
                blacklist_email = BlacklistEmail.objects.get(id=email_id)
                blacklist_email.is_active = not blacklist_email.is_active
                blacklist_email.save()
                messages.success(request, 'Email status updated')
            except BlacklistEmail.DoesNotExist:
                messages.error(request, 'Email not found')
        
        return redirect('admin_blacklist_email')
    
    context = {
        'blacklist_emails': blacklist_emails,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/blacklist_email.html', context)

# Admin Blog Management
@login_required
@admin_required
def admin_blog(request):
    posts = BlogPost.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'toggle_publish':
            post_id = request.POST.get('post_id')
            try:
                post = BlogPost.objects.get(id=post_id)
                post.is_published = not post.is_published
                post.save()
                messages.success(request, 'Post status updated')
            except BlogPost.DoesNotExist:
                messages.error(request, 'Post not found')
        elif action == 'delete':
            post_id = request.POST.get('post_id')
            try:
                post = BlogPost.objects.get(id=post_id)
                post.delete()
                messages.success(request, 'Post deleted')
            except BlogPost.DoesNotExist:
                messages.error(request, 'Post not found')
        
        return redirect('admin_blog')
    
    context = {
        'posts': posts,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/blog.html', context)

# Admin Notifications Management
@login_required
@admin_required
def admin_notifications(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by read status
    filter_status = request.GET.get('filter', '')
    if filter_status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_status == 'read':
        notifications = notifications.filter(is_read=True)
    
    # Get unread count
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'mark_all_read':
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            messages.success(request, 'All notifications marked as read')
            return redirect('admin_notifications')
        elif action == 'delete':
            notification_id = request.POST.get('notification_id')
            try:
                notification = Notification.objects.get(id=notification_id, user=request.user)
                notification.delete()
                messages.success(request, 'Notification deleted')
            except Notification.DoesNotExist:
                messages.error(request, 'Notification not found')
            return redirect('admin_notifications')
        elif action == 'delete_all_read':
            Notification.objects.filter(user=request.user, is_read=True).delete()
            messages.success(request, 'All read notifications deleted')
            return redirect('admin_notifications')
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'filter_status': filter_status,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/notifications.html', context)

# Mark notification as read (AJAX)
@login_required
@admin_required
@require_http_methods(["POST"])
def admin_mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)

# Create notification (for admin use)
@login_required
@admin_required
@require_http_methods(["POST"])
def admin_create_notification(request):
    title = request.POST.get('title', '').strip()
    message = request.POST.get('message', '').strip()
    notification_type = request.POST.get('notification_type', 'system')
    link = request.POST.get('link', '').strip()
    user_id = request.POST.get('user_id', '').strip()
    
    if not title or not message:
        messages.error(request, 'Title and message are required')
        return redirect('admin_notifications')
    
    # Create notification for specific user or all admins
    if user_id:
        try:
            target_user = User.objects.get(id=user_id)
            Notification.objects.create(
                user=target_user,
                title=title,
                message=message,
                notification_type=notification_type,
                link=link if link else None
            )
            messages.success(request, f'Notification sent to {target_user.username}')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
    else:
        # Send to all admins
        admin_users = User.objects.filter(
            Q(profile__role='admin') | Q(is_superuser=True)
        ).distinct()
        for admin_user in admin_users:
            Notification.objects.create(
                user=admin_user,
                title=title,
                message=message,
                notification_type=notification_type,
                link=link if link else None
            )
        messages.success(request, f'Notification sent to all admins')
    
    return redirect('admin_notifications')

# Add Funds
@login_required
def add_funds(request):
    # Get enabled payment methods from system settings
    from .settings_utils import get_setting, get_setting_float
    
    enabled_methods = []
    for method_code, method_name in Payment.PAYMENT_METHODS:
        is_enabled = get_setting(f'payment_{method_code}_enabled', 'true')
        if is_enabled.lower() in ('true', '1', 'yes', 'on'):
            enabled_methods.append((method_code, method_name))
    
    # If no payment methods are enabled, enable all by default
    if not enabled_methods:
        enabled_methods = Payment.PAYMENT_METHODS
    
    # Get min/max deposit settings
    min_deposit = get_setting_float('min_deposit', 1.0)
    max_deposit = get_setting_float('max_deposit', 10000.0)
    
    if request.method == 'POST':
        amount = request.POST.get('amount', '').strip()
        method = request.POST.get('method', '').strip()
        regenerate = request.POST.get('regenerate', '').strip() == 'true'
        payment_id = request.POST.get('payment_id', '').strip()
        
        errors = []
        
        # Handle QR regeneration for KHQR payments
        if regenerate and payment_id and method == 'khqr':
            try:
                payment = Payment.objects.get(id=payment_id, user=request.user, method='khqr', status='pending')
                # Regenerate QR code for existing payment
                from .payment_gateways import create_khqr_payment
                khqr_data, error = create_khqr_payment(payment)
                if khqr_data:
                    return render(request, 'panel/khqr_payment.html', {
                        'payment': payment,
                        'khqr_data': khqr_data,
                    })
                else:
                    messages.error(request, f'Failed to regenerate QR code: {error}')
                    return redirect('add_funds')
            except Payment.DoesNotExist:
                messages.error(request, 'Payment not found or cannot be regenerated')
                return redirect('add_funds')
        
        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                errors.append('Amount must be greater than 0')
            elif amount < min_deposit:
                errors.append(f'Minimum amount is ${min_deposit:.2f}')
            elif amount > max_deposit:
                errors.append(f'Maximum amount is ${max_deposit:,.2f}')
        except (ValueError, TypeError):
            errors.append('Invalid amount')
        
        # Validate payment method - check if it's enabled
        valid_methods = [choice[0] for choice in enabled_methods]
        if method not in valid_methods:
            errors.append('Invalid or disabled payment method')
        
        if not errors:
            # Generate unique transaction ID
            import uuid
            transaction_id = f"TXN{uuid.uuid4().hex[:12].upper()}"
            
            # Create payment record
            payment = Payment.objects.create(
                transaction_id=transaction_id,
                user=request.user,
                amount=amount,
                method=method,
                status='pending',
            )
            
            # Process payment based on method
            from .payment_gateways import (
                create_paypal_payment, 
                create_stripe_payment_intent,
                create_khqr_payment
            )
            from django.conf import settings
            
            if method == 'paypal':
                approval_url, error = create_paypal_payment(payment)
                if approval_url:
                    return redirect(approval_url)
                else:
                    messages.error(request, f'PayPal payment creation failed: {error}')
                    payment.status = 'failed'
                    payment.save()
                    
            elif method == 'stripe':
                client_secret, error = create_stripe_payment_intent(payment)
                if client_secret:
                    # Store payment ID in session for confirmation
                    request.session['stripe_payment_id'] = payment.id
                    return render(request, 'panel/stripe_payment.html', {
                        'payment': payment,
                        'client_secret': client_secret,
                        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
                    })
                else:
                    messages.error(request, f'Stripe payment creation failed: {error}')
                    payment.status = 'failed'
                    payment.save()
                    
            elif method == 'khqr':
                khqr_data, error = create_khqr_payment(payment)
                if khqr_data:
                    # Render KHQR payment page with QR code
                    return render(request, 'panel/khqr_payment.html', {
                        'payment': payment,
                        'khqr_data': khqr_data,
                    })
                else:
                    messages.error(request, f'KHQR payment creation failed: {error}')
                    payment.status = 'failed'
                    payment.save()
            else:
                # Other payment methods (manual processing)
                messages.success(request, f'Payment request created. Transaction ID: {transaction_id}. Please complete the payment.')
                return redirect('transaction_logs')
        
        # Show errors
        for error in errors:
            messages.error(request, error)
    
    # GET request - show form
    context = {
        'payment_methods': enabled_methods,
        'min_deposit': min_deposit,
        'max_deposit': max_deposit,
    }
    return render(request, 'panel/add_funds.html', context)

# Transaction Logs (User's own transactions)
@login_required
def transaction_logs(request):
    transactions = Payment.objects.filter(user=request.user).order_by('-created_at')
    
    # Filtering
    status_filter = request.GET.get('status', '')
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    
    # Pagination
    per_page = request.GET.get('per_page', '10')
    valid_per_page_options = ['10', '25', '50', '100']
    if per_page not in valid_per_page_options:
        per_page = '25'
    per_page_int = int(per_page)
    
    paginator = Paginator(transactions, per_page_int)
    page = request.GET.get('page', 1)
    
    try:
        transactions_page = paginator.page(page)
    except PageNotAnInteger:
        transactions_page = paginator.page(1)
    except EmptyPage:
        transactions_page = paginator.page(paginator.num_pages)
    
    # Calculate summary stats (using all transactions, not just current page)
    total_deposited = Payment.objects.filter(
        user=request.user, 
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    pending_count = Payment.objects.filter(
        user=request.user,
        status='pending'
    ).count()
    
    context = {
        'transactions': transactions_page,
        'status_filter': status_filter,
        'total_deposited': total_deposited,
        'pending_count': pending_count,
        'per_page': per_page,
        'per_page_options': valid_per_page_options,
    }
    return render(request, 'panel/transaction_logs.html', context)

# PayPal Payment Return (Success)
@login_required
def paypal_return(request):
    payment_id = request.GET.get('paymentId', '')
    payer_id = request.GET.get('PayerID', '')
    
    if not payment_id or not payer_id:
        messages.error(request, 'Invalid PayPal payment response')
        return redirect('add_funds')
    
    from .payment_gateways import execute_paypal_payment
    
    success, payment, error = execute_paypal_payment(payment_id, payer_id)
    
    if success and payment:
        messages.success(request, f'Payment successful! ${payment.amount} has been added to your account.')
        return redirect('transaction_logs')
    else:
        messages.error(request, f'Payment failed: {error}')
        return redirect('add_funds')

# PayPal Payment Cancel
@login_required
def paypal_cancel(request):
    payment_id = request.GET.get('token', '')
    
    if payment_id:
        try:
            from .payment_gateways import paypalrestsdk
            paypal_payment = paypalrestsdk.Payment.find(payment_id)
            if paypal_payment:
                try:
                    payment = Payment.objects.get(gateway_payment_id=payment_id)
                    payment.status = 'canceled'
                    payment.save()
                except Payment.DoesNotExist:
                    pass
        except:
            pass
    
    messages.warning(request, 'Payment was canceled')
    return redirect('add_funds')

# Stripe Payment Success
@login_required
def stripe_success(request):
    payment_id = request.session.get('stripe_payment_id')
    payment_intent_id = request.GET.get('payment_intent', '')
    
    if not payment_intent_id:
        messages.error(request, 'Invalid payment response')
        return redirect('add_funds')
    
    from .payment_gateways import confirm_stripe_payment
    
    success, payment, error = confirm_stripe_payment(payment_intent_id)
    
    if 'stripe_payment_id' in request.session:
        del request.session['stripe_payment_id']
    
    if success and payment:
        messages.success(request, f'Payment successful! ${payment.amount} has been added to your account.')
        return redirect('transaction_logs')
    else:
        messages.error(request, f'Payment failed: {error}')
        return redirect('add_funds')

# Stripe Payment Cancel
@login_required
def stripe_cancel(request):
    if 'stripe_payment_id' in request.session:
        del request.session['stripe_payment_id']
    
    messages.warning(request, 'Payment was canceled')
    return redirect('add_funds')

# Stripe Webhook
@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """
    Handle Stripe webhook events
    """
    
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)
    
    from .payment_gateways import handle_stripe_webhook
    
    success, payment, error = handle_stripe_webhook(event)
    
    if success:
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'error', 'message': error}, status=400)

# Check Payment Status (for KHQR and other async payments)
@login_required
def check_payment_status(request, payment_id):
    """
    Check the status of a payment (primarily for KHQR)
    """
    try:
        payment = Payment.objects.get(id=payment_id, user=request.user)
        
        # If already completed, return success
        if payment.status == 'completed':
            return JsonResponse({
                'status': 'completed',
                'message': 'Payment completed successfully'
            })
        
        # For KHQR payments, check if QR code has expired
        if payment.method == 'khqr':
            from django.utils import timezone
            from datetime import timedelta
            
            # Check if QR code has expired
            gateway_response = payment.gateway_response or {}
            expires_at_str = gateway_response.get('expires_at')
            
            if expires_at_str:
                try:
                    from datetime import datetime
                    expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                    if timezone.now() > expires_at:
                        # QR code has expired
                        payment.status = 'expired'
                        payment.save()
                        return JsonResponse({
                            'status': 'expired',
                            'message': 'QR code has expired. Please generate a new one.'
                        })
                except (ValueError, TypeError):
                    pass
            
            # Check status with gateway
            from .payment_gateways import check_khqr_payment_status
            success, updated_payment, error = check_khqr_payment_status(payment)
            
            if success and updated_payment:
                return JsonResponse({
                    'status': 'completed',
                    'message': 'Payment completed successfully'
                })
            elif updated_payment:
                return JsonResponse({
                    'status': updated_payment.status,
                    'message': error or 'Payment is pending'
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': error or 'Failed to check payment status'
                }, status=400)
        
        # For other payment methods, just return current status
        return JsonResponse({
            'status': payment.status,
            'message': f'Payment is {payment.status}'
        })
        
    except Payment.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Payment not found'
        }, status=404)


# ============================================
# Marketing Promotion Management Views
# ============================================

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def admin_promotions_list(request):
    """Admin view to list all marketing promotions"""
    if not request.user.profile.role == 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    # Filter and search
    status = request.GET.get('status', '')
    promotion_type = request.GET.get('type', '')
    search = request.GET.get('search', '')
    
    promotions = MarketingPromotion.objects.all()
    
    if status:
        promotions = promotions.filter(status=status)
    if promotion_type:
        promotions = promotions.filter(promotion_type=promotion_type)
    if search:
        promotions = promotions.filter(
            Q(title__icontains=search) | 
            Q(title_km__icontains=search) | 
            Q(promotion_id__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(promotions, 20)
    page = request.GET.get('page', 1)
    
    try:
        promotions_page = paginator.page(page)
    except PageNotAnInteger:
        promotions_page = paginator.page(1)
    except EmptyPage:
        promotions_page = paginator.page(paginator.num_pages)
    
    context = {
        'promotions': promotions_page,
        'status_choices': MarketingPromotion.STATUS_CHOICES,
        'type_choices': MarketingPromotion.PROMOTION_TYPES,
        'current_status': status,
        'current_type': promotion_type,
        'search': search,
    }
    
    return render(request, 'panel/admin/promotions_list.html', context)


def safe_float(value, default=0.0):
    """Safely convert a value to float, handling empty strings and None"""
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Safely convert a value to int, handling empty strings and None"""
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


@login_required
def admin_promotion_create(request):
    """Admin view to create a new promotion"""
    if not request.user.profile.role == 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            # Create promotion
            promotion = MarketingPromotion.objects.create(
                title=request.POST.get('title'),
                title_km=request.POST.get('title_km', ''),
                description=request.POST.get('description', ''),
                description_km=request.POST.get('description_km', ''),
                promotion_type=request.POST.get('promotion_type'),
                status=request.POST.get('status', 'draft'),
                background_color=request.POST.get('background_color', '#007bff'),
                text_color=request.POST.get('text_color', '#ffffff'),
                target_audience=request.POST.get('target_audience', 'all'),
                display_location=request.POST.get('display_location', 'homepage'),
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                display_priority=safe_int(request.POST.get('display_priority'), 0),
                cta_text=request.POST.get('cta_text', ''),
                cta_link=request.POST.get('cta_link', ''),
                discount_code=request.POST.get('discount_code', ''),
                discount_percentage=safe_float(request.POST.get('discount_percentage'), 0),
                bonus_amount=safe_float(request.POST.get('bonus_amount'), 0),
                auto_expire=request.POST.get('auto_expire') == 'on',
                show_countdown=request.POST.get('show_countdown') == 'on',
                max_views_per_user=safe_int(request.POST.get('max_views_per_user'), 0),
                created_by=request.user
            )
            
            # Handle image uploads
            if 'banner_image' in request.FILES:
                promotion.banner_image = request.FILES['banner_image']
            if 'banner_image_mobile' in request.FILES:
                promotion.banner_image_mobile = request.FILES['banner_image_mobile']
            
            promotion.save()
            
            messages.success(request, f'Promotion {promotion.promotion_id} created successfully!')
            return redirect('admin_promotions_list')
            
        except Exception as e:
            messages.error(request, f'Error creating promotion: {str(e)}')
    
    context = {
        'promotion_types': MarketingPromotion.PROMOTION_TYPES,
        'status_choices': MarketingPromotion.STATUS_CHOICES,
        'target_audience_choices': MarketingPromotion.TARGET_AUDIENCE,
        'display_location_choices': MarketingPromotion.DISPLAY_LOCATION,
    }
    
    return render(request, 'panel/admin/promotion_create.html', context)


@login_required
def admin_promotion_edit(request, promotion_id):
    """Admin view to edit a promotion"""
    if not request.user.profile.role == 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    promotion = get_object_or_404(MarketingPromotion, promotion_id=promotion_id)
    
    if request.method == 'POST':
        try:
            # Update promotion
            promotion.title = request.POST.get('title')
            promotion.title_km = request.POST.get('title_km', '')
            promotion.description = request.POST.get('description', '')
            promotion.description_km = request.POST.get('description_km', '')
            promotion.promotion_type = request.POST.get('promotion_type')
            promotion.status = request.POST.get('status', 'draft')
            promotion.background_color = request.POST.get('background_color', '#007bff')
            promotion.text_color = request.POST.get('text_color', '#ffffff')
            promotion.target_audience = request.POST.get('target_audience', 'all')
            promotion.display_location = request.POST.get('display_location', 'homepage')
            promotion.start_date = request.POST.get('start_date')
            promotion.end_date = request.POST.get('end_date')
            promotion.display_priority = safe_int(request.POST.get('display_priority'), 0)
            promotion.cta_text = request.POST.get('cta_text', '')
            promotion.cta_link = request.POST.get('cta_link', '')
            promotion.discount_code = request.POST.get('discount_code', '')
            promotion.discount_percentage = safe_float(request.POST.get('discount_percentage'), 0)
            promotion.bonus_amount = safe_float(request.POST.get('bonus_amount'), 0)
            promotion.auto_expire = request.POST.get('auto_expire') == 'on'
            promotion.show_countdown = request.POST.get('show_countdown') == 'on'
            promotion.max_views_per_user = safe_int(request.POST.get('max_views_per_user'), 0)
            promotion.is_active = request.POST.get('is_active') == 'on'
            
            # Handle image uploads
            if 'banner_image' in request.FILES:
                promotion.banner_image = request.FILES['banner_image']
            if 'banner_image_mobile' in request.FILES:
                promotion.banner_image_mobile = request.FILES['banner_image_mobile']
            
            promotion.save()
            
            messages.success(request, f'Promotion {promotion.promotion_id} updated successfully!')
            return redirect('admin_promotions_list')
            
        except Exception as e:
            messages.error(request, f'Error updating promotion: {str(e)}')
    
    context = {
        'promotion': promotion,
        'promotion_types': MarketingPromotion.PROMOTION_TYPES,
        'status_choices': MarketingPromotion.STATUS_CHOICES,
        'target_audience_choices': MarketingPromotion.TARGET_AUDIENCE,
        'display_location_choices': MarketingPromotion.DISPLAY_LOCATION,
    }
    
    return render(request, 'panel/admin/promotion_edit.html', context)


@login_required
def admin_promotion_delete(request, promotion_id):
    """Admin view to delete a promotion"""
    if not request.user.profile.role == 'admin':
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        try:
            promotion = get_object_or_404(MarketingPromotion, promotion_id=promotion_id)
            promotion_title = promotion.title
            promotion.delete()
            return JsonResponse({
                'status': 'success',
                'message': f'Promotion "{promotion_title}" deleted successfully'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error deleting promotion: {str(e)}'
            }, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
def admin_promotion_analytics(request, promotion_id):
    """Admin view to see detailed analytics for a promotion"""
    if not request.user.profile.role == 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    promotion = get_object_or_404(MarketingPromotion, promotion_id=promotion_id)
    
    # Get analytics data
    views = PromotionView.objects.filter(promotion=promotion).order_by('-viewed_at')[:50]
    clicks = PromotionClick.objects.filter(promotion=promotion).order_by('-clicked_at')[:50]
    conversions = PromotionConversion.objects.filter(promotion=promotion).order_by('-converted_at')[:50]
    
    # Calculate daily stats (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    daily_views = PromotionView.objects.filter(
        promotion=promotion, 
        viewed_at__gte=thirty_days_ago
    ).extra(select={'day': 'date(viewed_at)'}).values('day').annotate(count=Count('id')).order_by('day')
    
    daily_clicks = PromotionClick.objects.filter(
        promotion=promotion, 
        clicked_at__gte=thirty_days_ago
    ).extra(select={'day': 'date(clicked_at)'}).values('day').annotate(count=Count('id')).order_by('day')
    
    daily_conversions = PromotionConversion.objects.filter(
        promotion=promotion, 
        converted_at__gte=thirty_days_ago
    ).extra(select={'day': 'date(converted_at)'}).values('day').annotate(count=Count('id')).order_by('day')
    
    # Total conversion value
    total_conversion_value = PromotionConversion.objects.filter(
        promotion=promotion
    ).aggregate(total=Sum('conversion_value'))['total'] or 0
    
    # Serialize daily data for JSON (convert date objects to strings)
    import json
    daily_views_json = json.dumps([{'day': str(item['day']), 'count': item['count']} for item in daily_views])
    daily_clicks_json = json.dumps([{'day': str(item['day']), 'count': item['count']} for item in daily_clicks])
    daily_conversions_json = json.dumps([{'day': str(item['day']), 'count': item['count']} for item in daily_conversions])
    
    context = {
        'promotion': promotion,
        'views': views,
        'clicks': clicks,
        'conversions': conversions,
        'daily_views': daily_views_json,
        'daily_clicks': daily_clicks_json,
        'daily_conversions': daily_conversions_json,
        'total_conversion_value': total_conversion_value,
        'ctr': promotion.get_ctr(),
        'conversion_rate': promotion.get_conversion_rate(),
    }
    
    return render(request, 'panel/admin/promotion_analytics.html', context)


# Public promotion tracking endpoints
@require_http_methods(["POST"])
def track_promotion_view(request):
    """Track when a user views a promotion"""
    try:
        promotion_id = request.POST.get('promotion_id')
        promotion = get_object_or_404(MarketingPromotion, promotion_id=promotion_id)
        
        # Check max views per user
        if promotion.max_views_per_user > 0 and request.user.is_authenticated:
            user_views_count = PromotionView.objects.filter(
                promotion=promotion, 
                user=request.user
            ).count()
            
            if user_views_count >= promotion.max_views_per_user:
                return JsonResponse({'status': 'max_views_reached'})
        
        # Record view
        PromotionView.objects.create(
            promotion=promotion,
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        # Increment view count
        promotion.views_count += 1
        promotion.save(update_fields=['views_count'])
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@require_http_methods(["POST"])
def track_promotion_click(request):
    """Track when a user clicks on a promotion"""
    try:
        promotion_id = request.POST.get('promotion_id')
        promotion = get_object_or_404(MarketingPromotion, promotion_id=promotion_id)
        
        # Record click
        PromotionClick.objects.create(
            promotion=promotion,
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request)
        )
        
        # Increment click count
        promotion.clicks_count += 1
        promotion.save(update_fields=['clicks_count'])
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def get_active_promotions(request):
    """API endpoint to get currently active promotions for display"""
    location = request.GET.get('location', 'homepage')
    
    # Get active promotions for this location
    now = timezone.now()
    promotions = MarketingPromotion.objects.filter(
        is_active=True,
        status='active',
        start_date__lte=now,
        end_date__gte=now,
        display_location__in=[location, 'all_pages']
    ).order_by('-display_priority')
    
    # Filter by target audience
    if request.user.is_authenticated:
        profile = request.user.profile
        
        # Filter based on audience targeting
        filtered_promotions = []
        for promo in promotions:
            if promo.target_audience == 'all':
                filtered_promotions.append(promo)
            elif promo.target_audience == 'new_users' and profile.created_at >= timezone.now() - timedelta(days=7):
                filtered_promotions.append(promo)
            elif promo.target_audience == 'active_users' and profile.total_spent > 0:
                filtered_promotions.append(promo)
            elif promo.target_audience == 'inactive_users' and profile.total_spent == 0:
                filtered_promotions.append(promo)
            elif promo.target_audience == 'high_spenders' and profile.total_spent >= 100:
                filtered_promotions.append(promo)
            elif promo.target_audience == 'resellers' and profile.is_reseller:
                filtered_promotions.append(promo)
            elif promo.target_audience == 'specific_users' and promo.specific_users.filter(id=request.user.id).exists():
                filtered_promotions.append(promo)
        
        promotions = filtered_promotions
    else:
        # Only show promotions for 'all' or 'new_users' to non-authenticated users
        promotions = [p for p in promotions if p.target_audience in ['all', 'new_users']]
    
    # Limit to max per page setting
    try:
        max_per_page = SystemSetting.objects.get(key='promotion_max_per_page').get_int_value()
    except:
        max_per_page = 3
    
    promotions = promotions[:max_per_page]
    
    # Serialize promotions
    promotions_data = [{
        'promotion_id': p.promotion_id,
        'title': p.title,
        'title_km': p.title_km,
        'description': p.description,
        'description_km': p.description_km,
        'promotion_type': p.promotion_type,
        'banner_image': p.banner_image.url if p.banner_image else '',
        'background_color': p.background_color,
        'text_color': p.text_color,
        'cta_text': p.cta_text,
        'cta_link': p.cta_link,
        'show_countdown': p.show_countdown,
        'end_date': p.end_date.isoformat() if p.show_countdown else None,
    } for p in promotions]
    
    return JsonResponse({'promotions': promotions_data})


@login_required
def user_promotions(request):
    """User-facing view to see all active promotions"""
    now = timezone.now()
    
    # Get active promotions
    promotions = MarketingPromotion.objects.filter(
        is_active=True,
        status='active',
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-display_priority', '-created_at')
    
    # Filter by target audience
    profile = request.user.profile
    filtered_promotions = []
    
    for promo in promotions:
        if promo.target_audience == 'all':
            filtered_promotions.append(promo)
        elif promo.target_audience == 'new_users' and profile.created_at >= timezone.now() - timedelta(days=7):
            filtered_promotions.append(promo)
        elif promo.target_audience == 'active_users' and profile.total_spent > 0:
            filtered_promotions.append(promo)
        elif promo.target_audience == 'inactive_users' and profile.total_spent == 0:
            filtered_promotions.append(promo)
        elif promo.target_audience == 'high_spenders' and profile.total_spent >= 100:
            filtered_promotions.append(promo)
        elif promo.target_audience == 'resellers' and profile.is_reseller:
            filtered_promotions.append(promo)
        elif promo.target_audience == 'specific_users' and promo.specific_users.filter(id=request.user.id).exists():
            filtered_promotions.append(promo)
    
    # Check which promotions user has already viewed (for max_views_per_user)
    viewed_promotion_ids = set()
    if request.user.is_authenticated:
        user_views = PromotionView.objects.filter(
            user=request.user,
            promotion__in=filtered_promotions
        ).values_list('promotion_id', flat=True)
        viewed_promotion_ids = set(user_views)
    
    # Filter out promotions that user has exceeded max views
    final_promotions = []
    for promo in filtered_promotions:
        if promo.max_views_per_user > 0:
            view_count = PromotionView.objects.filter(
                promotion=promo,
                user=request.user
            ).count()
            if view_count >= promo.max_views_per_user:
                continue
        final_promotions.append(promo)
    
    context = {
        'promotions': final_promotions,
        'viewed_promotion_ids': viewed_promotion_ids,
    }
    
    return render(request, 'panel/promotions.html', context)

