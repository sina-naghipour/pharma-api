from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import (
    PaymentMethod, PaymentGateway, Payment, PaymentRefund,
    SavedPaymentMethod, PaymentWebhook, PaymentDispute
)

@admin.register(PaymentMethod)
class PaymentMethodAdmin(ModelAdmin):
    list_display = ['name', 'payment_type', 'is_active', 'processing_fee', 'processing_fee_percentage']
    list_filter = ['payment_type', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(PaymentGateway)
class PaymentGatewayAdmin(ModelAdmin):
    list_display = ['name', 'gateway_type', 'is_active', 'is_test_mode', 'created_at']
    list_filter = ['gateway_type', 'is_active', 'is_test_mode']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ['id', 'user', 'amount', 'currency', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'currency', 'payment_method', 'created_at']
    search_fields = ['id', 'user__email', 'gateway_transaction_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'processed_at']
    raw_id_fields = ['user', 'order']

@admin.register(PaymentRefund)
class PaymentRefundAdmin(ModelAdmin):
    list_display = ['id', 'payment', 'amount', 'reason', 'status', 'created_at']
    list_filter = ['reason', 'status', 'created_at']
    search_fields = ['id', 'payment__id', 'gateway_refund_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'processed_at']
    raw_id_fields = ['payment', 'initiated_by']

@admin.register(SavedPaymentMethod)
class SavedPaymentMethodAdmin(ModelAdmin):
    list_display = ['user', 'payment_method', 'card_type', 'last_four_digits', 'is_default', 'created_at']
    list_filter = ['payment_method', 'card_type', 'is_default', 'is_verified']
    search_fields = ['user__email', 'last_four_digits', 'cardholder_name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user']

@admin.register(PaymentWebhook)
class PaymentWebhookAdmin(ModelAdmin):
    list_display = ['gateway', 'event_type', 'status', 'payment', 'created_at']
    list_filter = ['gateway', 'event_type', 'status', 'created_at']
    search_fields = ['webhook_id', 'event_type']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['payment']

@admin.register(PaymentDispute)
class PaymentDisputeAdmin(ModelAdmin):
    list_display = ['payment', 'gateway_dispute_id', 'amount', 'reason', 'status', 'created_at']
    list_filter = ['reason', 'status', 'created_at']
    search_fields = ['gateway_dispute_id', 'payment__id']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['payment']