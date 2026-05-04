# products/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ManufacturerViewSet,
    ProductViewSet,
    ProductImageViewSet,
    BatchViewSet,
    ReviewViewSet
)

# Configure router for ViewSets
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'manufacturers', ManufacturerViewSet, basename='manufacturer')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'images', ProductImageViewSet, basename='product-image')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'reviews', ReviewViewSet, basename='review')

# URL patterns with versioning
app_name = 'products'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
]