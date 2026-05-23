import logging
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, mixins, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from products.models import Product, ProductVariant
from .models import (
    Cart, CartItem, Order, OrderItem, Shipment, 
    ShipmentItem, Refund, RefundItem
)
from payments.models import Payment
from .serializers import (
    CartSerializer, CartItemSerializer, AddToCartSerializer,
    UpdateCartItemSerializer, ApplyCouponSerializer,
    OrderListSerializer, OrderDetailSerializer, CreateOrderSerializer,
    CancelOrderSerializer, ShipmentSerializer, RefundSerializer,
    CreateRefundSerializer, GuestCheckoutSerializer
)
from payments.serializers import PaymentSerializer
from promotions.models import Coupon, CouponUsage

from .permissions import IsOrderOwner, IsAdminOrReadOnly
from .filters import OrderFilter
from django.utils import timezone

logger = logging.getLogger(__name__)


class CartViewSet(viewsets.GenericViewSet):
    """ViewSet for managing shopping cart"""
    permission_classes = [permissions.AllowAny]
    serializer_class = CartSerializer
    
    def get_queryset(self):
        """Get user's active cart"""
        if self.request.user.is_authenticated:
            return Cart.objects.filter(user=self.request.user, is_active=True)
        else:
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.save()
                session_key = self.request.session.session_key
            return Cart.objects.filter(session_id=session_key, user__isnull=True, is_active=True)
    
    def get_or_create_cart(self):
        """Get or create active cart for current user (authenticated) or session (anonymous)"""
        user = self.request.user
        session_key = self.request.session.session_key
        
        if not session_key:
            self.request.session.save()
            session_key = self.request.session.session_key
        
        if user.is_authenticated:
            cart = Cart.objects.filter(user=user, is_active=True).first()
            if cart:
                return cart
            anonymous_cart = Cart.objects.filter(session_id=session_key, user__isnull=True, is_active=True).first()
            if anonymous_cart:
                anonymous_cart.user = user
                anonymous_cart.session_id = None
                anonymous_cart.save()
                return anonymous_cart
            return Cart.objects.create(user=user)
        else:
            cart = Cart.objects.filter(session_id=session_key, user__isnull=True, is_active=True).first()
            if not cart:
                cart = Cart.objects.create(session_id=session_key)
            return cart
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current active cart"""
        cart = self.get_or_create_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart"""
        serializer = AddToCartSerializer(data=request.data)
        if serializer.is_valid():
            cart = self.get_or_create_cart()
            product = serializer.validated_data['product']
            variant = serializer.validated_data['variant']
            quantity = serializer.validated_data['quantity']
            
            cart_item = CartItem.objects.filter(
                cart=cart,
                product=product,
                variant=variant
            ).first()
            
            if cart_item:
                cart_item.quantity += quantity
                cart_item.save()
            else:
                unit_price = variant.calculated_price if variant else product.price
                CartItem.objects.create(
                    cart=cart,
                    product=product,
                    variant=variant,
                    quantity=quantity,
                    unit_price=unit_price
                )
            
            cart_serializer = self.get_serializer(cart)
            return Response(cart_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """Update cart item quantity"""
        item_id = request.data.get('item_id')
        if not item_id:
            return Response(
                {'error': _('Item ID is required')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart = self.get_or_create_cart()
        try:
            cart_item = CartItem.objects.get(cart=cart, id=item_id)
        except CartItem.DoesNotExist:
            return Response(
                {'error': _('Item not found in cart')},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UpdateCartItemSerializer(
            data=request.data,
            context={'cart_item': cart_item}
        )
        if serializer.is_valid():
            quantity = serializer.validated_data['quantity']
            
            if quantity == 0:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()
            
            cart_serializer = self.get_serializer(cart)
            return Response(cart_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        """Remove item from cart"""
        item_id = request.data.get('item_id')
        if not item_id:
            return Response(
                {'error': _('Item ID is required')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart = self.get_or_create_cart()
        try:
            cart_item = CartItem.objects.get(cart=cart, id=item_id)
        except CartItem.DoesNotExist:
            return Response(
                {'error': _('Item not found in cart')},
                status=status.HTTP_404_NOT_FOUND
            )
        
        cart_item.delete()
        cart_serializer = self.get_serializer(cart)
        return Response(cart_serializer.data)
    
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear cart"""
        cart = self.get_or_create_cart()
        cart.items.all().delete()
        cart_serializer = self.get_serializer(cart)
        return Response(cart_serializer.data)
    
    @action(detail=False, methods=['post'])
    def apply_coupon(self, request):
        code = request.data.get('code')
        if not code:
            return Response({'error': 'لطفا کد تخفیف را وارد کنید'}, status=status.HTTP_400_BAD_REQUEST)

        cart = self.get_or_create_cart()

        try:
            coupon = Coupon.objects.get(code=code, is_active=True)
        except Coupon.DoesNotExist:
            return Response({'error': 'کد تخفیف نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        if coupon.valid_from and coupon.valid_from > now:
            return Response({'error': 'این کد تخفیف هنوز فعال نشده است'}, status=status.HTTP_400_BAD_REQUEST)
        if coupon.valid_until and coupon.valid_until < now:
            return Response({'error': 'این کد تخفیف منقضی شده است'}, status=status.HTTP_400_BAD_REQUEST)

        if cart.subtotal < coupon.minimum_order_amount:
            return Response({'error': f'حداقل مبلغ سفارش برای این کد {coupon.minimum_order_amount} تومان است'}, status=status.HTTP_400_BAD_REQUEST)

        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            return Response({'error': 'این کد تخفیف به حداکثر تعداد استفاده رسیده است'}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.is_authenticated and coupon.usage_limit_per_user:
            user_usage_count = CouponUsage.objects.filter(coupon=coupon, user=request.user).count()
            if user_usage_count >= coupon.usage_limit_per_user:
                return Response({'error': 'شما قبلاً از این کد تخفیف استفاده کرده‌اید'}, status=status.HTTP_400_BAD_REQUEST)

        cart.coupon = coupon
        cart.save()
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def upload_prescription(self, request):
        """Upload prescription file"""
        if not request.user.is_authenticated:
            return Response({'error': 'لطفا وارد حساب کاربری خود شوید'}, status=status.HTTP_401_UNAUTHORIZED)
        cart = self.get_or_create_cart()
        if 'prescription_file' not in request.FILES:
            return Response({'error': _('Prescription file is required')}, status=status.HTTP_400_BAD_REQUEST)
        cart.prescription_file = request.FILES['prescription_file']
        cart.save(update_fields=['prescription_file'])
        serializer = self.get_serializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def set_addresses(self, request):
        """Set shipping and billing addresses (requires authentication)"""
        if not request.user.is_authenticated:
            return Response({'error': 'لطفا وارد حساب کاربری خود شوید'}, status=status.HTTP_401_UNAUTHORIZED)
        shipping_address_id = request.data.get('shipping_address_id')
        billing_address_id = request.data.get('billing_address_id')
        use_same_address = request.data.get('use_same_address', False)
        if not shipping_address_id:
            return Response({'error': _('Shipping address ID is required')}, status=status.HTTP_400_BAD_REQUEST)
        cart = self.get_or_create_cart()
        from accounts.models import UserAddress
        try:
            shipping_address = UserAddress.objects.get(id=shipping_address_id, user=request.user)
            cart.shipping_address = shipping_address
        except UserAddress.DoesNotExist:
            return Response({'error': _('Invalid shipping address')}, status=status.HTTP_400_BAD_REQUEST)
        if use_same_address:
            cart.billing_address = shipping_address
        elif billing_address_id:
            try:
                billing_address = UserAddress.objects.get(id=billing_address_id, user=request.user)
                cart.billing_address = billing_address
            except UserAddress.DoesNotExist:
                return Response({'error': _('Invalid billing address')}, status=status.HTTP_400_BAD_REQUEST)
        cart.save(update_fields=['shipping_address', 'billing_address'])
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    def merge_cart(self, cart_from, cart_to):
        """Merge items from one cart into another, then delete the source cart"""
        for item in cart_from.items.all():
            existing_item = cart_to.items.filter(product=item.product, variant=item.variant).first()
            if existing_item:
                existing_item.quantity += item.quantity
                existing_item.save()
            else:
                item.cart = cart_to
                item.save()
        cart_from.delete()

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def guest_checkout(self, request):
        """Guest checkout – creates user, transfers cart, places order, returns tokens"""
        serializer = GuestCheckoutSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            result = serializer.save()
            return Response({
                'order_id': result['order'].id,
                'access': result['access'],
                'refresh': result['refresh'],
                'user': result['user']
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing orders"""
    permission_classes = [IsAuthenticated, IsOrderOwner]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = OrderFilter
    ordering_fields = ['created_at', 'status', 'total']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get orders based on user role"""
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return OrderListSerializer
        if self.action == 'create':
            return CreateOrderSerializer
        if self.action == 'cancel':
            return CancelOrderSerializer
        return OrderDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Create order from cart"""
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            order = serializer.save()
            
            # Return order details
            detail_serializer = OrderDetailSerializer(order)
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel order"""
        order = self.get_object()
        serializer = CancelOrderSerializer(
            data=request.data,
            context={'order': order}
        )
        
        if serializer.is_valid():
            reason = serializer.validated_data.get('reason', '')
            try:
                order.cancel(reason)
                return Response(
                    {'message': _('Order cancelled successfully')},
                    status=status.HTTP_200_OK
                )
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def shipments(self, request, pk=None):
        """Get order shipments"""
        order = self.get_object()
        shipments = order.shipments.all()
        serializer = ShipmentSerializer(shipments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """Get order payments"""
        order = self.get_object()
        payments = order.payments.all()
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def refunds(self, request, pk=None):
        """Get order refunds"""
        order = self.get_object()
        refunds = order.refunds.all()
        serializer = RefundSerializer(refunds, many=True)
        return Response(serializer.data)


class ShipmentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing shipments"""
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['order', 'status', 'carrier']
    ordering_fields = ['created_at', 'shipped_at', 'delivered_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get shipments based on user role"""
        user = self.request.user
        if user.is_staff:
            return Shipment.objects.all()
        return Shipment.objects.filter(order__user=user)


class RefundViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    """ViewSet for managing refunds"""
    queryset = Refund.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['order', 'status']
    ordering_fields = ['requested_at', 'processed_at']
    ordering = ['-requested_at']
    
    def get_queryset(self):
        """Get refunds based on user role"""
        user = self.request.user
        if user.is_staff:
            return Refund.objects.all()
        return Refund.objects.filter(order__user=user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return CreateRefundSerializer
        return RefundSerializer
    
    def create(self, request, *args, **kwargs):
        """Create refund request"""
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            refund = serializer.save()
            
            # Return refund details
            detail_serializer = RefundSerializer(refund)
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentViewSet(mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    """ViewSet for viewing payments"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['order', 'status', 'method']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get payments based on user role"""
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(order__user=user)
    
    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        """Process payment (placeholder for payment gateway integration)"""
        if not request.user.is_staff:
            return Response(
                {'error': _('Permission denied')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        payment = self.get_object()
        
        # This is a placeholder for payment processing
        # In a real application, this would integrate with a payment gateway
        
        # Simulate successful payment
        payment.status = Payment.STATUS_COMPLETED
        payment.transaction_id = f"SIMULATED-{payment.id}"
        payment.save()
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data)