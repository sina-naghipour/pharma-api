# orders/serializers.py
from rest_framework import serializers
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from accounts.models import UserAddress
from products.models import Product, ProductVariant
from products.serializers import ProductListSerializer
from .models import (
    Cart, CartItem, Order, OrderItem, Shipment, 
    ShipmentItem, Refund, RefundItem
)

from payments.models import Payment

class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items"""
    product_details = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'variant', 'quantity', 
            'unit_price', 'total_price', 'product_details'
        ]
        read_only_fields = ['id', 'unit_price', 'total_price']
    
    def get_product_details(self, obj):
        """Get simplified product details with primary image URL"""
        request = self.context.get('request')
        product = obj.product
        
        # Get primary image absolute URL
        primary_image = None
        primary_img_obj = product.images.filter(is_primary=True).first()
        if primary_img_obj and request:
            primary_image = request.build_absolute_uri(primary_img_obj.image.url)
        elif product.images.first() and request:
            # fallback to first image if no primary is set
            primary_image = request.build_absolute_uri(product.images.first().image.url)
        
        return {
            'id': product.id,
            'name': product.name,
            'slug': product.slug,
            'primary_image': primary_image,
            'in_stock': product.in_stock,
            'prescription_required': product.prescription_required,
            'variant_name': obj.variant.name if obj.variant else None
        }
    
    def validate(self, data):
        """Validate cart item data"""
        product = data['product']
        variant = data.get('variant')
        quantity = data['quantity']
        
        # Check if product is active
        if not product.is_active:
            raise serializers.ValidationError({
                'product': _("This product is not available.")
            })
        
        # Check if variant belongs to product
        if variant and variant.product != product:
            raise serializers.ValidationError({
                'variant': _("This variant does not belong to the selected product.")
            })
        
        # Check if variant is active
        if variant and not variant.is_active:
            raise serializers.ValidationError({
                'variant': _("This variant is not available.")
            })
        
        # Check stock availability
        if product.track_inventory:
            available_quantity = variant.stock_quantity if variant else product.stock_quantity
            
            # For existing items, we need to add the current quantity
            if self.instance:
                current_quantity = self.instance.quantity
                required_quantity = quantity - current_quantity
            else:
                required_quantity = quantity
            
            if required_quantity > 0 and required_quantity > available_quantity:
                if available_quantity == 0:
                    raise serializers.ValidationError({
                        'quantity': _("This product is out of stock.")
                    })
                else:
                    raise serializers.ValidationError({
                        'quantity': _(f"Only {available_quantity} items available.")
                    })
        
        return data


class CartSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart"""
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    requires_prescription = serializers.BooleanField(read_only=True)
    has_out_of_stock_items = serializers.BooleanField(read_only=True)
    shipping_address_details = serializers.SerializerMethodField()
    billing_address_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'items', 'subtotal', 'total', 
            'discount_amount', 'total_items', 'requires_prescription',
            'has_out_of_stock_items', 'shipping_address', 'billing_address',
            'shipping_address_details', 'billing_address_details',
            'prescription_file', 'prescription_verified',
            'coupon', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'subtotal', 'total', 'discount_amount',
            'total_items', 'requires_prescription', 'has_out_of_stock_items',
            'prescription_verified', 'created_at', 'updated_at'
        ]
    
    def get_shipping_address_details(self, obj):
        """Get shipping address details"""
        if obj.shipping_address:
            return {
                'id': obj.shipping_address.id,
                'recipient_name': obj.shipping_address.recipient_name,
                'address': f"{obj.shipping_address.street_address}, {obj.shipping_address.district}, {obj.shipping_address.city}, {obj.shipping_address.province}",
                'phone': obj.shipping_address.recipient_phone
            }
        return None
    
    def get_billing_address_details(self, obj):
        """Get billing address details"""
        if obj.billing_address:
            return {
                'id': obj.billing_address.id,
                'recipient_name': obj.billing_address.recipient_name,
                'address': f"{obj.billing_address.street_address}, {obj.billing_address.district}, {obj.billing_address.city}, {obj.billing_address.province}",
                'phone': obj.billing_address.recipient_phone
            }
        return None


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart"""
    product_id = serializers.UUIDField(required=True)
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, default=1)
    
    def validate(self, data):
        """Validate add to cart data"""
        product_id = data['product_id']
        variant_id = data.get('variant_id')
        quantity = data['quantity']
        
        # Check if product exists
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError({
                'product_id': _("Product not found or not available.")
            })
        # check max order quantity
        if product.max_order_quantity > 0 and quantity > product.max_order_quantity:
            raise serializers.ValidationError({
                'quantity': _(f'You can order at most {product.max_order_quantity} of this product.')
            })
        # Check if variant exists and belongs to product
        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.get(
                    id=variant_id, 
                    product=product,
                    is_active=True
                )
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError({
                    'variant_id': _("Variant not found or not available.")
                })
        
        # Check stock availability
        if product.track_inventory:
            available_quantity = variant.stock_quantity if variant else product.stock_quantity
            if quantity > available_quantity:
                if available_quantity == 0:
                    raise serializers.ValidationError({
                        'quantity': _("This product is out of stock.")
                    })
                else:
                    raise serializers.ValidationError({
                        'quantity': _(f"Only {available_quantity} items available.")
                    })
        
        # Add validated objects to data
        data['product'] = product
        data['variant'] = variant
        
        return data


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item quantity"""
    quantity = serializers.IntegerField(min_value=0, required=True)
    
    def validate(self, data):
        """Validate cart item update data"""
        quantity = data['quantity']
        cart_item = self.context['cart_item']
        product = cart_item.product
        # check max order quantity
        if quantity > cart_item.quantity and product.max_order_quantity > 0 and quantity > product.max_order_quantity:
            raise serializers.ValidationError({
                'quantity': _(f'You cannot exceed {product.max_order_quantity} of this product.')
            })

        # Check stock availability if increasing quantity
        if quantity > cart_item.quantity and cart_item.product.track_inventory:
            variant = cart_item.variant
            available_quantity = variant.stock_quantity if variant else cart_item.product.stock_quantity
            required_quantity = quantity - cart_item.quantity
            
            if required_quantity > available_quantity:
                if available_quantity == 0:
                    raise serializers.ValidationError({
                        'quantity': _("This product is out of stock.")
                    })
                else:
                    raise serializers.ValidationError({
                        'quantity': _(f"Only {available_quantity} additional items available.")
                    })
        
        return data


class ApplyCouponSerializer(serializers.Serializer):
    """Serializer for applying coupon to cart"""
    code = serializers.CharField(max_length=50, required=True)


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""
    total = serializers.DecimalField(source='total_price', max_digits=12, decimal_places=2)
    
    def get_total(self, obj):
        return obj.unit_price * obj.quantity
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'variant', 'product_name', 'variant_name',
            'sku', 'quantity', 'unit_price', 'subtotal', 'discount_amount',
            'tax_amount', 'total', 'requires_prescription',
            'batch_number', 'expiry_date'
        ]
        read_only_fields = ['id']


class OrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for order list view"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'status_display',
            'created_at', 'total', 'payment_method',
            'payment_method_display', 'tracking_number'
        ]
        read_only_fields = fields

    def get_total(self, obj):
        return obj.total_amount


class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for orders"""
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    is_cancelled = serializers.BooleanField(read_only=True)
    can_cancel = serializers.BooleanField(read_only=True)
    total = serializers.DecimalField(source='total_amount', max_digits=12, decimal_places=2)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'status', 'status_display',
            'created_at', 'updated_at', 'paid_at', 'shipped_at',
            'delivered_at', 'cancelled_at', 'shipping_address',
            'billing_address', 'payment_method', 'payment_method_display',
            'payment_id', 'subtotal', 'shipping_cost', 'tax_amount',
            'discount_amount', 'total', 'coupon_code', 'coupon_discount',
            'prescription_file', 'prescription_verified', 'tracking_number',
            'shipping_carrier', 'estimated_delivery', 'customer_notes',
            'items', 'is_paid', 'is_completed', 'is_cancelled', 'can_cancel'
        ]
        read_only_fields = fields

    def get_total(self, obj):
        return sum([item.total_price for item in obj.items.all()])


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating orders"""
    shipping_address_id = serializers.UUIDField(required=True)
    billing_address_id = serializers.UUIDField(required=False)
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_METHOD_CHOICES, required=True)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    use_same_address_for_billing = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """Validate order creation data"""
        user = self.context['request'].user
        
        # Validate shipping address
        try:
            shipping_address = UserAddress.objects.get(
                id=data['shipping_address_id'],
                user=user
            )
        except UserAddress.DoesNotExist:
            raise serializers.ValidationError({
                'shipping_address_id': _("Invalid shipping address.")
            })
        
        # Set billing address based on selection
        if data.get('use_same_address_for_billing'):
            billing_address = shipping_address
        else:
            try:
                billing_address = UserAddress.objects.get(
                    id=data.get('billing_address_id'),
                    user=user
                )
            except UserAddress.DoesNotExist:
                raise serializers.ValidationError({
                    'billing_address_id': _("Invalid billing address.")
                })
        
        # Get active cart
        try:
            cart = Cart.objects.get(user=user, is_active=True)
        except Cart.DoesNotExist:
            raise serializers.ValidationError({
                'non_field_errors': _("No active cart found.")
            })
        
        # Check if cart has items
        if not cart.items.exists():
            raise serializers.ValidationError({
                'non_field_errors': _("Your cart is empty.")
            })
        
        # Check if prescription is required and provided
        if cart.requires_prescription and not cart.prescription_file:
            raise serializers.ValidationError({
                'non_field_errors': _("Prescription is required for some items in your cart.")
            })
        
        # Check if any item is out of stock
        if cart.has_out_of_stock_items:
            raise serializers.ValidationError({
                'non_field_errors': _("Some items in your cart are out of stock.")
            })
        
        # Add validated objects to data
        data['cart'] = cart
        data['shipping_address'] = shipping_address
        data['billing_address'] = billing_address
        
        return data
    
    def create(self, validated_data):
        """Create order from cart"""
        cart = validated_data['cart']
        user = self.context['request'].user
        shipping_address = validated_data['shipping_address']
        billing_address = validated_data['billing_address']
        payment_method = validated_data['payment_method']
        customer_notes = validated_data.get('customer_notes', '')
        
        with transaction.atomic():
            # Create order
            order = Order.objects.create(
                user=user,
                status=Order.STATUS_PENDING,
                shipping_address=self._address_to_json(shipping_address),
                billing_address=self._address_to_json(billing_address),
                payment_method=payment_method,
                subtotal=cart.subtotal,
                discount_amount=cart.discount_amount,
                total_amount=cart.total,          # ✅ fixed field name
                customer_notes=customer_notes,
                prescription_file=cart.prescription_file,
                prescription_verified=cart.prescription_verified
            )
            
            # Add coupon info if applied
            if cart.coupon:
                order.coupon_code = cart.coupon.code
                order.coupon_discount = cart.discount_amount
                order.save(update_fields=['coupon_code', 'coupon_discount'])
            
            # Create order items from cart items
            for cart_item in cart.items.all():
                # Get product price
                if cart_item.variant:
                    unit_price = cart_item.variant.calculated_price
                else:
                    unit_price = cart_item.product.price
                
                # Create order item (compute totals inline, avoid variable)
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
                    total_price=unit_price * cart_item.quantity,   # ✅ fixed: total_price
                    requires_prescription=cart_item.product.prescription_required == 'required'
                )
                
                # Update product inventory
                if cart_item.product.track_inventory:
                    if cart_item.variant:
                        cart_item.variant.stock_quantity -= cart_item.quantity
                        cart_item.variant.save(update_fields=['stock_quantity'])
                    else:
                        cart_item.product.stock_quantity -= cart_item.quantity
                        cart_item.product.save(update_fields=['stock_quantity'])
            
            # Deactivate cart
            cart.is_active = False
            cart.save(update_fields=['is_active'])
            # TODO payment later.
            # # Create payment record for online payments
            # if payment_method == Order.PAYMENT_ONLINE:
            #     Payment.objects.create(
            #         order=order,
            #         amount=order.total_amount,
            #         method='online',      # adjust to your actual choice value
            #         status='pending'
            #     )
            # elif payment_method == Order.PAYMENT_COD:
            #     Payment.objects.create(
            #         order=order,
            #         amount=order.total_amount,
            #         method='cod',         # adjust to your actual choice value
            #         status='pending'
            #     )
            
            return order
        
    def _address_to_json(self, address):
        """Convert address model to JSON representation"""
        return {
            'recipient_name': f"{address.first_name} {address.last_name}".strip(),
            'recipient_phone': address.phone_number,
            'province': address.state_province,
            'city': address.city,
            'district': address.address_line_2 or '',
            'street_address': address.address_line_1,
            'postal_code': address.postal_code,
            'type': address.address_type
        }


class CancelOrderSerializer(serializers.Serializer):
    """Serializer for cancelling orders"""
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate order cancellation"""
        order = self.context['order']
        
        if not order.can_cancel:
            raise serializers.ValidationError({
                'non_field_errors': _("This order cannot be cancelled.")
            })
        
        return data


class ShipmentItemSerializer(serializers.ModelSerializer):
    """Serializer for shipment items"""
    product_name = serializers.CharField(source='order_item.product_name', read_only=True)
    
    class Meta:
        model = ShipmentItem
        fields = [
            'id', 'order_item', 'quantity', 'batch_number', 'product_name'
        ]
        read_only_fields = ['id']


class ShipmentSerializer(serializers.ModelSerializer):
    """Serializer for shipments"""
    items = ShipmentItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Shipment
        fields = [
            'id', 'order', 'tracking_number', 'carrier', 
            'status', 'status_display', 'shipped_at', 'delivered_at',
            'tracking_url', 'notes', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RefundItemSerializer(serializers.ModelSerializer):
    """Serializer for refund items"""
    product_name = serializers.CharField(source='order_item.product_name', read_only=True)
    
    class Meta:
        model = RefundItem
        fields = [
            'id', 'order_item', 'quantity', 'amount', 
            'reason', 'product_name'
        ]
        read_only_fields = ['id']


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for refunds"""
    items = RefundItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'order', 'amount', 'reason', 'status',
            'status_display', 'transaction_id', 'requested_at',
            'processed_at', 'notes', 'items'
        ]
        read_only_fields = [
            'id', 'status', 'transaction_id', 'requested_at',
            'processed_at', 'notes'
        ]


class CreateRefundSerializer(serializers.Serializer):
    """Serializer for creating refund requests"""
    order_id = serializers.UUIDField(required=True)
    reason = serializers.CharField(required=True)
    items = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )
    
    def validate(self, data):
        """Validate refund request data"""
        user = self.context['request'].user
        order_id = data['order_id']
        items = data['items']
        
        # Check if order exists and belongs to user
        try:
            order = Order.objects.get(id=order_id, user=user)
        except Order.DoesNotExist:
            raise serializers.ValidationError({
                'order_id': _("Order not found.")
            })
        
        # Check if order is paid
        if not order.is_paid:
            raise serializers.ValidationError({
                'order_id': _("Only paid orders can be refunded.")
            })
        
        # Validate refund items
        validated_items = []
        total_refund_amount = 0
        
        for item_data in items:
            if not all(k in item_data for k in ('order_item_id', 'quantity')):
                raise serializers.ValidationError({
                    'items': _("Each item must have order_item_id and quantity.")
                })
            
            try:
                order_item = OrderItem.objects.get(
                    id=item_data['order_item_id'],
                    order=order
                )
            except OrderItem.DoesNotExist:
                raise serializers.ValidationError({
                    'items': _(f"Item {item_data['order_item_id']} not found in this order.")
                })
            
            # Check if quantity is valid
            quantity = int(item_data['quantity'])
            if quantity <= 0 or quantity > order_item.quantity:
                raise serializers.ValidationError({
                    'items': _(f"Invalid quantity for item {order_item.product_name}.")
                })
            
            # Calculate refund amount for this item
            item_refund_amount = (order_item.total / order_item.quantity) * quantity
            
            validated_items.append({
                'order_item': order_item,
                'quantity': quantity,
                'amount': item_refund_amount,
                'reason': item_data.get('reason', '')
            })
            
            total_refund_amount += item_refund_amount
        
        # Check if there are items to refund
        if not validated_items:
            raise serializers.ValidationError({
                'items': _("No valid items to refund.")
            })
        
        # Add validated data
        data['order'] = order
        data['validated_items'] = validated_items
        data['total_amount'] = total_refund_amount
        
        return data
    
    def create(self, validated_data):
        """Create refund request"""
        order = validated_data['order']
        reason = validated_data['reason']
        total_amount = validated_data['total_amount']
        validated_items = validated_data['validated_items']
        
        with transaction.atomic():
            # Create refund
            refund = Refund.objects.create(
                order=order,
                amount=total_amount,
                reason=reason,
                status=Refund.STATUS_REQUESTED
            )
            
            # Create refund items
            for item_data in validated_items:
                RefundItem.objects.create(
                    refund=refund,
                    order_item=item_data['order_item'],
                    quantity=item_data['quantity'],
                    amount=item_data['amount'],
                    reason=item_data['reason'] or reason
                )
            
            return refund


