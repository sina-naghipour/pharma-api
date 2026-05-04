# orders/filters.py
import django_filters
from django.db.models import Q
from .models import Order


class OrderFilter(django_filters.FilterSet):
    """Filter for Order model"""
    min_total = django_filters.NumberFilter(field_name="total", lookup_expr='gte')
    max_total = django_filters.NumberFilter(field_name="total", lookup_expr='lte')
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = Order
        fields = [
            'status', 'payment_method', 'min_total', 'max_total',
            'created_after', 'created_before'
        ]
    
    def filter_search(self, queryset, name, value):
        """Filter by order number or tracking number"""
        return queryset.filter(
            Q(order_number__icontains=value) |
            Q(tracking_number__icontains=value)
        )