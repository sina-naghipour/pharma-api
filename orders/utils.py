from django.db import transaction
from products.models import Product, ProductVariant
from rest_framework import serializers

def check_and_lock_stock(cart_items):
    """
    Lock product/variant rows and check stock availability.
    Raises ValidationError if any item has insufficient stock.
    """
    product_ids = []
    variant_ids = []
    for item in cart_items:
        if item.variant:
            variant_ids.append(item.variant.id)
        else:
            product_ids.append(item.product.id)
    
    # Lock rows in database to prevent race conditions
    if product_ids:
        Product.objects.select_for_update().filter(id__in=product_ids)
    if variant_ids:
        ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
    
    # Verify stock
    for item in cart_items:
        variant = item.variant
        product = item.product
        required = item.quantity
        if variant:
            if variant.track_inventory and variant.stock_quantity < required:
                raise serializers.ValidationError(
                    f"موجودی کافی برای {variant.name} وجود ندارد."
                )
        else:
            if product.track_inventory and product.stock_quantity < required:
                raise serializers.ValidationError(
                    f"موجودی کافی برای {product.name} وجود ندارد."
                )