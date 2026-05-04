# products/views.py
import logging
from django.db.models import Q, Avg, Count
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, filters, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Category,
    Manufacturer,
    Product,
    ProductImage,
    ProductVariant,
    Batch,
    ProductTag
)
from reviews.models import Review
from .serializers import (
    CategorySerializer,
    CategoryListSerializer,
    ManufacturerSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductImageSerializer,
    ProductVariantSerializer,
    BatchSerializer,
    ReviewSerializer
)
from .filters import ProductFilter
from .permissions import IsAdminOrReadOnly, IsOwnerOrAdminOrReadOnly

logger = logging.getLogger(__name__)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing product categories"""
    queryset = Category.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'order', 'created_at']
    ordering = ['order', 'name']
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return CategoryListSerializer
        return CategorySerializer
    
    @action(detail=False, methods=['get'])
    def root(self, request):
        """Get root categories (no parent)"""
        root_categories = Category.objects.filter(parent=None)
        serializer = CategorySerializer(root_categories, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def products(self, request, slug=None):
        """Get products in a category"""
        category = self.get_object()
        products = Product.objects.filter(
            categories=category,
            is_active=True
        )
        
        # Apply filters, search, and ordering
        product_filter = ProductFilter(request.GET, queryset=products)
        products = product_filter.qs
        
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(
                page, 
                many=True, 
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductListSerializer(
            products, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)


class ManufacturerViewSet(viewsets.ModelViewSet):
    """ViewSet for managing manufacturers"""
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'country']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    lookup_field = 'slug'
    
    @action(detail=True, methods=['get'])
    def products(self, request, slug=None):
        """Get products from a manufacturer"""
        manufacturer = self.get_object()
        products = Product.objects.filter(
            manufacturer=manufacturer,
            is_active=True
        )
        
        # Apply filters, search, and ordering
        product_filter = ProductFilter(request.GET, queryset=products)
        products = product_filter.qs
        
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(
                page, 
                many=True, 
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductListSerializer(
            products, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    """ViewSet for managing products"""
    queryset = Product.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'sku', 'barcode']
    ordering_fields = ['name', 'price', 'created_at', 'stock_quantity']
    ordering = ['-created_at']
    lookup_field = 'slug'
    
    def get_queryset(self):
        """Return queryset based on user and action"""
        queryset = Product.objects.all()
        
        # For list and retrieve actions, only show active products to non-admin users
        if self.action in ['list', 'retrieve'] and not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
            
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return ProductListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer
    
    def get_serializer_context(self):
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products"""
        featured_products = Product.objects.filter(
            is_active=True,
            is_featured=True
        )
        
        page = self.paginate_queryset(featured_products)
        if page is not None:
            serializer = ProductListSerializer(
                page, 
                many=True, 
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductListSerializer(
            featured_products, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def on_sale(self, request):
        """Get products on sale"""
        on_sale_products = Product.objects.filter(
            is_active=True,
            compare_price__isnull=False
        ).exclude(compare_price__lte=F('price'))
        
        page = self.paginate_queryset(on_sale_products)
        if page is not None:
            serializer = ProductListSerializer(
                page, 
                many=True, 
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductListSerializer(
            on_sale_products, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_review(self, request, slug=None):
        """Add a review to a product"""
        product = self.get_object()
        
        # Add product_id to serializer context
        context = self.get_serializer_context()
        context['product_id'] = product.id
        
        serializer = ReviewSerializer(data=request.data, context=context)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def similar(self, request, slug=None):
        """Get similar products"""
        product = self.get_object()
        
        # Get products in same categories
        similar_products = Product.objects.filter(
            categories__in=product.categories.all(),
            is_active=True
        ).exclude(id=product.id).distinct()
        
        # Limit to 10 products
        similar_products = similar_products[:10]
        
        serializer = ProductListSerializer(
            similar_products, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def variants(self, request, slug=None):
        """Get product variants"""
        product = self.get_object()
        variants = product.variants.filter(is_active=True)
        
        serializer = ProductVariantSerializer(variants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, slug=None):
        """Get product reviews"""
        product = self.get_object()
        
        # Only show approved reviews to non-admin users
        if not request.user.is_staff:
            reviews = product.reviews.filter(is_approved=True)
        else:
            reviews = product.reviews.all()
            
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class ProductImageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing product images"""
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        """Filter images by product if provided"""
        product_slug = self.request.query_params.get('product', None)
        if product_slug:
            return ProductImage.objects.filter(product__slug=product_slug)
        return ProductImage.objects.all()


class BatchViewSet(viewsets.ModelViewSet):
    """ViewSet for managing product batches"""
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product']
    ordering_fields = ['expiry_date', 'manufacturing_date', 'created_at']
    ordering = ['expiry_date']
    
    def get_queryset(self):
        """Filter batches by product if provided"""
        product_slug = self.request.query_params.get('product', None)
        if product_slug:
            return Batch.objects.filter(product__slug=product_slug)
        return Batch.objects.all()
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get batches expiring within 90 days"""
        batches = Batch.objects.filter(
            expiry_date__lte=timezone.now().date() + timezone.timedelta(days=90),
            expiry_date__gt=timezone.now().date()
        )
        
        serializer = BatchSerializer(batches, many=True)
        return Response(serializer.data)


class ReviewViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   viewsets.GenericViewSet):
    """ViewSet for managing reviews"""
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsOwnerOrAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'user', 'rating', 'is_approved']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter reviews based on user permissions"""
        if self.request.user.is_staff:
            return Review.objects.all()
        elif self.request.user.is_authenticated:
            # Regular users can see all approved reviews + their own
            return Review.objects.filter(
                Q(user=self.request.user)
            )
        # Anonymous users can only see approved reviews
        return Review.objects.filter(is_approved=True)
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Get reviews by current user"""
        if not request.user.is_authenticated:
            return Response(
                {"error": _("Authentication required")},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        reviews = Review.objects.filter(user=request.user)
        
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a review (admin only)"""
        if not request.user.is_staff:
            return Response(
                {"error": _("Admin privileges required")},
                status=status.HTTP_403_FORBIDDEN
            )
            
        review = self.get_object()
        review.save()
        
        serializer = self.get_serializer(review)
        return Response(serializer.data)