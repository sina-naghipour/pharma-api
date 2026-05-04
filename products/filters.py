# products/filters.py
import django_filters
from django.db.models import Q
from .models import Product


class ProductFilter(django_filters.FilterSet):
    """Filter for Product model"""
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
    category = django_filters.CharFilter(method='filter_category')
    manufacturer = django_filters.CharFilter(field_name="manufacturer__slug")
    in_stock = django_filters.BooleanFilter(field_name="in_stock")
    on_sale = django_filters.BooleanFilter(method='filter_on_sale')
    prescription = django_filters.CharFilter(field_name="prescription_required")
    tag = django_filters.CharFilter(field_name="tags__slug")
    
    class Meta:
        model = Product
        fields = [
            'product_type', 'min_price', 'max_price', 'category',
            'manufacturer', 'in_stock', 'on_sale', 'prescription',
            'tag'
        ]
    
    def filter_category(self, queryset, name, value):
        """Filter by category slug, including child categories"""
        # Split comma-separated values
        if ',' in value:
            slugs = value.split(',')
            return queryset.filter(categories__slug__in=slugs).distinct()
        
        # Single category filter
        return queryset.filter(categories__slug=value)
    
    def filter_on_sale(self, queryset, name, value):
        """Filter products that are on sale"""
        if value:
            return queryset.filter(
                compare_price__isnull=False
            ).exclude(compare_price__lte=F('price'))
        return queryset