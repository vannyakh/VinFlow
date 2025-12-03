from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.db.models import Q
from django.utils import timezone

from .models import (
    Service, Order, UserProfile, Coupon
)

class APILoginView(APIView):
    """API Login - Returns API token"""
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'status': 'success',
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'balance': float(user.profile.balance),
                }
            })
        return Response({'status': 'error', 'message': 'Invalid credentials'}, status=401)

class APIServicesView(APIView):
    """Get all active services"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        services = Service.objects.filter(is_active=True)
        data = []
        for service in services:
            data.append({
                'id': service.id,
                'name': service.name,
                'category': service.category.name if service.category else '',
                'type': service.service_type,
                'rate': float(service.rate),
                'min_order': service.min_order,
                'max_order': service.max_order,
                'description': service.description,
            })
        return Response({'status': 'success', 'services': data})

class APICreateOrderView(APIView):
    """Create order via API"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            service_id = request.data.get('service_id')
            link = request.data.get('link')
            quantity = int(request.data.get('quantity', 0))
            drip_feed = request.data.get('drip_feed', False)
            drip_feed_quantity = int(request.data.get('drip_feed_quantity', 0))
            drip_feed_days = int(request.data.get('drip_feed_days', 0))
            coupon_code = request.data.get('coupon_code', '')
            
            service = Service.objects.get(id=service_id, is_active=True)
            
            if quantity < service.min_order or quantity > service.max_order:
                return Response({
                    'status': 'error',
                    'message': f'Quantity must be between {service.min_order} and {service.max_order}'
                }, status=400)
            
            # Calculate charge
            charge = (service.rate / 1000) * quantity
            
            # Apply coupon
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
                return Response({
                    'status': 'error',
                    'message': 'Insufficient balance'
                }, status=400)
            
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
            
            # Place order to supplier
            from .tasks import place_order_to_supplier, execute_task_async_or_sync
            execute_task_async_or_sync(place_order_to_supplier, order.id)
            
            return Response({
                'status': 'success',
                'order': {
                    'order_id': order.order_id,
                    'service': service.name,
                    'quantity': order.quantity,
                    'charge': float(order.charge),
                    'status': order.status,
                }
            })
            
        except Service.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Service not found'
            }, status=404)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=400)

class APIOrdersView(APIView):
    """Get user orders"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        orders = Order.objects.select_related('service').filter(user=request.user).order_by('-created_at')
        status_filter = request.GET.get('status', '')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        data = []
        for order in orders:
            data.append({
                'order_id': order.order_id,
                'service': order.service.name,
                'platform': order.get_platform_display(),
                'link': order.link,
                'quantity': order.quantity,
                'charge': float(order.charge),
                'status': order.status,
                'start_count': order.start_count,
                'remains': order.remains,
                'created_at': order.created_at.isoformat(),
            })
        
        return Response({'status': 'success', 'orders': data})

class APIOrderStatusView(APIView):
    """Get specific order status"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        try:
            order = Order.objects.select_related('service').get(id=order_id, user=request.user)
            return Response({
                'status': 'success',
                'order': {
                    'order_id': order.order_id,
                    'service': order.service.name,
                    'platform': order.get_platform_display(),
                    'link': order.link,
                    'quantity': order.quantity,
                    'charge': float(order.charge),
                    'status': order.status,
                    'start_count': order.start_count,
                    'remains': order.remains,
                    'created_at': order.created_at.isoformat(),
                }
            })
        except Order.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Order not found'
            }, status=404)

class APIBalanceView(APIView):
    """Get user balance"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'status': 'success',
            'balance': float(request.user.profile.balance),
            'total_spent': float(request.user.profile.total_spent),
        })

