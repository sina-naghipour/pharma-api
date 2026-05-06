import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, F


class Cart(models.Model):
    """Shopping cart model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carts',
        null=True,
        blank=True,
        verbose_name=_('User')
    )
    session_id = models.CharField(_('Session ID'), max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    # Cart status
    is_active = models.BooleanField(_('Active'), default=True)
    
    # Shipping and billing
    shipping_address = models.ForeignKey(
        'accounts.UserAddress',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shipping_carts',
        verbose_name=_('Shipping Address')
    )
    billing_address = models.ForeignKey(
        'accounts.UserAddress',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_carts',
        verbose_name=_('Billing Address')
    )
    
    # Prescription
    prescription_file = models.FileField(
        _('Prescription File'),
        upload_to='prescriptions/%Y/%m/',
        null=True,
        blank=True
    )
    prescription_verified = models.BooleanField(_('Prescription Verified'), default=False)
    prescription_verified_at = models.DateTimeField(_('Prescription Verified At'), null=True, blank=True)
    prescription_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_order_prescriptions',
        verbose_name=_('Verified By')
    )
    
    # Coupon
    coupon = models.ForeignKey(
        'promotions.Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carts',
        verbose_name=_('Applied Coupon')
    )
    
    class Meta:
        verbose_name = 'سبد خرید'
        verbose_name_plural = 'سبدهای خرید'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_id']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Cart {self.id}"
    
    @property
    def subtotal(self):
        return self.items.aggregate(
            subtotal=Sum(F('quantity') * F('unit_price'), default=0)
        )['subtotal'] or Decimal('0.00')
    
    @property
    def total_items(self):
        return self.items.aggregate(
            total=Sum('quantity', default=0)
        )['total'] or 0
    
    @property
    def requires_prescription(self):
        return self.items.filter(
            product__prescription_required='required'
        ).exists()
    
    @property
    def has_out_of_stock_items(self):
        for item in self.items.all():
            if not item.product.in_stock:
                return True
        return False
    
    @property
    def discount_amount(self):
        if not self.coupon:
            return Decimal('0.00')
        
        subtotal = self.subtotal
        
        if self.coupon.discount_type == 'percentage':
            return (subtotal * self.coupon.discount_value / 100).quantize(Decimal('0.01'))
        else:
            return min(self.coupon.discount_value, subtotal)
    
    @property
    def total(self):
        return max(self.subtotal - self.discount_amount, Decimal('0.00'))
    
    def merge_with(self, cart):
        for item in cart.items.all():
            existing_item = self.items.filter(product=item.product).first()
            if existing_item:
                existing_item.quantity += item.quantity
                existing_item.save()
            else:
                item.cart = self
                item.save()
        cart.delete()


class CartItem(models.Model):
    """Shopping cart item model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Cart')
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name=_('Product')
    )
    variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cart_items',
        verbose_name=_('Product Variant')
    )
    quantity = models.PositiveIntegerField(_('Quantity'), default=1)
    unit_price = models.DecimalField(
        _('Unit Price'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    added_at = models.DateTimeField(_('Added At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = 'آیتم سبد خرید'
        verbose_name_plural = 'آیتم‌های سبد خرید'
        ordering = ['-added_at']
        indexes = [
            models.Index(fields=['cart', 'product']),
        ]
        unique_together = ['cart', 'product', 'variant']
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in cart {self.cart.id}"
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price
    
    def save(self, *args, **kwargs):
        if not self.unit_price:
            if self.variant:
                self.unit_price = self.variant.calculated_price
            else:
                self.unit_price = self.product.price
        self.cart.updated_at = timezone.now()
        self.cart.save(update_fields=['updated_at'])
        super().save(*args, **kwargs)


class Order(models.Model):
    """Order model"""
    STATUS_PENDING = 'pending'
    STATUS_PAYMENT_PROCESSING = 'payment_processing'
    STATUS_PAID = 'paid'
    STATUS_PREPARING = 'preparing'
    STATUS_SHIPPED = 'shipped'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REFUNDED = 'refunded'
    STATUS_PARTIALLY_REFUNDED = 'partially_refunded'
    STATUS_FAILED = 'failed'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_PAYMENT_PROCESSING, _('Payment Processing')),
        (STATUS_PAID, _('Paid')),
        (STATUS_PREPARING, _('Preparing')),
        (STATUS_SHIPPED, _('Shipped')),
        (STATUS_DELIVERED, _('Delivered')),
        (STATUS_CANCELLED, _('Cancelled')),
        (STATUS_REFUNDED, _('Refunded')),
        (STATUS_PARTIALLY_REFUNDED, _('Partially Refunded')),
        (STATUS_FAILED, _('Failed')),
    ]
    
    PAYMENT_ONLINE = 'online'
    PAYMENT_COD = 'cod'
    PAYMENT_WALLET = 'wallet'
    
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_ONLINE, _('Online Payment')),
        (PAYMENT_COD, _('Cash on Delivery')),
        (PAYMENT_WALLET, _('Wallet')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(_('Order Number'), max_length=20, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='user_orders',
        verbose_name=_('User')
    )
    
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    paid_at = models.DateTimeField(_('Paid At'), null=True, blank=True)
    shipped_at = models.DateTimeField(_('Shipped At'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('Delivered At'), null=True, blank=True)
    cancelled_at = models.DateTimeField(_('Cancelled At'), null=True, blank=True)
    
    shipping_address = models.JSONField(_('Shipping Address'))
    billing_address = models.JSONField(_('Billing Address'))
    
    payment_method = models.CharField(
        _('Payment Method'),
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default=PAYMENT_ONLINE
    )
    payment_id = models.CharField(_('Payment ID'), max_length=100, blank=True)
    
    subtotal = models.DecimalField(
        _('Subtotal'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    shipping_cost = models.DecimalField(
        _('Shipping Cost'),
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    tax_amount = models.DecimalField(
        _('Tax Amount'),
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    discount_amount = models.DecimalField(
        _('Discount Amount'),
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    total_amount = models.DecimalField(
        _('Total Amount'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    coupon_code = models.CharField(_('Coupon Code'), max_length=50, blank=True)
    coupon_discount = models.DecimalField(
        _('Coupon Discount'),
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    prescription_file = models.FileField(
        _('Prescription File'),
        upload_to='prescriptions/%Y/%m/',
        null=True,
        blank=True
    )
    prescription_verified = models.BooleanField(_('Prescription Verified'), default=False)
    
    tracking_number = models.CharField(_('Tracking Number'), max_length=100, blank=True)
    shipping_carrier = models.CharField(_('Shipping Carrier'), max_length=100, blank=True)
    estimated_delivery = models.DateField(_('Estimated Delivery'), null=True, blank=True)
    
    customer_notes = models.TextField(_('Customer Notes'), blank=True)
    staff_notes = models.TextField(_('Staff Notes'), blank=True)
    
    class Meta:
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارش‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        if self.status == self.STATUS_PAID and not self.paid_at:
            self.paid_at = timezone.now()
        elif self.status == self.STATUS_SHIPPED and not self.shipped_at:
            self.shipped_at = timezone.now()
        elif self.status == self.STATUS_DELIVERED and not self.delivered_at:
            self.delivered_at = timezone.now()
        elif self.status == self.STATUS_CANCELLED and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)
    
    def _generate_order_number(self):
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4().int)[:5]
        return f"ORD-{date_str}-{random_str}"
    
    @property
    def is_paid(self):
        return self.status in [
            self.STATUS_PAID,
            self.STATUS_PREPARING,
            self.STATUS_SHIPPED,
            self.STATUS_DELIVERED
        ]
    
    @property
    def is_completed(self):
        return self.status == self.STATUS_DELIVERED
    
    @property
    def is_cancelled(self):
        return self.status == self.STATUS_CANCELLED
    
    @property
    def requires_prescription(self):
        return self.items.filter(
            product__prescription_required='required'
        ).exists()
    
    @property
    def can_cancel(self):
        return self.status in [
            self.STATUS_PENDING,
            self.STATUS_PAYMENT_PROCESSING,
            self.STATUS_PAID
        ]
    
    def cancel(self, reason=""):
        if not self.can_cancel:
            raise ValueError(_("This order cannot be cancelled."))
        self.status = self.STATUS_CANCELLED
        self.cancelled_at = timezone.now()
        self.staff_notes += f"\nCancelled: {reason}"
        self.save(update_fields=['status', 'cancelled_at', 'staff_notes', 'updated_at'])
        for item in self.items.all():
            if item.product.track_inventory:
                item.product.stock_quantity += item.quantity
                item.product.save(update_fields=['stock_quantity'])


class OrderItem(models.Model):
    """Order item model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Order')
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name=_('Product')
    )
    variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        verbose_name=_('Product Variant')
    )
    product_name = models.CharField(_('Product Name'), max_length=255)
    variant_name = models.CharField(_('Variant Name'), max_length=100, blank=True)
    sku = models.CharField(_('SKU'), max_length=50)
    quantity = models.PositiveIntegerField(_('Quantity'))
    unit_price = models.DecimalField(
        _('Unit Price'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    subtotal = models.DecimalField(
        _('Subtotal'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    discount_amount = models.DecimalField(
        _('Discount Amount'),
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    tax_amount = models.DecimalField(
        _('Tax Amount'),
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    total_price = models.DecimalField(
        _('Total Price'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    requires_prescription = models.BooleanField(_('Requires Prescription'), default=False)
    batch_number = models.CharField(_('Batch Number'), max_length=50, blank=True)
    expiry_date = models.DateField(_('Expiry Date'), null=True, blank=True)
    
    class Meta:
        verbose_name = 'آیتم سفارش'
        verbose_name_plural = 'آیتم‌های سفارش'
        ordering = ['product_name']
        indexes = [
            models.Index(fields=['order', 'product']),
            models.Index(fields=['sku']),
        ]
    
    def __str__(self):
        return f"{self.quantity} x {self.product_name} in order {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.product_name:
            self.product_name = self.product.name
        if self.variant and not self.variant_name:
            self.variant_name = self.variant.name
        if not self.sku:
            self.sku = self.variant.sku if self.variant else self.product.sku
        self.requires_prescription = self.product.prescription_required == 'required'
        if not self.subtotal:
            self.subtotal = self.unit_price * self.quantity
        if not self.total_price:
            self.total_price = self.subtotal - self.discount_amount + self.tax_amount
        super().save(*args, **kwargs)


class Shipment(models.Model):
    """Shipment model for order fulfillment"""
    STATUS_PROCESSING = 'processing'
    STATUS_SHIPPED = 'shipped'
    STATUS_DELIVERED = 'delivered'
    STATUS_FAILED = 'failed'
    STATUS_RETURNED = 'returned'
    
    STATUS_CHOICES = [
        (STATUS_PROCESSING, _('Processing')),
        (STATUS_SHIPPED, _('Shipped')),
        (STATUS_DELIVERED, _('Delivered')),
        (STATUS_FAILED, _('Failed')),
        (STATUS_RETURNED, _('Returned')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='shipments',
        verbose_name=_('Order')
    )
    tracking_number = models.CharField(_('Tracking Number'), max_length=100)
    carrier = models.CharField(_('Carrier'), max_length=100)
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PROCESSING
    )
    shipped_at = models.DateTimeField(_('Shipped At'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('Delivered At'), null=True, blank=True)
    tracking_url = models.URLField(_('Tracking URL'), blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = 'مرسوله'
        verbose_name_plural = 'مرسولات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['tracking_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Shipment {self.tracking_number} for order {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        if self.status == self.STATUS_SHIPPED and not self.shipped_at:
            self.shipped_at = timezone.now()
        if self.order.status not in [Order.STATUS_SHIPPED, Order.STATUS_DELIVERED]:
            self.order.status = Order.STATUS_SHIPPED
            self.order.shipped_at = timezone.now()
            self.order.save(update_fields=['status', 'shipped_at', 'updated_at'])
        elif self.status == self.STATUS_DELIVERED and not self.delivered_at:
            self.delivered_at = timezone.now()
        if self.order.status != Order.STATUS_DELIVERED:
            self.order.status = Order.STATUS_DELIVERED
            self.order.delivered_at = timezone.now()
            self.order.save(update_fields=['status', 'delivered_at', 'updated_at'])
        super().save(*args, **kwargs)


class ShipmentItem(models.Model):
    """Shipment item model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Shipment')
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name='shipment_items',
        verbose_name=_('Order Item')
    )
    quantity = models.PositiveIntegerField(_('Quantity'))
    batch_number = models.CharField(_('Batch Number'), max_length=50, blank=True)
    
    class Meta:
        verbose_name = 'آیتم مرسوله'
        verbose_name_plural = 'آیتم‌های مرسوله'
        indexes = [
            models.Index(fields=['shipment']),
            models.Index(fields=['order_item']),
        ]
    
    def __str__(self):
        return f"{self.quantity} x {self.order_item.product_name} in shipment {self.shipment.tracking_number}"


class Refund(models.Model):
    """Refund model"""
    STATUS_REQUESTED = 'requested'
    STATUS_PROCESSING = 'processing'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_COMPLETED = 'completed'
    
    STATUS_CHOICES = [
        (STATUS_REQUESTED, _('Requested')),
        (STATUS_PROCESSING, _('Processing')),
        (STATUS_APPROVED, _('Approved')),
        (STATUS_REJECTED, _('Rejected')),
        (STATUS_COMPLETED, _('Completed')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_refunds',
        verbose_name=_('Order')
    )
    amount = models.DecimalField(
        _('Amount'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    reason = models.TextField(_('Reason'))
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_REQUESTED
    )
    transaction_id = models.CharField(_('Transaction ID'), max_length=100, blank=True)
    refunded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_order_refunds',
        verbose_name=_('Refunded By')
    )
    requested_at = models.DateTimeField(_('Requested At'), auto_now_add=True)
    processed_at = models.DateTimeField(_('Processed At'), null=True, blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    
    class Meta:
        verbose_name = 'بازپرداخت سفارش'
        verbose_name_plural = 'بازپرداخت‌های سفارش'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Refund {self.id} for order {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        if self.status in [self.STATUS_APPROVED, self.STATUS_REJECTED, self.STATUS_COMPLETED] and not self.processed_at:
            self.processed_at = timezone.now()
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if not is_new and self.status == self.STATUS_COMPLETED:
            total_refunded = Refund.objects.filter(
                order=self.order,
                status=self.STATUS_COMPLETED
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            if total_refunded >= self.order.total_amount:
                self.order.status = Order.STATUS_REFUNDED
            else:
                self.order.status = Order.STATUS_PARTIALLY_REFUNDED
            self.order.save(update_fields=['status', 'updated_at'])


class RefundItem(models.Model):
    """Refund item model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refund = models.ForeignKey(
        Refund,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Refund')
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name='refund_items',
        verbose_name=_('Order Item')
    )
    quantity = models.PositiveIntegerField(_('Quantity'))
    amount = models.DecimalField(
        _('Amount'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    reason = models.CharField(_('Reason'), max_length=255)
    
    class Meta:
        verbose_name = 'آیتم بازپرداخت'
        verbose_name_plural = 'آیتم‌های بازپرداخت'
        indexes = [
            models.Index(fields=['refund']),
            models.Index(fields=['order_item']),
        ]
    
    def __str__(self):
        return f"{self.quantity} x {self.order_item.product_name} in refund {self.refund.id}"