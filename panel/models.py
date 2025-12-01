from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

# User Profile Extension
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('reseller', 'Reseller'),
        ('user', 'User'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    language = models.CharField(max_length=5, default='en', choices=[('en', 'English'), ('km', 'ភាសាខ្មែរ')])
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    api_key = models.CharField(max_length=64, unique=True, blank=True)
    is_reseller = models.BooleanField(default=False)
    reseller_domain = models.CharField(max_length=255, blank=True)
    parent_reseller = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='child_resellers')
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 2FA Security
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True)
    backup_codes = models.JSONField(default=list, blank=True)  # Store backup codes as list
    
    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = uuid.uuid4().hex
        if not self.referral_code:
            self.referral_code = uuid.uuid4().hex[:12].upper()
        super().save(*args, **kwargs)

# Service Category
class ServiceCategory(models.Model):
    name = models.CharField(max_length=100)
    name_km = models.CharField(max_length=100, blank=True)
    icon = models.CharField(max_length=50, blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Service Categories"
        ordering = ['order']

# Service Model
class Service(models.Model):
    CATEGORY_CHOICES = [
        ('ig', 'Instagram'), ('fb', 'Facebook'), ('tt', 'TikTok'), 
        ('yt', 'YouTube'), ('tw', 'Twitter'), ('sh', 'Shopee'), 
        ('tg', 'Telegram'), ('other', 'Other')
    ]
    
    name = models.CharField(max_length=200)
    name_km = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True)
    service_type = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    rate = models.DecimalField(max_digits=10, decimal_places=4)  # per 1000
    min_order = models.IntegerField(default=1)
    max_order = models.IntegerField(default=100000)
    description = models.TextField(blank=True)
    description_km = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    supplier_api = models.CharField(max_length=50, default='jap')  # jap, peakerr, smmkings
    external_service_id = models.CharField(max_length=100, blank=True)
    drip_feed_enabled = models.BooleanField(default=False)
    refill_enabled = models.BooleanField(default=False)
    refill_days = models.IntegerField(default=30, validators=[MinValueValidator(30), MaxValueValidator(360)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']

# Order Model with Drip-Feed and Refill
class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Partial', 'Partial'),
        ('Canceled', 'Canceled'),
        ('Refunded', 'Refunded'),
    ]
    
    order_id = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    link = models.URLField()
    quantity = models.IntegerField()
    charge = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    start_count = models.IntegerField(default=0)
    remains = models.IntegerField(default=0)
    
    # Drip-Feed
    drip_feed = models.BooleanField(default=False)
    drip_feed_quantity = models.IntegerField(default=0)  # per day
    drip_feed_days = models.IntegerField(default=0)
    
    # Refill
    refill_enabled = models.BooleanField(default=False)
    refill_days = models.IntegerField(default=30)
    refill_count = models.IntegerField(default=0)
    
    # External tracking
    external_order_id = models.CharField(max_length=100, blank=True)
    supplier_response = models.JSONField(default=dict, blank=True)
    
    # Fraud detection
    is_fraud = models.BooleanField(default=False)
    fraud_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"ORD{self.id or uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

# Subscription Packages
class SubscriptionPackage(models.Model):
    name = models.CharField(max_length=200)
    name_km = models.CharField(max_length=200, blank=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    quantity_per_day = models.IntegerField()
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

# User Subscriptions
class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    package = models.ForeignKey(SubscriptionPackage, on_delete=models.CASCADE)
    link = models.URLField()
    is_active = models.BooleanField(default=True)
    next_delivery = models.DateTimeField(null=True, blank=True)
    last_delivery = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

# Coupon System
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=[('percent', 'Percentage'), ('fixed', 'Fixed Amount')])
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

# Payment Transactions
class Payment(models.Model):
    PAYMENT_METHODS = [
        ('aba', 'ABA PayWay'),
        ('wing', 'Wing Bank'),
        ('pipay', 'Pi Pay'),
        ('khqr', 'KHQR'),
        ('usdt', 'USDT'),
        ('card', 'Credit Card'),
        ('truemoney', 'TrueMoney'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    ]
    
    transaction_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    gateway_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

# Ticket Support System
class Ticket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    ticket_id = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    subject = models.CharField(max_length=200)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.ticket_id:
            self.ticket_id = f"TKT{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

# Affiliate System
class AffiliateCommission(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commissions')
    referred_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referred_commissions')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)  # percentage
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

# Blog System for SEO
class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    title_km = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    content_km = models.TextField(blank=True)
    excerpt = models.TextField(blank=True)
    excerpt_km = models.TextField(blank=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    featured_image = models.ImageField(upload_to='blog/', blank=True)
    is_published = models.BooleanField(default=False)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']