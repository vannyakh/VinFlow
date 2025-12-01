from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
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
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    
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

