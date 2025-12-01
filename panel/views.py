from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import translation
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from datetime import timedelta
import json
import csv
import io
import pyotp
import qrcode
from io import BytesIO
import base64
import secrets

from .models import (
    UserProfile, Service, ServiceCategory, Order, SubscriptionPackage,
    UserSubscription, Coupon, Payment, Ticket, TicketMessage,
    AffiliateCommission, BlogPost, BlacklistIP, BlacklistLink, BlacklistEmail
)

# Create UserProfile on user creation
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

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
                
                # Handle referral code
                if referral_code:
                    try:
                        referrer = UserProfile.objects.get(referral_code=referral_code.upper())
                        user.profile.referred_by = referrer.user
                        user.profile.save()
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
    
    return render(request, 'panel/register.html')

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
                    # Check if 2FA is enabled
                    try:
                        if user.profile.two_factor_enabled:
                            # Store user ID in session for 2FA verification
                            request.session['2fa_user_id'] = user.id
                            request.session['2fa_verified'] = False
                            return redirect('verify_2fa')
                        else:
                            # No 2FA, proceed with normal login
                            login(request, user)
                            # Set language from user profile
                            try:
                                if user.profile.language:
                                    translation.activate(user.profile.language)
                                    request.session['django_language'] = user.profile.language
                            except:
                                pass
                            
                            messages.success(request, f'Welcome back, {user.username}!')
                            next_url = request.GET.get('next', 'dashboard')
                            return redirect(next_url)
                    except:
                        # Profile might not exist, proceed with normal login
                        login(request, user)
                        messages.success(request, f'Welcome back, {user.username}!')
                        next_url = request.GET.get('next', 'dashboard')
                        return redirect(next_url)
                else:
                    messages.error(request, 'Your account has been disabled. Please contact support.')
            else:
                messages.error(request, 'Invalid username or password. Please try again.')
    
    return render(request, 'panel/login.html')

# Dashboard
@login_required
def dashboard(request):
    user = request.user
    profile = user.profile
    
    # Statistics
    total_orders = Order.objects.filter(user=user).count()
    completed_orders = Order.objects.filter(user=user, status='Completed').count()
    pending_orders = Order.objects.filter(user=user, status__in=['Pending', 'Processing']).count()
    total_spent = Order.objects.filter(user=user).aggregate(Sum('charge'))['charge__sum'] or 0
    
    # Recent orders
    recent_orders = Order.objects.filter(user=user).order_by('-created_at')[:5]
    
    # Active subscriptions
    active_subscriptions = UserSubscription.objects.filter(user=user, is_active=True).count()
    
    context = {
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'total_spent': total_spent,
        'recent_orders': recent_orders,
        'active_subscriptions': active_subscriptions,
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

# Create Order
@login_required
@require_http_methods(["POST"])
def create_order(request):
    try:
        service_id = request.POST.get('service_id')
        link = request.POST.get('link')
        quantity = int(request.POST.get('quantity', 0))
        drip_feed = request.POST.get('drip_feed') == 'on'
        drip_feed_quantity = int(request.POST.get('drip_feed_quantity', 0))
        drip_feed_days = int(request.POST.get('drip_feed_days', 0))
        coupon_code = request.POST.get('coupon_code', '')
        
        service = get_object_or_404(Service, id=service_id, is_active=True)
        
        # Validate quantity
        if quantity < service.min_order or quantity > service.max_order:
            messages.error(request, f'Quantity must be between {service.min_order} and {service.max_order}')
            return redirect('services')
        
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
        if request.user.profile.balance < final_charge:
            messages.error(request, 'Insufficient balance. Please top up your account.')
            return redirect('dashboard')
        
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
        
        # Deduct balance
        request.user.profile.balance -= final_charge
        request.user.profile.total_spent += final_charge
        request.user.profile.save()
        
        # Place order to supplier (async)
        from .tasks import place_order_to_supplier
        place_order_to_supplier.delay(order.id)
        
        messages.success(request, f'Order #{order.order_id} created successfully!')
        return redirect('orders')
        
    except Exception as e:
        messages.error(request, f'Error creating order: {str(e)}')
        return redirect('services')

# Orders List
@login_required
def orders(request):
    orders_list = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Filtering
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders_list = orders_list.filter(status=status_filter)
    
    context = {
        'orders': orders_list,
        'status_filter': status_filter,
    }
    return render(request, 'panel/orders.html', context)

# Order Detail (HTMX)
@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'panel/partials/order_detail.html', {'order': order})

# Real-time Order Status (HTMX polling)
@login_required
def order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
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
                
                from .tasks import place_order_to_supplier
                place_order_to_supplier.delay(order.id)
                
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
        is_admin = request.user.profile.role == 'admin'
        
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
        
        from .tasks import place_order_to_supplier
        place_order_to_supplier.delay(order.id)
        
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
    
    return render(request, 'panel/free_trial.html', {'service': likes_service})

# Profile
@login_required
def profile(request):
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
                        if request.user.profile.avatar:
                            request.user.profile.avatar.delete(save=False)
                        request.user.profile.avatar = avatar
                        messages.success(request, 'Avatar updated successfully!')
                    else:
                        messages.error(request, 'Invalid file type. Please upload JPEG, PNG, GIF, or WebP image.')
            
            # Update language
            if 'language' in request.POST:
                language = request.POST.get('language', 'en')
                request.user.profile.language = language
                
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
            request.user.profile.save()
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
    
    return render(request, 'panel/verify_2fa.html', {'user': user})

# 2FA Setup
@login_required
def setup_2fa(request):
    profile = request.user.profile
    
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
    profile = request.user.profile
    
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
    profile = request.user.profile
    
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
    if request.user.profile.role != 'admin':
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
    
    context = {
        'total_users': total_users,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_orders': pending_orders,
        'daily_stats': daily_stats,
        'top_services': top_services,
        'recent_orders': recent_orders,
        'pending_tickets_count': pending_tickets_count,
    }
    return render(request, 'panel/admin/dashboard.html', context)

# Admin decorator
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.profile.role != 'admin':
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
    search = request.GET.get('search', '')
    
    orders = Order.objects.all()
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
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
        'search': search,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/orders.html', context)

# Admin Dripfeed Management
@login_required
@admin_required
def admin_dripfeed(request):
    dripfeed_orders = Order.objects.filter(drip_feed=True).order_by('-created_at')
    
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
    
    canceled_orders = Order.objects.filter(status='Canceled').order_by('-updated_at')
    
    context = {
        'canceled_orders': canceled_orders,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/cancel.html', context)

# Admin Services Management
@login_required
@admin_required
def admin_services(request):
    services = Service.objects.all().order_by('category', 'name')
    categories = ServiceCategory.objects.all().order_by('order')
    
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
        return redirect('admin_services')
    
    context = {
        'services': services,
        'categories': categories,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/services.html', context)

# Admin Transaction Logs
@login_required
@admin_required
def admin_transactions(request):
    transactions = Payment.objects.all().order_by('-created_at')[:200]
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    
    context = {
        'transactions': transactions,
        'status_filter': status_filter,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/transactions.html', context)

# Admin Categories Management
@login_required
@admin_required
def admin_categories(request):
    categories = ServiceCategory.objects.all().order_by('order')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            name = request.POST.get('name')
            name_km = request.POST.get('name_km', '')
            order = int(request.POST.get('order', 0))
            ServiceCategory.objects.create(name=name, name_km=name_km, order=order)
            messages.success(request, 'Category created successfully')
        elif action == 'update':
            category_id = request.POST.get('category_id')
            try:
                category = ServiceCategory.objects.get(id=category_id)
                category.name = request.POST.get('name')
                category.name_km = request.POST.get('name_km', '')
                category.order = int(request.POST.get('order', 0))
                category.is_active = request.POST.get('is_active') == 'on'
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
        
        return redirect('admin_categories')
    
    context = {
        'categories': categories,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/categories.html', context)

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
    search = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    
    users = User.objects.all()
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search)
        )
    
    if role_filter:
        users = users.filter(profile__role=role_filter)
    
    users = users.order_by('-date_joined')[:100]
    
    context = {
        'users': users,
        'search': search,
        'role_filter': role_filter,
        'pending_tickets_count': Ticket.objects.filter(status__in=['open', 'in_progress']).count(),
    }
    return render(request, 'panel/admin/users.html', context)

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

# Add Funds
@login_required
def add_funds(request):
    if request.method == 'POST':
        amount = request.POST.get('amount', '').strip()
        method = request.POST.get('method', '').strip()
        
        errors = []
        
        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                errors.append('Amount must be greater than 0')
            elif amount < 1:
                errors.append('Minimum amount is $1.00')
            elif amount > 10000:
                errors.append('Maximum amount is $10,000.00')
        except (ValueError, TypeError):
            errors.append('Invalid amount')
        
        # Validate payment method
        valid_methods = [choice[0] for choice in Payment.PAYMENT_METHODS]
        if method not in valid_methods:
            errors.append('Invalid payment method')
        
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
            
            # TODO: Integrate with actual payment gateway
            # For now, we'll simulate payment processing
            # In production, this would redirect to payment gateway or process payment
            
            messages.success(request, f'Payment request created. Transaction ID: {transaction_id}. Please complete the payment.')
            return redirect('transaction_logs')
        
        # Show errors
        for error in errors:
            messages.error(request, error)
    
    # GET request - show form
    payment_methods = Payment.PAYMENT_METHODS
    context = {
        'payment_methods': payment_methods,
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
    
    # Calculate summary stats
    total_deposited = Payment.objects.filter(
        user=request.user, 
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    pending_count = Payment.objects.filter(
        user=request.user,
        status='pending'
    ).count()
    
    context = {
        'transactions': transactions,
        'status_filter': status_filter,
        'total_deposited': total_deposited,
        'pending_count': pending_count,
    }
    return render(request, 'panel/transaction_logs.html', context)
