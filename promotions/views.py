# promotions/views.py
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, mixins, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Coupon, CouponUsage, Promotion, PromotionProduct,
    RewardPoint, RewardPointTransaction, ReferralProgram, Referral
)
from .serializers import (
    CouponSerializer, CouponUsageSerializer, ValidateCouponSerializer,
    PromotionSerializer, PromotionProductSerializer, PromotionProductCreateUpdateSerializer,
    RewardPointSerializer, RewardPointTransactionSerializer,
    ReferralProgramSerializer, ReferralSerializer, CreateReferralSerializer,
    RedeemReferralCodeSerializer
)
from .permissions import IsAdminOrReadOnly
from .filters import CouponFilter, PromotionFilter


class CouponViewSet(viewsets.ModelViewSet):
    """ViewSet for managing coupons"""
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CouponFilter
    search_fields = ['code', 'description']
    ordering_fields = ['created_at', 'valid_until', 'used_count']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def validate(self, request):
        """Validate a coupon code"""
        serializer = ValidateCouponSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.validated_data['code']
            order_total = serializer.validated_data['order_total']
            
            try:
                coupon = Coupon.objects.get(code=code, is_active=True)
                
                # Check if coupon is valid
                if not coupon.is_valid:
                    if coupon.is_expired:
                        return Response(
                            {'error': _('This coupon has expired.')},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    return Response(
                        {'error': _('This coupon is not valid.')},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if coupon is fully redeemed
                if coupon.is_fully_redeemed:
                    return Response(
                        {'error': _('This coupon has reached its usage limit.')},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if user can use this coupon
                if not coupon.can_be_used_by(request.user):
                    if coupon.first_time_customers_only:
                        return Response(
                            {'error': _('This coupon is for first-time customers only.')},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    return Response(
                        {'error': _('You have already used this coupon.')},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check minimum order amount
                if order_total < coupon.minimum_order_amount:
                    return Response(
                        {'error': _(f'This coupon requires a minimum order of {coupon.minimum_order_amount}.')},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Calculate discount
                discount_amount = coupon.calculate_discount(order_total)
                
                return Response({
                    'valid': True,
                    'discount_amount': discount_amount,
                    'total_after_discount': order_total - discount_amount,
                    'coupon': CouponSerializer(coupon).data
                })
                
            except Coupon.DoesNotExist:
                return Response(
                    {'error': _('Invalid coupon code.')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser])
    def usage(self, request, pk=None):
        """Get coupon usage history"""
        coupon = self.get_object()
        usages = coupon.usages.all().order_by('-used_at')
        
        page = self.paginate_queryset(usages)
        if page is not None:
            serializer = CouponUsageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CouponUsageSerializer(usages, many=True)
        return Response(serializer.data)


class PromotionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing promotions"""
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PromotionFilter
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-start_date']
    
    def get_queryset(self):
        """Filter promotions based on user role"""
        queryset = Promotion.objects.all()
        
        # For non-admin users, only show active and current promotions
        if not self.request.user.is_staff:
            now = timezone.now()
            queryset = queryset.filter(
                is_active=True,
                start_date__lte=now
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=now)
            )
        
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def add_product(self, request, pk=None):
        """Add a product to promotion"""
        promotion = self.get_object()
        serializer = PromotionProductCreateUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            # Check if product already exists in promotion
            product = serializer.validated_data['product']
            if PromotionProduct.objects.filter(promotion=promotion, product=product).exists():
                return Response(
                    {'error': _('This product is already in the promotion.')},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create promotion product
            promotion_product = serializer.save(promotion=promotion)
            
            # Return updated promotion
            response_serializer = PromotionProductSerializer(
                promotion_product,
                context={'request': request}
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def update_product(self, request, pk=None):
        """Update a product in promotion"""
        promotion = self.get_object()
        product_id = request.data.get('product_id')
        
        if not product_id:
            return Response(
                {'error': _('Product ID is required.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            promotion_product = PromotionProduct.objects.get(
                promotion=promotion,
                product_id=product_id
            )
        except PromotionProduct.DoesNotExist:
            return Response(
                {'error': _('Product not found in this promotion.')},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PromotionProductCreateUpdateSerializer(
            promotion_product,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            updated_product = serializer.save()
            response_serializer = PromotionProductSerializer(
                updated_product,
                context={'request': request}
            )
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def remove_product(self, request, pk=None):
        """Remove a product from promotion"""
        promotion = self.get_object()
        product_id = request.data.get('product_id')
        
        if not product_id:
            return Response(
                {'error': _('Product ID is required.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            promotion_product = PromotionProduct.objects.get(
                promotion=promotion,
                product_id=product_id
            )
            promotion_product.delete()
            return Response(
                {'success': _('Product removed from promotion.')},
                status=status.HTTP_200_OK
            )
        except PromotionProduct.DoesNotExist:
            return Response(
                {'error': _('Product not found in this promotion.')},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def active(self, request):
        """Get active promotions"""
        now = timezone.now()
        promotions = Promotion.objects.filter(
            is_active=True,
            start_date__lte=now
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        )
        
        page = self.paginate_queryset(promotions)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(promotions, many=True, context={'request': request})
        return Response(serializer.data)


class RewardPointViewSet(mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    """ViewSet for managing reward points"""
    serializer_class = RewardPointSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter reward points based on user role"""
        if self.request.user.is_staff:
            return RewardPoint.objects.all()
        return RewardPoint.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        """Get user's reward points"""
        if kwargs.get('pk') == 'me' or kwargs.get('pk') == request.user.id:
            # Get or create reward points for current user
            reward_points, created = RewardPoint.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(reward_points)
            return Response(serializer.data)
        
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Get reward point transactions"""
        # Handle 'me' identifier
        if pk == 'me':
            user = request.user
        else:
            # For admin users, allow viewing any user's transactions
            if not request.user.is_staff and str(request.user.id) != pk:
                return Response(
                    {'error': _('You can only view your own reward points.')},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get user from pk
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(pk=pk)
            except User.DoesNotExist:
                return Response(
                    {'error': _('User not found.')},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Get transactions
        transactions = RewardPointTransaction.objects.filter(user=user).order_by('-created_at')
        
        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = RewardPointTransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = RewardPointTransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class ReferralProgramViewSet(viewsets.ModelViewSet):
    """ViewSet for managing referral programs"""
    queryset = ReferralProgram.objects.all()
    serializer_class = ReferralProgramSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def get_queryset(self):
        """Filter referral programs based on user role"""
        queryset = ReferralProgram.objects.all()
        
        # For non-admin users, only show active programs
        if not self.request.user.is_staff:
            now = timezone.now()
            queryset = queryset.filter(
                is_active=True,
                start_date__lte=now
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=now)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def active(self, request):
        """Get active referral program"""
        now = timezone.now()
        program = ReferralProgram.objects.filter(
            is_active=True,
            start_date__lte=now
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        ).first()
        
        if program:
            serializer = self.get_serializer(program)
            return Response(serializer.data)
        
        return Response(
            {'error': _('No active referral program found.')},
            status=status.HTTP_404_NOT_FOUND
        )


class ReferralViewSet(mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    """ViewSet for managing referrals"""
    serializer_class = ReferralSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter referrals based on user role"""
        if self.request.user.is_staff:
            return Referral.objects.all()
        return Referral.objects.filter(referrer=self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return CreateReferralSerializer
        if self.action == 'redeem':
            return RedeemReferralCodeSerializer
        return ReferralSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new referral"""
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            referral = serializer.save()
            
            # Return created referral
            response_serializer = ReferralSerializer(referral)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def redeem(self, request):
        """Redeem a referral code"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                referral = serializer.redeem(request.user)
                
                # Return redeemed referral
                response_serializer = ReferralSerializer(referral)
                return Response(response_serializer.data)
            except serializers.ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def my_referrals(self, request):
        """Get user's referrals"""
        referrals = Referral.objects.filter(referrer=request.user).order_by('-referred_at')
        
        page = self.paginate_queryset(referrals)
        if page is not None:
            serializer = ReferralSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ReferralSerializer(referrals, many=True)
        return Response(serializer.data)