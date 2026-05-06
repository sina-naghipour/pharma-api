from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    Coupon, CouponUsage, Promotion, PromotionProduct,
    RewardPoint, RewardPointTransaction, ReferralProgram, Referral
)


class CouponUsageInline(TabularInline):
    model = CouponUsage
    extra = 0
    readonly_fields = ['user', 'order', 'discount_amount', 'used_at']
    fields = ['user', 'order', 'discount_amount', 'used_at']
    can_delete = False


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = [
        'code', 'discount_type', 'discount_value', 'valid_from',
        'valid_until', 'is_active', 'used_count', 'is_valid'
    ]
    list_filter = [
        'is_active', 'discount_type', 'valid_from', 'valid_until',
        'first_time_customers_only'
    ]
    search_fields = ['code', 'description']
    readonly_fields = ['used_count', 'is_valid', 'is_expired', 'is_fully_redeemed']
    inlines = [CouponUsageInline]
    filter_horizontal = ['applicable_products', 'applicable_categories']
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'description', 'is_active')
        }),
        ('Discount Settings', {
            'fields': ('discount_type', 'discount_value', 'minimum_order_amount', 'maximum_discount_amount')
        }),
        ('Usage Limits', {
            'fields': ('usage_limit', 'usage_limit_per_user', 'used_count', 'first_time_customers_only')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('Applicable Items', {
            'fields': ('applicable_products', 'applicable_categories')
        }),
        ('Status', {
            'fields': ('is_valid', 'is_expired', 'is_fully_redeemed')
        }),
    )


class PromotionProductInline(TabularInline):
    model = PromotionProduct
    extra = 1
    fields = [
        'product', 'discount_percentage', 'discount_price',
        'buy_quantity', 'get_quantity', 'get_discount_percentage',
        'display_order'
    ]


@admin.register(Promotion)
class PromotionAdmin(ModelAdmin):
    list_display = [
        'name', 'promotion_type', 'discount_percentage', 'start_date', 
        'end_date', 'is_active', 'is_valid'
    ]
    list_filter = ['is_active', 'promotion_type', 'start_date', 'end_date']
    search_fields = ['name', 'description']
    readonly_fields = ['is_valid', 'is_expired', 'days_remaining']
    inlines = [PromotionProductInline]
    filter_horizontal = ['categories']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'promotion_type', 'is_active')
        }),
        ('Discount Settings', {
            'fields': ('discount_percentage',)
        }),
        ('Validity Period', {
            'fields': ('start_date', 'end_date')
        }),
        ('Status', {
            'fields': ('is_valid', 'is_expired', 'days_remaining')
        }),
        ('Display Options', {
            'fields': ('banner_image', 'banner_text', 'highlight_color')
        }),
        ('Categories', {
            'fields': ('categories',)
        }),
    )


class RewardPointTransactionInline(TabularInline):
    model = RewardPointTransaction
    extra = 0
    readonly_fields = ['transaction_type', 'points', 'reason', 'reference', 'created_at']
    fields = ['transaction_type', 'points', 'reason', 'reference', 'created_at']
    can_delete = False
    max_num = 0


@admin.register(RewardPoint)
class RewardPointAdmin(ModelAdmin):
    list_display = ['user', 'points_balance', 'lifetime_points', 'tier', 'last_activity_date']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['lifetime_points', 'tier', 'last_activity_date']
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Points', {
            'fields': ('points_balance', 'lifetime_points')
        }),
        ('Status', {
            'fields': ('tier', 'last_activity_date')
        }),
    )


@admin.register(RewardPointTransaction)
class RewardPointTransactionAdmin(ModelAdmin):
    list_display = ['user', 'transaction_type', 'points', 'reason', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user__email', 'reason', 'reference']
    readonly_fields = ['created_at']


@admin.register(ReferralProgram)
class ReferralProgramAdmin(ModelAdmin):
    list_display = [
        'name', 'referrer_reward_points', 'referee_reward_points',
        'referee_discount_percentage', 'is_active', 'is_valid'
    ]
    list_filter = ['is_active', 'start_date', 'end_date']
    search_fields = ['name', 'description']
    readonly_fields = ['is_valid']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Reward Settings', {
            'fields': ('referrer_reward_points', 'referee_reward_points', 'referee_discount_percentage')
        }),
        ('Validity Period', {
            'fields': ('start_date', 'end_date', 'is_valid')
        }),
    )


@admin.register(Referral)
class ReferralAdmin(ModelAdmin):
    list_display = [
        'code', 'referrer', 'referee_email', 'referee',
        'status', 'referred_at', 'completed_at'
    ]
    list_filter = ['status', 'referred_at', 'completed_at']
    search_fields = [
        'code', 'referrer__email', 'referee_email',
        'referee__email'
    ]
    readonly_fields = ['code', 'referred_at', 'completed_at']
    fieldsets = (
        ('Referral Information', {
            'fields': ('program', 'code', 'referrer', 'referee_email')
        }),
        ('Status', {
            'fields': ('status', 'referee', 'referred_at', 'completed_at')
        }),
    )


# Custom admin actions
@admin.action(description='Activate selected promotions')
def activate_promotions(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(
        request, 
        f'{updated} promotion(s) were successfully activated.'
    )


@admin.action(description='Deactivate selected promotions')
def deactivate_promotions(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(
        request, 
        f'{updated} promotion(s) were successfully deactivated.'
    )


@admin.action(description='Activate selected coupons')
def activate_coupons(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(
        request, 
        f'{updated} coupon(s) were successfully activated.'
    )


@admin.action(description='Deactivate selected coupons')
def deactivate_coupons(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(
        request, 
        f'{updated} coupon(s) were successfully deactivated.'
    )


# Add actions to admin classes
PromotionAdmin.actions = [activate_promotions, deactivate_promotions]
CouponAdmin.actions = [activate_coupons, deactivate_coupons]