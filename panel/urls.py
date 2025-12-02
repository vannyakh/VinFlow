from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('maintenance/', views.maintenance, name='maintenance'),
    path('services/', views.services, name='services'),
    path('orders/', views.orders, name='orders'),
    path('orders/create/', views.create_order, name='create_order'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/status/', views.order_status, name='order_status'),
    path('orders/mass-upload/', views.mass_order_upload, name='mass_order_upload'),
    path('tickets/', views.tickets, name='tickets'),
    path('tickets/create/', views.create_ticket, name='create_ticket'),
    path('tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('free-trial/', views.free_trial, name='free_trial'),
    path('profile/', views.profile, name='profile'),
    path('add-funds/', views.add_funds, name='add_funds'),
    path('transaction-logs/', views.transaction_logs, name='transaction_logs'),
    
    # Payment Gateway Routes
    path('payment/paypal/return/', views.paypal_return, name='paypal_return'),
    path('payment/paypal/cancel/', views.paypal_cancel, name='paypal_cancel'),
    path('payment/stripe/success/', views.stripe_success, name='stripe_success'),
    path('payment/stripe/cancel/', views.stripe_cancel, name='stripe_cancel'),
    path('payment/stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    
    # Admin Routes
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/statistics/', views.admin_statistics, name='admin_statistics'),
    path('admin/reports/', views.admin_reports, name='admin_reports'),
    path('admin/orders/', views.admin_orders, name='admin_orders'),
    path('admin/dripfeed/', views.admin_dripfeed, name='admin_dripfeed'),
    path('admin/subscriptions/', views.admin_subscriptions, name='admin_subscriptions'),
    path('admin/cancel/', views.admin_cancel, name='admin_cancel'),
    path('admin/services/', views.admin_services, name='admin_services'),
    path('admin/transactions/', views.admin_transactions, name='admin_transactions'),
    path('admin/transactions/export/', views.admin_transactions_export, name='admin_transactions_export'),
    path('admin/categories/', views.admin_categories, name='admin_categories'),
    path('admin/settings/', views.admin_settings, name='admin_settings'),
    path('admin/settings/toggle-maintenance/', views.toggle_maintenance_mode, name='toggle_maintenance_mode'),
    path('admin/tickets/', views.admin_tickets, name='admin_tickets'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/create/', views.admin_create_user, name='admin_create_user'),
    path('admin/users/<int:user_id>/edit/', views.admin_edit_user, name='admin_edit_user'),
    path('admin/users/<int:user_id>/edit-role/', views.admin_edit_user_role, name='admin_edit_user_role'),
    path('admin/users/<int:user_id>/assign-group/', views.admin_assign_user_group, name='admin_assign_user_group'),
    path('admin/user-groups/', views.admin_user_groups, name='admin_user_groups'),
    path('admin/user-groups/create/', views.admin_create_group, name='admin_create_group'),
    path('admin/user-groups/<int:group_id>/edit/', views.admin_edit_group, name='admin_edit_group'),
    path('admin/user-groups/<int:group_id>/delete/', views.admin_delete_group, name='admin_delete_group'),
    path('admin/subscribers/', views.admin_subscribers, name='admin_subscribers'),
    path('admin/user-activity/', views.admin_user_activity, name='admin_user_activity'),
    path('admin/blacklist/ip/', views.admin_blacklist_ip, name='admin_blacklist_ip'),
    path('admin/blacklist/link/', views.admin_blacklist_link, name='admin_blacklist_link'),
    path('admin/blacklist/email/', views.admin_blacklist_email, name='admin_blacklist_email'),
    path('admin/blog/', views.admin_blog, name='admin_blog'),
    path('admin/notifications/', views.admin_notifications, name='admin_notifications'),
    path('admin/notifications/<int:notification_id>/mark-read/', views.admin_mark_notification_read, name='admin_mark_notification_read'),
    path('admin/notifications/create/', views.admin_create_notification, name='admin_create_notification'),
    
    # 2FA Routes
    path('verify-2fa/', views.verify_2fa, name='verify_2fa'),
    path('setup-2fa/', views.setup_2fa, name='setup_2fa'),
    path('disable-2fa/', views.disable_2fa, name='disable_2fa'),
    path('regenerate-backup-codes/', views.regenerate_backup_codes, name='regenerate_backup_codes'),
    
    # API Endpoints
    path('api/login/', api_views.APILoginView.as_view(), name='api_login'),
    path('api/services/', api_views.APIServicesView.as_view(), name='api_services'),
    path('api/orders/', api_views.APICreateOrderView.as_view(), name='api_create_order'),
    path('api/orders/list/', api_views.APIOrdersView.as_view(), name='api_orders'),
    path('api/orders/<int:order_id>/', api_views.APIOrderStatusView.as_view(), name='api_order_status'),
    path('api/balance/', api_views.APIBalanceView.as_view(), name='api_balance'),
]

