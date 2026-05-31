import logging
import uuid
from django.core.cache import cache
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, mixins, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
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
from accounts.models import OTP, User
from accounts.serializers import UserSerializer
from accounts.otp_service import send_verification_code

from .permissions import IsOrderOwner, IsAdminOrReadOnly
from .filters import OrderFilter
from django.utils import timezone
from utils.idempotency import IdempotencyHelper
from . import serializers

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
        serializer = AddToCartSerializer(data=request.data)
        if serializer.is_valid():
            cart = self.get_or_create_cart()
            product = serializer.validated_data['product']
            variant = serializer.validated_data['variant']
            quantity = serializer.validated_data['quantity']

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                variant=variant,
                defaults={'quantity': quantity, 'unit_price': variant.calculated_price if variant else product.price}
            )
            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            # If coupon exists and new item is not applicable, remove coupon
            if cart.coupon and not cart.coupon.is_applicable_to_item(cart_item):
                cart.coupon = None
                cart.save(update_fields=['coupon'])

            cart_serializer = self.get_serializer(cart)
            return Response(cart_serializer.data)

        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['post'])
    def update_item(self, request):
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({'error': 'Item ID is required'}, status=400)

        cart = self.get_or_create_cart()
        try:
            cart_item = CartItem.objects.get(cart=cart, id=item_id)
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found'}, status=404)

        serializer = UpdateCartItemSerializer(data=request.data, context={'cart_item': cart_item})
        if serializer.is_valid():
            quantity = serializer.validated_data['quantity']
            if quantity == 0:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()

            # Clear coupon if there are no eligible items left
            if cart.coupon:
                eligible_exists = any(cart.coupon.is_applicable_to_item(item) for item in cart.items.all())
                if not eligible_exists:
                    cart.coupon = None
                    cart.save(update_fields=['coupon'])

            cart_serializer = self.get_serializer(cart)
            return Response(cart_serializer.data)

        return Response(serializer.errors, status=400)

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

        # Clear coupon if there are no eligible items left
        if cart.coupon:
            eligible_exists = any(cart.coupon.is_applicable_to_item(item) for item in cart.items.all())
            if not eligible_exists:
                cart.coupon = None
                cart.save(update_fields=['coupon'])

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
            return Response({'error': 'لطفا کد تخفیف را وارد کنید'}, status=400)

        cart = self.get_or_create_cart()
        user = request.user if request.user.is_authenticated else None
        # For anonymous, use session key instead of user id
        user_id = user.id if user else request.session.session_key

        # Build idempotency key unique for this coupon, user, and cart
        key = IdempotencyHelper.generate_key('coupon', code, user_id, cart.id)

        def process_apply():
            # ---- existing coupon validation logic ----
            try:
                coupon = Coupon.objects.get(code=code, is_active=True)
            except Coupon.DoesNotExist:
                raise serializers.ValidationError('کد تخفیف نامعتبر است')

            now = timezone.now()
            if coupon.valid_from and coupon.valid_from > now:
                raise serializers.ValidationError('این کد تخفیف هنوز فعال نشده است')
            if coupon.valid_until and coupon.valid_until < now:
                raise serializers.ValidationError('این کد تخفیف منقضی شده است')

            if cart.subtotal < coupon.minimum_order_amount:
                raise serializers.ValidationError(f'حداقل مبلغ سفارش برای این کد {coupon.minimum_order_amount} تومان است')

            if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
                raise serializers.ValidationError('این کد تخفیف به حداکثر تعداد استفاده رسیده است')

            if user and coupon.usage_limit_per_user:
                user_usage_count = CouponUsage.objects.filter(coupon=coupon, user=user).count()
                if user_usage_count >= coupon.usage_limit_per_user:
                    raise serializers.ValidationError('شما قبلاً از این کد تخفیف استفاده کرده‌اید')

            # Apply coupon to cart
            cart.coupon = coupon
            cart.save()

            # Prepare optional partial eligibility message
            eligible_count = sum(1 for item in cart.items.all() if coupon.is_applicable_to_item(item))
            total_count = cart.items.count()
            message = None
            if eligible_count < total_count:
                message = f"کد تخفیف فقط برای {eligible_count} محصول از {total_count} محصول قابل استفاده است."

            # Serialize cart and include message if needed
            serializer = CartSerializer(cart, context={'request': request})
            response_data = serializer.data
            if message:
                response_data['coupon_message'] = message
            return response_data, 200

        try:
            data, status_code, from_cache = IdempotencyHelper.get_or_create(key, 60*60*48, process_apply)
            return Response(data, status=status_code)
        except serializers.ValidationError as e:
            return Response({'error': str(e)}, status=400)

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

    # ==================== GUEST CHECKOUT WITH OTP ====================
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def guest_checkout_request_otp(self, request):
        """Step 1: Send OTP and store guest data + cart ID in cache"""
        phone = request.data.get('phone')
        guest_data = request.data.get('guest_data')
        
        if not phone:
            return Response({'error': 'شماره موبایل الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        if not guest_data:
            return Response({'error': 'داده‌های ناقص'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the current anonymous cart
        cart = self.get_or_create_cart()
        if not cart or not cart.items.exists():
            return Response({'error': 'سبد خرید خالی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        reg_id = str(uuid.uuid4())
        cache.set(f'guest_checkout_{reg_id}', {
            'phone': phone,
            'guest_data': guest_data,
            'cart_id': cart.id,
            'session_key': self.request.session.session_key
        }, timeout=600)
        
        try:
            send_verification_code(phone)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'reg_id': reg_id, 'message': 'کد تایید ارسال شد'})

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def guest_checkout_verify_otp(self, request):
        """Step 2: Verify OTP, create user & order, return tokens"""
        reg_id = request.data.get('reg_id')
        code = request.data.get('code')
        
        if not reg_id or not code:
            return Response({'error': 'شناسه و کد تایید الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        cached = cache.get(f'guest_checkout_{reg_id}')
        if not cached:
            return Response({'error': 'زمان جلسه به اتمام رسیده است. لطفاً دوباره اقدام کنید.'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        phone = cached['phone']
        guest_data = cached['guest_data']
        cart_id = cached['cart_id']
        session_key = cached['session_key']
        
        # Verify OTP
        try:
            otp = OTP.objects.get(phone_number=phone)
        except OTP.DoesNotExist:
            return Response({'error': 'درخواست کد تایید یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        if not otp.is_valid() or otp.code != code:
            return Response({'error': 'کد نامعتبر یا منقضی شده'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as verified
        otp.is_verified = True
        otp.save()
        
        # Find or create user by phone
        user = User.objects.filter(phone_number=phone).first()
        if not user:
            user = User.objects.create_user(
                username=phone,
                email=guest_data.get('guest_email', ''),
                phone_number=phone,
                first_name=guest_data['guest_first_name'],
                last_name=guest_data['guest_last_name'],
                user_type='customer',
                is_active=True
            )
        else:
            if not user.first_name and guest_data.get('guest_first_name'):
                user.first_name = guest_data['guest_first_name']
            if not user.last_name and guest_data.get('guest_last_name'):
                user.last_name = guest_data['guest_last_name']
            if guest_data.get('guest_email') and not user.email:
                user.email = guest_data['guest_email']
            user.save()
        
        # Retrieve the cart (must still exist)
        try:
            cart = Cart.objects.get(id=cart_id, session_id=session_key, user__isnull=True, is_active=True)
        except Cart.DoesNotExist:
            return Response({'error': 'سبد خرید یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        # Transfer cart to user
        cart.user = user
        cart.session_id = None
        cart.save()
        
        # Create shipping address
        from accounts.models import UserAddress
        address = UserAddress.objects.create(
            user=user,
            address_type='shipping',
            first_name=guest_data['address_first_name'],
            last_name=guest_data['address_last_name'],
            address_line_1=guest_data['address_line_1'],
            address_line_2=guest_data.get('address_line_2', ''),
            city=guest_data['city'],
            state_province=guest_data['state_province'],
            postal_code=guest_data['postal_code'],
            phone_number=guest_data.get('phone_number', ''),
            is_default=True
        )
        
        # Build address JSON
        address_json = {
            'recipient_name': f"{address.first_name} {address.last_name}",
            'recipient_phone': address.phone_number,
            'province': address.state_province,
            'city': address.city,
            'district': address.address_line_2 or '',
            'street_address': address.address_line_1,
            'postal_code': address.postal_code,
            'type': address.address_type
        }
        
        # Create order
        order = Order.objects.create(
            user=user,
            status=Order.STATUS_PENDING,
            shipping_address=address_json,
            billing_address=address_json,
            payment_method=guest_data['payment_method'],
            subtotal=cart.subtotal,
            discount_amount=cart.discount_amount,
            total_amount=cart.total,
            customer_notes=guest_data.get('notes', '')
        )
        
        # Create order items
        for cart_item in cart.items.all():
            if cart_item.variant:
                unit_price = cart_item.variant.calculated_price
            else:
                unit_price = cart_item.product.price
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                variant=cart_item.variant,
                product_name=cart_item.product.name,
                variant_name=cart_item.variant.name if cart_item.variant else '',
                sku=cart_item.variant.sku if cart_item.variant else cart_item.product.sku,
                quantity=cart_item.quantity,
                unit_price=unit_price,
                subtotal=unit_price * cart_item.quantity,
                total_price=unit_price * cart_item.quantity,
                requires_prescription=cart_item.product.prescription_required == 'required'
            )
            # Reduce inventory
            if cart_item.product.track_inventory:
                if cart_item.variant:
                    cart_item.variant.stock_quantity -= cart_item.quantity
                    cart_item.variant.save(update_fields=['stock_quantity'])
                else:
                    cart_item.product.stock_quantity -= cart_item.quantity
                    cart_item.product.save(update_fields=['stock_quantity'])
        
        cart.is_active = False
        cart.save(update_fields=['is_active'])
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        cache.delete(f'guest_checkout_{reg_id}')
        
        return Response({
            'order_id': order.id,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def guest_checkout(self, request):
        """Guest checkout – creates user, transfers cart, places order, returns tokens (no OTP)"""
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

    @action(detail=False, methods=['post'])
    def remove_coupon(self, request):
        cart = self.get_or_create_cart()
        if cart.coupon:
            cart.coupon = None
            cart.save(update_fields=['coupon'])
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

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
                return Response({'message': _('Order cancelled successfully')}, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
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
        user = self.request.user
        if user.is_staff:
            return Refund.objects.all()
        return Refund.objects.filter(order__user=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateRefundSerializer
        return RefundSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            refund = serializer.save()
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
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(order__user=user)
    
    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'error': _('Permission denied')}, status=status.HTTP_403_FORBIDDEN)
        payment = self.get_object()
        payment.status = Payment.STATUS_COMPLETED
        payment.transaction_id = f"SIMULATED-{payment.id}"
        payment.save()
        serializer = self.get_serializer(payment)
        return Response(serializer.data)