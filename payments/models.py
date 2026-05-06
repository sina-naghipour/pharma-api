from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class PaymentMethod(models.Model):
    """Payment methods available in the system"""
    PAYMENT_TYPES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('bank_transfer', 'Bank Transfer'),
        ('wallet', 'Digital Wallet'),
        ('cod', 'Cash on Delivery'),
    ]
    
    name = models.CharField(max_length=100)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    requires_verification = models.BooleanField(default=False)
    processing_fee = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    processing_fee_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    min_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    max_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    gateway_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'روش پرداخت'
        verbose_name_plural = 'روش‌های پرداخت'
    
    def __str__(self):
        return self.name
    
    def calculate_processing_fee(self, amount):
        fee = self.processing_fee
        if self.processing_fee_percentage > 0:
            fee += (amount * self.processing_fee_percentage / 100)
        return fee


class PaymentGateway(models.Model):
    GATEWAY_TYPES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('razorpay', 'Razorpay'),
        ('square', 'Square'),
        ('braintree', 'Braintree'),
        ('authorize_net', 'Authorize.Net'),
    ]
    
    name = models.CharField(max_length=100)
    gateway_type = models.CharField(max_length=20, choices=GATEWAY_TYPES)
    is_active = models.BooleanField(default=True)
    is_test_mode = models.BooleanField(default=True)
    api_key = models.CharField(max_length=255, blank=True)
    secret_key = models.CharField(max_length=255, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    endpoint_url = models.URLField(blank=True)
    configuration = models.JSONField(default=dict, blank=True)
    supported_currencies = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'درگاه پرداخت'
        verbose_name_plural = 'درگاه‌های پرداخت'
    
    def __str__(self):
        return f"{self.name} ({'Test' if self.is_test_mode else 'Live'})"


class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='payments')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.PROTECT, null=True, blank=True)
    
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='USD')
    processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    gateway_transaction_id = models.CharField(max_length=255, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    billing_address = models.TextField()
    payment_details = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order']),
            models.Index(fields=['gateway_transaction_id']),
        ]
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت‌ها'
    
    def __str__(self):
        return f"Payment {self.id} - {self.amount} {self.currency}"
    
    def save(self, *args, **kwargs):
        if not self.net_amount:
            self.net_amount = self.amount - self.processing_fee
        super().save(*args, **kwargs)


class PaymentRefund(models.Model):
    REFUND_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    REFUND_REASON = [
        ('customer_request', 'Customer Request'),
        ('order_cancelled', 'Order Cancelled'),
        ('product_return', 'Product Return'),
        ('duplicate_payment', 'Duplicate Payment'),
        ('fraudulent', 'Fraudulent'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    initiated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_refunds')
    
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    reason = models.CharField(max_length=20, choices=REFUND_REASON)
    notes = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=REFUND_STATUS, default='pending')
    gateway_refund_id = models.CharField(max_length=255, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'بازپرداخت'
        verbose_name_plural = 'بازپرداخت‌ها'
    
    def __str__(self):
        return f"Refund {self.id} - {self.amount}"


class SavedPaymentMethod(models.Model):
    CARD_TYPES = [
        ('visa', 'Visa'),
        ('mastercard', 'MasterCard'),
        ('amex', 'American Express'),
        ('discover', 'Discover'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_payment_methods')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    
    card_type = models.CharField(max_length=20, choices=CARD_TYPES, blank=True)
    last_four_digits = models.CharField(max_length=4, blank=True)
    expiry_month = models.PositiveIntegerField(null=True, blank=True)
    expiry_year = models.PositiveIntegerField(null=True, blank=True)
    cardholder_name = models.CharField(max_length=100, blank=True)
    
    account_identifier = models.CharField(max_length=100, blank=True)
    
    gateway_token = models.CharField(max_length=255, blank=True)
    gateway_customer_id = models.CharField(max_length=255, blank=True)
    
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        unique_together = ['user', 'gateway_token']
        verbose_name = 'روش پرداخت ذخیره شده'
        verbose_name_plural = 'روش‌های پرداخت ذخیره شده'
    
    def __str__(self):
        if self.last_four_digits:
            return f"{self.card_type.title()} ending in {self.last_four_digits}"
        return f"{self.payment_method.name} - {self.account_identifier}"


class PaymentWebhook(models.Model):
    WEBHOOK_STATUS = [
        ('received', 'Received'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
        ('ignored', 'Ignored'),
    ]
    
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE, related_name='webhooks')
    webhook_id = models.CharField(max_length=255, blank=True)
    event_type = models.CharField(max_length=100)
    
    payload = models.JSONField()
    headers = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(max_length=20, choices=WEBHOOK_STATUS, default='received')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True, related_name='webhooks')
    
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['gateway', 'event_type']),
            models.Index(fields=['webhook_id']),
        ]
        verbose_name = 'وب‌هوک پرداخت'
        verbose_name_plural = 'وب‌هوک‌های پرداخت'
    
    def __str__(self):
        return f"Webhook {self.event_type} from {self.gateway.name}"


class PaymentDispute(models.Model):
    DISPUTE_STATUS = [
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('accepted', 'Accepted'),
    ]
    
    DISPUTE_REASON = [
        ('fraudulent', 'Fraudulent'),
        ('subscription_cancelled', 'Subscription Cancelled'),
        ('product_unacceptable', 'Product Unacceptable'),
        ('product_not_received', 'Product Not Received'),
        ('duplicate', 'Duplicate'),
        ('credit_not_processed', 'Credit Not Processed'),
        ('general', 'General'),
        ('other', 'Other'),
    ]
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='disputes')
    gateway_dispute_id = models.CharField(max_length=255)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    
    reason = models.CharField(max_length=30, choices=DISPUTE_REASON)
    status = models.CharField(max_length=20, choices=DISPUTE_STATUS, default='open')
    
    evidence_due_by = models.DateTimeField(null=True, blank=True)
    evidence_details = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'اختلاف پرداخت'
        verbose_name_plural = 'اختلافات پرداخت'
    
    def __str__(self):
        return f"Dispute {self.gateway_dispute_id} - {self.amount} {self.currency}"