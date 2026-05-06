# orders/urls.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
 CartViewSet,
 OrderViewSet,
 ShipmentViewSet,
 RefundViewSet,
 PaymentViewSet
)

# Configure router for ViewSets
router = SimpleRouter()
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'shipments', ShipmentViewSet, basename='shipment')
router.register(r'refunds', RefundViewSet, basename='refund')
router.register(r'payments', PaymentViewSet, basename='payment')

# URL patterns with versioning
app_name = 'orders'

urlpatterns = [
 # Include router URLs
 path('', include(router.urls)),
]