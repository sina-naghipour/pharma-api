# promotions/filters.py
import django_filters
from django.db.models import Q
from django.utils import timezone
from .models import Coupon, Promotion


class CouponFilter(django_filters.FilterSet):
    """Filter for Coupon model"""
    is_active = django_filters.BooleanFilter(field_name='is_active')
    is_valid = django_filters.BooleanFilter(method='filter_is_valid')
    is_expired = django_filters.BooleanFilter(method='filter_is_expired')
    valid_from_after = django_filters.DateTimeFilter(field_name='valid_from', lookup_expr='gte')
    valid_from_before = django_filters.DateTimeFilter(field_name='valid_from', lookup_expr='lte')
    valid_until_after = django_filters.DateTimeFilter(field_name='valid_until', lookup_expr='gte')
    valid_until_before = django_filters.DateTimeFilter(field_name='valid_until', lookup_expr='lte')
    discount_type = django_filters.ChoiceFilter(choices=Coupon.DISCOUNT_TYPE_CHOICES)
    min_discount_value = django_filters.NumberFilter(field_name='discount_value', lookup_expr='gte')
    max_discount_value = django_filters.NumberFilter(field_name='discount_value', lookup_expr='lte')
    
    class Meta:
        model = Coupon
        fields = [
            'is_active', 'is_valid', 'is_expired',
            'valid_from_after', 'valid_from_before',
            'valid_until_after', 'valid_until_before',
            'discount_type', 'min_discount_value', 'max_discount_value',
            'first_time_customers_only'
        ]
    
    def filter_is_valid(self, queryset, name, value):
        """Filter by validity status"""
        now = timezone.now()
        if value:  # is_valid=True
            return queryset.filter(
                is_active=True,
                valid_from__lte=now
            ).filter(
                Q(valid_until__isnull=True) | Q(valid_until__gt=now)
            )
        else:  # is_valid=False
            return queryset.filter(
                Q(is_active=False) |
                Q(valid_from__gt=now) |
                Q(valid_until__lte=now, valid_until__isnull=False)
            )
    
    def filter_is_expired(self, queryset, name, value):
        """Filter by expiration status"""
        now = timezone.now()
        if value:  # is_expired=True
            return queryset.filter(valid_until__lt=now, valid_until__isnull=False)
        else:  # is_expired=False
            return queryset.filter(
                Q(valid_until__isnull=True) | Q(valid_until__gte=now)
            )


class PromotionFilter(django_filters.FilterSet):
    """Filter for Promotion model"""
    is_active = django_filters.BooleanFilter(field_name='is_active')
    is_current = django_filters.BooleanFilter(method='filter_is_current')
    promotion_type = django_filters.ChoiceFilter(choices=Promotion.PROMOTION_TYPE_CHOICES)
    start_date_after = django_filters.DateTimeFilter(field_name='start_date', lookup_expr='gte')
    start_date_before = django_filters.DateTimeFilter(field_name='start_date', lookup_expr='lte')
    end_date_after = django_filters.DateTimeFilter(field_name='end_date', lookup_expr='gte')
    end_date_before = django_filters.DateTimeFilter(field_name='end_date', lookup_expr='lte')
    min_discount = django_filters.NumberFilter(field_name='discount_percentage', lookup_expr='gte')
    max_discount = django_filters.NumberFilter(field_name='discount_percentage', lookup_expr='lte')

    class Meta:
        model = Promotion
        fields = [
            'is_active', 'is_current', 'promotion_type',
            'start_date_after', 'start_date_before',
            'end_date_after', 'end_date_before',
            'min_discount', 'max_discount',
        ]
    
    def filter_is_current(self, queryset, name, value):
        """Filter by current status (active and within date range)"""
        now = timezone.now()
        if value:  # is_current=True
            return queryset.filter(
                is_active=True,
                start_date__lte=now
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gt=now)
            )
        else:  # is_current=False
            return queryset.filter(
                Q(is_active=False) |
                Q(start_date__gt=now) |
                Q(end_date__lte=now, end_date__isnull=False)
            )