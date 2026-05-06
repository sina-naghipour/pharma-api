from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Cart, CartItem, Order, OrderItem, Shipment, ShipmentItem, Refund, RefundItem
)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['total_price', 'added_at']
    fields = ['product', 'variant', 'quantity', 'unit_price', 'total_price', 'added_at']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'total_items', 'subtotal', 
        'is_active', 'updated_at'
    ]
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['user__email', 'session_id']
    readonly_fields = ['id', 'subtotal', 'total_items', 'created_at', 'updated_at']
    inlines = [CartItemInline]
    raw_id_fields = ['user', 'shipping_address', 'billing_address', 'coupon']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'session_id', 'is_active')
        }),
        ('Addresses', {
            'fields': ('shipping_address', 'billing_address')
        }),
        ('Prescription', {
            'fields': ('prescription_file', 'prescription_verified')
        }),
        ('Coupon', {
            'fields': ('coupon',)
        }),
        ('Summary', {
            'fields': ('subtotal', 'total_items')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'variant', 'quantity', 'unit_price', 'total_price']
    list_filter = ['added_at', 'updated_at']
    search_fields = ['product__name', 'cart__user__email']
    readonly_fields = ['id', 'total_price', 'added_at', 'updated_at']
    raw_id_fields = ['cart', 'product', 'variant']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['id', 'product_name', 'sku', 'subtotal', 'total_price']
    fields = [
        'product', 'variant', 'product_name', 'quantity', 
        'unit_price', 'subtotal', 'discount_amount', 'tax_amount', 'total_price'
    ]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'user', 'status', 'prescription_status',
        'total_amount', 'payment_method', 'created_at'
    ]
    list_filter = [
        'status', 'payment_method', 'created_at', 'updated_at',
        'prescription_verified'  # removed 'prescription_verified_at'
    ]
    search_fields = [
        'order_number', 'user__email', 'user__first_name',
        'user__last_name', 'payment_id'
    ]
    readonly_fields = [
        'id', 'order_number', 'created_at', 'updated_at',
        'paid_at', 'shipped_at', 'delivered_at', 'cancelled_at',
        'prescription_file_link'   # removed 'prescription_verified_at/_by'
    ]
    inlines = [OrderItemInline]
    raw_id_fields = ['user']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Order Information', {'fields': ('id', 'order_number', 'user', 'status')}),
        ('Payment Details', {'fields': ('payment_method', 'payment_id')}),
        ('Addresses', {'fields': ('shipping_address', 'billing_address')}),
        ('Order Amounts', {'fields': ('subtotal', 'shipping_cost', 'tax_amount', 'discount_amount', 'total_amount')}),
        ('Coupon Details', {'fields': ('coupon_code', 'coupon_discount'), 'classes': ('collapse',)}),
        # Temporary: remove the two new fields, keep only existing ones
        ('Prescription', {'fields': ('prescription_file_link', 'prescription_verified'), 'classes': ('collapse',)}),
        ('Shipping Information', {'fields': ('tracking_number', 'shipping_carrier', 'estimated_delivery'), 'classes': ('collapse',)}),
        ('Notes', {'fields': ('customer_notes', 'staff_notes'), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at', 'paid_at', 'shipped_at', 'delivered_at', 'cancelled_at'), 'classes': ('collapse',)}),
    )

    actions = [
        'mark_as_paid', 'mark_as_shipped', 'cancel_orders',
        'mark_prescription_verified', 'mark_prescription_rejected'
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('user',)
        return self.readonly_fields

    def prescription_status(self, obj):
        if obj.prescription_file:
            if obj.prescription_verified:
                return format_html('<span style="color: green;">✓ تأیید شده</span>')
            else:
                return format_html('<span style="color: orange;">⏳ در انتظار بررسی</span>')
        return '—'
    prescription_status.short_description = 'وضعیت نسخه'

    def prescription_file_link(self, obj):
        if obj.prescription_file:
            return format_html('<a href="{}" target="_blank">دانلود نسخه</a>', obj.prescription_file.url)
        return 'بدون نسخه'
    prescription_file_link.short_description = 'فایل نسخه'

    def mark_prescription_verified(self, request, queryset):
        updated = queryset.update(prescription_verified=True)
        self.message_user(request, f"{updated} نسخه تأیید شد.")
    mark_prescription_verified.short_description = "تأیید نسخه سفارش‌های انتخاب شده"

    def mark_prescription_rejected(self, request, queryset):
        updated = queryset.update(prescription_verified=False)
        self.message_user(request, f"{updated} نسخه رد شد.")
    mark_prescription_rejected.short_description = "رد نسخه سفارش‌های انتخاب شده"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'order', 'product_name', 'variant_name', 'quantity', 
        'unit_price', 'total_price'
    ]
    list_filter = ['requires_prescription', 'order__status']
    search_fields = [
        'product_name', 'sku', 'order__order_number',
        'order__user__email'
    ]
    readonly_fields = [
        'id', 'product_name', 'variant_name', 'sku', 
        'subtotal', 'total_price'
    ]
    raw_id_fields = ['order', 'product', 'variant']


class ShipmentItemInline(admin.TabularInline):
    model = ShipmentItem
    extra = 0
    fields = ['order_item', 'quantity', 'batch_number']


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = [
        'tracking_number', 'order', 'carrier', 'status', 
        'shipped_at', 'delivered_at'
    ]
    list_filter = ['status', 'carrier', 'shipped_at', 'delivered_at']
    search_fields = [
        'tracking_number', 'order__order_number', 
        'order__user__email', 'carrier'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'shipped_at', 'delivered_at'
    ]
    inlines = [ShipmentItemInline]
    raw_id_fields = ['order']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Shipment Information', {
            'fields': ('id', 'order', 'tracking_number', 'carrier', 'status')
        }),
        ('Tracking', {
            'fields': ('tracking_url', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ShipmentItem)
class ShipmentItemAdmin(admin.ModelAdmin):
    list_display = ['shipment', 'order_item', 'quantity', 'batch_number']
    search_fields = [
        'shipment__tracking_number', 'order_item__product_name',
        'batch_number'
    ]
    raw_id_fields = ['shipment', 'order_item']


class RefundItemInline(admin.TabularInline):
    model = RefundItem
    extra = 0
    fields = ['order_item', 'quantity', 'amount', 'reason']


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'order', 'amount', 'status', 'requested_at', 'processed_at'
    ]
    list_filter = ['status', 'requested_at', 'processed_at']
    search_fields = [
        'order__order_number', 'order__user__email', 
        'transaction_id', 'reason'
    ]
    readonly_fields = [
        'id', 'requested_at', 'processed_at'
    ]
    inlines = [RefundItemInline]
    raw_id_fields = ['order', 'refunded_by']
    date_hierarchy = 'requested_at'
    
    fieldsets = (
        ('Refund Information', {
            'fields': ('id', 'order', 'amount', 'status')
        }),
        ('Details', {
            'fields': ('reason', 'transaction_id', 'notes')
        }),
        ('Processing', {
            'fields': ('refunded_by', 'requested_at', 'processed_at')
        }),
    )


@admin.register(RefundItem)
class RefundItemAdmin(admin.ModelAdmin):
    list_display = ['refund', 'order_item', 'quantity', 'amount', 'reason']
    search_fields = [
        'refund__order__order_number', 'order_item__product_name', 'reason'
    ]
    raw_id_fields = ['refund', 'order_item']


# Custom admin actions (already included in OrderAdmin.actions list)
@admin.action(description='Mark selected orders as paid')
def mark_as_paid(modeladmin, request, queryset):
    updated = queryset.filter(status=Order.STATUS_PENDING).update(
        status=Order.STATUS_PAID
    )
    modeladmin.message_user(
        request, 
        f'{updated} order(s) were successfully marked as paid.'
    )


@admin.action(description='Mark selected orders as shipped')
def mark_as_shipped(modeladmin, request, queryset):
    updated = queryset.filter(status=Order.STATUS_PAID).update(
        status=Order.STATUS_SHIPPED
    )
    modeladmin.message_user(
        request, 
        f'{updated} order(s) were successfully marked as shipped.'
    )


@admin.action(description='Cancel selected orders')
def cancel_orders(modeladmin, request, queryset):
    cancelled_count = 0
    for order in queryset:
        if order.can_cancel:
            order.cancel("Cancelled by admin")
            cancelled_count += 1
    
    modeladmin.message_user(
        request, 
        f'{cancelled_count} order(s) were successfully cancelled.'
    )