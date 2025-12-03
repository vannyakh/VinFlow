from django.contrib import admin
from .models import (
    UserProfile, ServiceCategory, Service, Order, SubscriptionPackage,
    UserSubscription, Coupon, Payment, Ticket, TicketMessage,
    AffiliateCommission, BlogPost, SystemSetting, MarketingPromotion,
    PromotionView, PromotionClick, PromotionConversion
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'balance', 'total_spent', 'is_reseller']
    list_filter = ['role', 'is_reseller']
    search_fields = ['user__username', 'user__email']

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_km', 'order', 'is_active']
    list_editable = ['order', 'is_active']

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'service_type', 'rate', 'min_order', 'max_order', 'is_active', 'supplier_api']
    list_filter = ['service_type', 'is_active', 'supplier_api', 'category']
    search_fields = ['name', 'name_km']
    list_editable = ['is_active', 'rate']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'user', 'service', 'platform', 'quantity', 'charge', 'status', 'created_at']
    list_filter = ['status', 'platform', 'created_at', 'service']
    search_fields = ['order_id', 'user__username', 'link']
    readonly_fields = ['order_id', 'created_at', 'updated_at']

@admin.register(SubscriptionPackage)
class SubscriptionPackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'service', 'quantity_per_day', 'price_per_month', 'is_active']
    list_filter = ['is_active', 'service']

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'package', 'is_active', 'next_delivery', 'created_at']
    list_filter = ['is_active', 'created_at']

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'usage_limit', 'used_count', 'is_active', 'valid_until']
    list_filter = ['is_active', 'discount_type']
    search_fields = ['code']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'user', 'amount', 'method', 'status', 'created_at']
    list_filter = ['status', 'method', 'created_at']
    search_fields = ['transaction_id', 'user__username']

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'user', 'subject', 'priority', 'status', 'created_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['ticket_id', 'subject', 'user__username']

@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'user', 'is_admin', 'created_at']
    list_filter = ['is_admin', 'created_at']

@admin.register(AffiliateCommission)
class AffiliateCommissionAdmin(admin.ModelAdmin):
    list_display = ['referrer', 'referred_user', 'commission_amount', 'is_paid', 'created_at']
    list_filter = ['is_paid', 'created_at']

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'author', 'is_published', 'views', 'created_at']
    list_filter = ['is_published', 'created_at']
    search_fields = ['title', 'slug']
    prepopulated_fields = {'slug': ('title',)}

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'label', 'group', 'setting_type', 'get_value', 'is_public', 'updated_at']
    list_filter = ['group', 'setting_type', 'is_public', 'is_encrypted']
    search_fields = ['key', 'label', 'description']
    list_editable = ['is_public']
    readonly_fields = ['updated_at', 'updated_by']
    fieldsets = (
        ('Basic Information', {
            'fields': ('key', 'label', 'description', 'group', 'setting_type', 'order')
        }),
        ('Value', {
            'fields': ('value', 'default_value')
        }),
        ('Options', {
            'fields': ('is_public', 'is_encrypted')
        }),
        ('Metadata', {
            'fields': ('updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def get_value(self, obj):
        return obj.get_value()[:50] + '...' if len(obj.get_value()) > 50 else obj.get_value()
    get_value.short_description = 'Value'


# Marketing Promotion Admin
class PromotionViewInline(admin.TabularInline):
    model = PromotionView
    extra = 0
    readonly_fields = ['user', 'ip_address', 'user_agent', 'viewed_at']
    can_delete = False
    max_num = 10


class PromotionClickInline(admin.TabularInline):
    model = PromotionClick
    extra = 0
    readonly_fields = ['user', 'ip_address', 'clicked_at']
    can_delete = False
    max_num = 10


class PromotionConversionInline(admin.TabularInline):
    model = PromotionConversion
    extra = 0
    readonly_fields = ['user', 'conversion_type', 'conversion_value', 'order', 'payment', 'converted_at']
    can_delete = False
    max_num = 10


@admin.register(MarketingPromotion)
class MarketingPromotionAdmin(admin.ModelAdmin):
    list_display = [
        'promotion_id', 'title', 'promotion_type', 'status', 'target_audience', 
        'display_location', 'start_date', 'end_date', 'get_performance', 'is_active'
    ]
    list_filter = [
        'promotion_type', 'status', 'target_audience', 'display_location', 
        'is_active', 'start_date', 'end_date'
    ]
    search_fields = ['promotion_id', 'title', 'title_km', 'description']
    readonly_fields = [
        'promotion_id', 'views_count', 'clicks_count', 'conversions_count',
        'get_ctr', 'get_conversion_rate', 'created_at', 'updated_at'
    ]
    list_editable = ['is_active', 'status']
    filter_horizontal = ['specific_users']
    inlines = [PromotionViewInline, PromotionClickInline, PromotionConversionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'promotion_id', 'title', 'title_km', 'description', 'description_km',
                'promotion_type', 'status'
            )
        }),
        ('Visual Design', {
            'fields': (
                'banner_image', 'banner_image_mobile', 'background_color', 'text_color'
            )
        }),
        ('Targeting', {
            'fields': (
                'target_audience', 'specific_users', 'display_location'
            )
        }),
        ('Schedule & Priority', {
            'fields': (
                'start_date', 'end_date', 'display_priority'
            )
        }),
        ('Call to Action', {
            'fields': (
                'cta_text', 'cta_link'
            )
        }),
        ('Offer Details', {
            'fields': (
                'discount_code', 'discount_percentage', 'bonus_amount'
            ),
            'classes': ('collapse',)
        }),
        ('Performance Metrics', {
            'fields': (
                'views_count', 'clicks_count', 'conversions_count',
                'get_ctr', 'get_conversion_rate'
            ),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': (
                'is_active', 'auto_expire', 'show_countdown', 'max_views_per_user'
            )
        }),
        ('Metadata', {
            'fields': (
                'created_by', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_performance(self, obj):
        """Display performance summary"""
        ctr = obj.get_ctr()
        conversion_rate = obj.get_conversion_rate()
        return f"Views: {obj.views_count} | CTR: {ctr:.2f}% | Conv: {conversion_rate:.2f}%"
    get_performance.short_description = 'Performance'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new promotion
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PromotionView)
class PromotionViewAdmin(admin.ModelAdmin):
    list_display = ['promotion', 'user', 'ip_address', 'viewed_at']
    list_filter = ['promotion', 'viewed_at']
    search_fields = ['promotion__promotion_id', 'promotion__title', 'user__username', 'ip_address']
    readonly_fields = ['promotion', 'user', 'ip_address', 'user_agent', 'viewed_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PromotionClick)
class PromotionClickAdmin(admin.ModelAdmin):
    list_display = ['promotion', 'user', 'ip_address', 'clicked_at']
    list_filter = ['promotion', 'clicked_at']
    search_fields = ['promotion__promotion_id', 'promotion__title', 'user__username', 'ip_address']
    readonly_fields = ['promotion', 'user', 'ip_address', 'clicked_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PromotionConversion)
class PromotionConversionAdmin(admin.ModelAdmin):
    list_display = ['promotion', 'user', 'conversion_type', 'conversion_value', 'converted_at']
    list_filter = ['promotion', 'conversion_type', 'converted_at']
    search_fields = ['promotion__promotion_id', 'promotion__title', 'user__username']
    readonly_fields = ['promotion', 'user', 'conversion_type', 'conversion_value', 'order', 'payment', 'converted_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
