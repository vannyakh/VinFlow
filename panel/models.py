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



# Social Network Models
class SocialNetwork(models.Model):
    """
    Model for managing social network platform configurations
    """
    PLATFORM_CHOICES = [
        ('ig', 'Instagram'),
        ('fb', 'Facebook'),
        ('tt', 'TikTok'),
        ('yt', 'YouTube'),
        ('tw', 'Twitter/X'),
        ('sp', 'Spotify'),
        ('li', 'LinkedIn'),
        ('dc', 'Discord'),
        ('sc', 'Snapchat'),
        ('twitch', 'Twitch'),
        ('tg', 'Telegram'),
        ('google', 'Google'),
        ('sh', 'Shopee'),
        ('web', 'Website Traffic'),
        ('review', 'Reviews'),
        ('other', 'Others'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
        ('deprecated', 'Deprecated'),
    ]
    
    platform_code = models.CharField(max_length=20, unique=True, choices=PLATFORM_CHOICES)
    name = models.CharField(max_length=100, help_text="Display name")
    name_km = models.CharField(max_length=100, blank=True, help_text="Khmer translation")
    description = models.TextField(blank=True, help_text="Platform description")
    description_km = models.TextField(blank=True, help_text="Khmer description")
    
    # Visual elements
    icon = models.CharField(max_length=100, blank=True, help_text="Icon class or path")
    icon_image = models.ImageField(upload_to='social_networks/icons/', blank=True, null=True)
    color = models.CharField(max_length=7, default='#000000', help_text="Brand color (hex)")
    logo = models.ImageField(upload_to='social_networks/logos/', blank=True, null=True)
    
    # Configuration
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True, help_text="Available for orders")
    is_featured = models.BooleanField(default=False, help_text="Show in featured section")
    display_order = models.IntegerField(default=0, help_text="Display order in lists")
    
    # Metadata
    website_url = models.URLField(blank=True, help_text="Official website")
    documentation_url = models.URLField(blank=True, help_text="API documentation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Social Network"
        verbose_name_plural = "Social Networks"
    
    def __str__(self):
        return f"{self.name} ({self.platform_code})"
    
    def get_icon_class(self):
        """Get icon class for common platforms"""
        icon_map = {
            'ig': 'fab fa-instagram',
            'fb': 'fab fa-facebook',
            'tt': 'fab fa-tiktok',
            'yt': 'fab fa-youtube',
            'tw': 'fab fa-twitter',
            'sp': 'fab fa-spotify',
            'li': 'fab fa-linkedin',
            'dc': 'fab fa-discord',
            'sc': 'fab fa-snapchat',
            'twitch': 'fab fa-twitch',
            'tg': 'fab fa-telegram',
            'google': 'fab fa-google',
        }
        return icon_map.get(self.platform_code, 'fas fa-globe')
    
# Service Category
class ServiceCategory(models.Model):
    name = models.CharField(max_length=100)
    name_km = models.CharField(max_length=100, blank=True)
    icon = models.CharField(max_length=50, blank=True)
    social_network = models.ForeignKey('SocialNetwork', on_delete=models.SET_NULL, null=True, blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Service Categories"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

# Service Model
class Service(models.Model):
    CATEGORY_CHOICES = [
        ('ig', 'Instagram'), ('fb', 'Facebook'), ('tt', 'TikTok'), 
        ('yt', 'YouTube'), ('tw', 'Twitter/X'), ('sp', 'Spotify'),
        ('li', 'LinkedIn'), ('dc', 'Discord'), ('sc', 'Snapchat'),
        ('twitch', 'Twitch'), ('tg', 'Telegram'), ('google', 'Google'),
        ('sh', 'Shopee'), ('web', 'Website Traffic'), ('review', 'Reviews'),
        ('other', 'Others')
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
    
    PLATFORM_CHOICES = [
        ('ig', 'Instagram'), ('fb', 'Facebook'), ('tt', 'TikTok'), 
        ('yt', 'YouTube'), ('tw', 'Twitter/X'), ('sp', 'Spotify'),
        ('li', 'LinkedIn'), ('dc', 'Discord'), ('sc', 'Snapchat'),
        ('twitch', 'Twitch'), ('tg', 'Telegram'), ('google', 'Google'),
        ('sh', 'Shopee'), ('web', 'Website Traffic'), ('review', 'Reviews'),
        ('other', 'Others')
    ]
    
    order_id = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='other')
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
        # Auto-populate platform from service if not set
        if not self.platform and self.service:
            self.platform = self.service.service_type
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
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('khqr', 'KHQR Bakong'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
        ('expired', 'Expired'),
    ]
    
    transaction_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    gateway_response = models.JSONField(default=dict, blank=True)
    gateway_payment_id = models.CharField(max_length=255, blank=True)  # PayPal/Stripe payment ID
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.transaction_id} - {self.user.username} - ${self.amount}"

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

# Blacklist Models
class BlacklistIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blacklisted_ips')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Blacklist IP Address"
        verbose_name_plural = "Blacklist IP Addresses"
        ordering = ['-created_at']

class BlacklistLink(models.Model):
    link = models.URLField(unique=True)
    reason = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blacklisted_links')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Blacklist Link"
        verbose_name_plural = "Blacklist Links"
        ordering = ['-created_at']

class BlacklistEmail(models.Model):
    email = models.EmailField(unique=True)
    reason = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blacklisted_emails')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Blacklist Email"
        verbose_name_plural = "Blacklist Emails"
        ordering = ['-created_at']

# Settings/Configuration Model
class SystemSetting(models.Model):
    SETTING_GROUPS = [
        ('general', 'General'),
        ('payment', 'Payment'),
        ('email', 'Email'),
        ('api', 'API'),
        ('security', 'Security'),
        ('seo', 'SEO'),
        ('social', 'Social Media'),
        ('maintenance', 'Maintenance'),
    ]
    
    SETTING_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('boolean', 'Boolean'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('textarea', 'Textarea'),
        ('json', 'JSON'),
        ('image', 'Image'),
        ('image_list', 'Image List'),
    ]
    
    key = models.CharField(max_length=100, unique=True, help_text="Unique setting key (e.g., 'site_name', 'min_deposit')")
    value = models.TextField(blank=True, help_text="Setting value")
    default_value = models.TextField(blank=True, help_text="Default value if not set")
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES, default='text')
    group = models.CharField(max_length=20, choices=SETTING_GROUPS, default='general')
    label = models.CharField(max_length=200, help_text="Human-readable label")
    description = models.TextField(blank=True, help_text="Help text for this setting")
    is_public = models.BooleanField(default=False, help_text="Can be accessed via API/public")
    is_encrypted = models.BooleanField(default=False, help_text="Should this value be encrypted?")
    order = models.IntegerField(default=0, help_text="Display order within group")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_settings')
    
    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"
        ordering = ['group', 'order', 'key']
    
    def __str__(self):
        return f"{self.label} ({self.key})"
    
    def get_value(self):
        """Get the actual value, using default if empty"""
        return self.value if self.value else self.default_value
    
    def get_bool_value(self):
        """Get boolean value"""
        if self.setting_type == 'boolean':
            return self.get_value().lower() in ('true', '1', 'yes', 'on')
        return False
    
    def get_int_value(self):
        """Get integer value"""
        try:
            return int(self.get_value())
        except (ValueError, TypeError):
            return 0
    
    def get_float_value(self):
        """Get float value"""
        try:
            return float(self.get_value())
        except (ValueError, TypeError):
            return 0.0
    
    def get_image_list(self):
        """Get image list as Python list"""
        if self.setting_type == 'image_list' and self.value:
            try:
                import json
                return json.loads(self.value)
            except:
                return []
        return []

# Notification System
class Notification(models.Model):
    TYPE_CHOICES = [
        ('order', 'Order'),
        ('payment', 'Payment'),
        ('ticket', 'Ticket'),
        ('system', 'System'),
        ('user', 'User'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.URLField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
    
    def __str__(self):
        return f"{self.title} - {self.user.username if self.user else 'All Users'}"

# Marketing Promotion System
class MarketingPromotion(models.Model):
    """
    Model for managing marketing promotions and campaigns
    """
    PROMOTION_TYPES = [
        ('banner', 'Banner'),
        ('popup', 'Popup'),
        ('notification', 'Notification'),
        ('email', 'Email Campaign'),
        ('discount', 'Discount Campaign'),
        ('flash_sale', 'Flash Sale'),
        ('free_bonus', 'Free Bonus'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    TARGET_AUDIENCE = [
        ('all', 'All Users'),
        ('new_users', 'New Users'),
        ('active_users', 'Active Users'),
        ('inactive_users', 'Inactive Users'),
        ('high_spenders', 'High Spenders'),
        ('resellers', 'Resellers'),
        ('specific_users', 'Specific Users'),
    ]
    
    DISPLAY_LOCATION = [
        ('homepage', 'Homepage'),
        ('dashboard', 'User Dashboard'),
        ('services', 'Services Page'),
        ('checkout', 'Checkout Page'),
        ('all_pages', 'All Pages'),
    ]
    
    promotion_id = models.CharField(max_length=20, unique=True, blank=True)
    title = models.CharField(max_length=200, help_text="Promotion title")
    title_km = models.CharField(max_length=200, blank=True, help_text="Khmer translation")
    description = models.TextField(blank=True, help_text="Promotion description")
    description_km = models.TextField(blank=True, help_text="Khmer description")
    
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPES, default='banner')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Visual elements
    banner_image = models.ImageField(upload_to='promotions/banners/', blank=True, null=True)
    banner_image_mobile = models.ImageField(upload_to='promotions/banners/mobile/', blank=True, null=True)
    background_color = models.CharField(max_length=7, default='#007bff', help_text="Hex color code")
    text_color = models.CharField(max_length=7, default='#ffffff', help_text="Hex color code")
    
    # Targeting
    target_audience = models.CharField(max_length=20, choices=TARGET_AUDIENCE, default='all')
    specific_users = models.ManyToManyField(User, blank=True, related_name='targeted_promotions')
    display_location = models.CharField(max_length=20, choices=DISPLAY_LOCATION, default='homepage')
    
    # Timing
    start_date = models.DateTimeField(help_text="When promotion starts")
    end_date = models.DateTimeField(help_text="When promotion ends")
    display_priority = models.IntegerField(default=0, help_text="Higher number = higher priority")
    
    # Call to action
    cta_text = models.CharField(max_length=100, blank=True, help_text="Button text (e.g., 'Shop Now')")
    cta_link = models.CharField(max_length=500, blank=True, help_text="Button link")
    
    # Discount/Offer details (if applicable)
    discount_code = models.CharField(max_length=50, blank=True, help_text="Associated coupon code")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Free balance bonus")
    
    # Performance tracking
    views_count = models.IntegerField(default=0, help_text="How many times viewed")
    clicks_count = models.IntegerField(default=0, help_text="How many times clicked")
    conversions_count = models.IntegerField(default=0, help_text="How many conversions")
    
    # Settings
    is_active = models.BooleanField(default=True)
    auto_expire = models.BooleanField(default=True, help_text="Auto expire after end_date")
    show_countdown = models.BooleanField(default=False, help_text="Show countdown timer")
    max_views_per_user = models.IntegerField(default=0, help_text="0 = unlimited")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_promotions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-display_priority', '-created_at']
        verbose_name = "Marketing Promotion"
        verbose_name_plural = "Marketing Promotions"
    
    def save(self, *args, **kwargs):
        if not self.promotion_id:
            self.promotion_id = f"PROMO{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.promotion_id} - {self.title}"
    
    def is_currently_active(self):
        """Check if promotion is currently active based on time and status"""
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active and 
            self.status == 'active' and 
            self.start_date <= now <= self.end_date
        )
    
    def get_ctr(self):
        """Calculate Click-Through Rate"""
        if self.views_count == 0:
            return 0
        return (self.clicks_count / self.views_count) * 100
    
    def get_conversion_rate(self):
        """Calculate Conversion Rate"""
        if self.clicks_count == 0:
            return 0
        return (self.conversions_count / self.clicks_count) * 100


class PromotionView(models.Model):
    """
    Track individual user views of promotions
    """
    promotion = models.ForeignKey(MarketingPromotion, on_delete=models.CASCADE, related_name='user_views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='promotion_views')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-viewed_at']
        verbose_name = "Promotion View"
        verbose_name_plural = "Promotion Views"
    
    def __str__(self):
        return f"{self.promotion.promotion_id} viewed by {self.user.username if self.user else 'Anonymous'}"


class PromotionClick(models.Model):
    """
    Track clicks on promotions
    """
    promotion = models.ForeignKey(MarketingPromotion, on_delete=models.CASCADE, related_name='user_clicks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='promotion_clicks')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    clicked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-clicked_at']
        verbose_name = "Promotion Click"
        verbose_name_plural = "Promotion Clicks"
    
    def __str__(self):
        return f"{self.promotion.promotion_id} clicked by {self.user.username if self.user else 'Anonymous'}"


class PromotionConversion(models.Model):
    """
    Track conversions from promotions (orders, sign-ups, deposits)
    """
    CONVERSION_TYPES = [
        ('order', 'Order Placed'),
        ('deposit', 'Deposit Made'),
        ('signup', 'User Signup'),
        ('coupon_used', 'Coupon Used'),
    ]
    
    promotion = models.ForeignKey(MarketingPromotion, on_delete=models.CASCADE, related_name='conversions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promotion_conversions')
    conversion_type = models.CharField(max_length=20, choices=CONVERSION_TYPES)
    conversion_value = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Value of conversion (e.g., order amount)")
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True)
    payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, blank=True)
    converted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-converted_at']
        verbose_name = "Promotion Conversion"
        verbose_name_plural = "Promotion Conversions"
    
    def __str__(self):
        return f"{self.promotion.promotion_id} - {self.conversion_type} by {self.user.username}"

