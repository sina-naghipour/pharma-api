# promotions/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import (
    Coupon, CouponUsage, Promotion, PromotionProduct,
    RewardPoint, RewardPointTransaction, ReferralProgram, Referral
)


class CouponSerializer(serializers.ModelSerializer):
    """Serializer for Coupon model"""
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_fully_redeemed = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'description', 'discount_type', 
            'discount_value', 'minimum_order_amount', 'maximum_discount_amount',
            'usage_limit', 'usage_limit_per_user', 'used_count',
            'valid_from', 'valid_until', 'is_active',
            'first_time_customers_only', 'is_valid', 'is_expired', 'is_fully_redeemed',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'used_count', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate coupon data"""
        # Validate discount value
        discount_type = data.get('discount_type', self.instance.discount_type if self.instance else None)
        discount_value = data.get('discount_value', self.instance.discount_value if self.instance else None)
        
        if discount_type == Coupon.PERCENTAGE and discount_value > 100:
            raise serializers.ValidationError({
                'discount_value': _("Percentage discount cannot exceed 100%.")
            })
        
        # Validate dates
        valid_from = data.get('valid_from', self.instance.valid_from if self.instance else None)
        valid_until = data.get('valid_until', self.instance.valid_until if self.instance else None)
        
        if valid_from and valid_until and valid_from >= valid_until:
            raise serializers.ValidationError({
                'valid_until': _("End date must be after start date.")
            })
        
        return data


class CouponUsageSerializer(serializers.ModelSerializer):
    """Serializer for CouponUsage model"""
    coupon_code = serializers.CharField(source='coupon.code', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = CouponUsage
        fields = [
            'id', 'coupon', 'coupon_code', 'user', 'user_email',
            'order', 'order_number', 'discount_amount', 'used_at'
        ]
        read_only_fields = fields


class ValidateCouponSerializer(serializers.Serializer):
    """Serializer for validating coupon codes"""
    code = serializers.CharField(required=True)
    order_total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=True
    )


class PromotionProductSerializer(serializers.ModelSerializer):
    """Serializer for PromotionProduct model"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    
    class Meta:
        model = PromotionProduct
        fields = [
            'id', 'product', 'product_name', 'product_image',
            'discount_percentage', 'discount_price', 'discounted_price',
            'buy_quantity', 'get_quantity', 'get_discount_percentage',
            'display_order'
        ]
        read_only_fields = ['id', 'product_name', 'product_image', 'discounted_price']
    
    def get_product_image(self, obj):
        """Get product image URL"""
        request = self.context.get('request')
        primary_image = obj.product.images.filter(is_primary=True).first()
        if primary_image and request:
            return request.build_absolute_uri(primary_image.image.url)
        return None
    
    def get_discounted_price(self, obj):
        """Get calculated discounted price"""
        return obj.get_discount_price()


class PromotionSerializer(serializers.ModelSerializer):
    """Serializer for Promotion model"""
    promotion_products = PromotionProductSerializer(many=True, read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Promotion
        fields = [
            'id', 'name', 'description', 'promotion_type',
            'discount_percentage', 'start_date', 'end_date',
            'is_active', 'banner_image', 'banner_text',
            'highlight_color', 'is_valid', 'is_expired',
            'days_remaining', 'promotion_products',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate promotion data"""
        # Validate dates
        start_date = data.get('start_date', self.instance.start_date if self.instance else None)
        end_date = data.get('end_date', self.instance.end_date if self.instance else None)
        
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError({
                'end_date': _("End date must be after start date.")
            })
        
        return data


class PromotionProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating promotion products"""
    
    class Meta:
        model = PromotionProduct
        fields = [
            'product', 'discount_percentage', 'discount_price',
            'buy_quantity', 'get_quantity', 'get_discount_percentage',
            'display_order'
        ]
    
    def validate(self, data):
        """Validate promotion product data"""
        # Ensure either discount_percentage or discount_price is provided, not both
        if data.get('discount_percentage') is not None and data.get('discount_price') is not None:
            raise serializers.ValidationError({
                'non_field_errors': _("Please provide either discount percentage or discount price, not both.")
            })
        
        return data


class RewardPointTransactionSerializer(serializers.ModelSerializer):
    """Serializer for RewardPointTransaction model"""
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = RewardPointTransaction
        fields = [
            'id', 'points', 'transaction_type', 'transaction_type_display',
            'reason', 'reference', 'created_at'
        ]
        read_only_fields = fields


class RewardPointSerializer(serializers.ModelSerializer):
    """Serializer for RewardPoint model"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    tier = serializers.CharField(read_only=True)
    recent_transactions = serializers.SerializerMethodField()
    
    class Meta:
        model = RewardPoint
        fields = [
            'id', 'user', 'user_email', 'points_balance',
            'lifetime_points', 'last_activity_date', 'tier',
            'recent_transactions'
        ]
        read_only_fields = fields
    
    def get_recent_transactions(self, obj):
        """Get recent reward point transactions"""
        transactions = RewardPointTransaction.objects.filter(
            user=obj.user
        ).order_by('-created_at')[:5]
        
        return RewardPointTransactionSerializer(transactions, many=True).data


class ReferralProgramSerializer(serializers.ModelSerializer):
    """Serializer for ReferralProgram model"""
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ReferralProgram
        fields = [
            'id', 'name', 'description', 'referrer_reward_points',
            'referee_reward_points', 'referee_discount_percentage',
            'start_date', 'end_date', 'is_active', 'is_valid',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate referral program data"""
        # Validate dates
        start_date = data.get('start_date', self.instance.start_date if self.instance else None)
        end_date = data.get('end_date', self.instance.end_date if self.instance else None)
        
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError({
                'end_date': _("End date must be after start date.")
            })
        
        return data


class ReferralSerializer(serializers.ModelSerializer):
    """Serializer for Referral model"""
    referrer_email = serializers.EmailField(source='referrer.email', read_only=True)
    referee_user_email = serializers.EmailField(source='referee.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Referral
        fields = [
            'id', 'program', 'referrer', 'referrer_email',
            'referee_email', 'referee', 'referee_user_email',
            'status', 'status_display', 'code',
            'referred_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'referrer_email', 'referee_user_email',
            'status', 'status_display', 'code',
            'referred_at', 'completed_at'
        ]


class CreateReferralSerializer(serializers.Serializer):
    """Serializer for creating new referrals"""
    referee_email = serializers.EmailField(required=True)
    
    def validate_referee_email(self, value):
        """Validate referee email"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Check if email already exists
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                _("This email is already registered.")
            )
        
        # Check if this email has already been referred
        if Referral.objects.filter(referee_email=value, status=Referral.PENDING).exists():
            raise serializers.ValidationError(
                _("This email has already been invited.")
            )
        
        return value
    
    def create(self, validated_data):
        """Create a new referral"""
        from django.utils.crypto import get_random_string
        
        referee_email = validated_data['referee_email']
        user = self.context['request'].user
        
        # Get active referral program
        try:
            program = ReferralProgram.objects.filter(
                is_active=True,
                start_date__lte=timezone.now()
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=timezone.now())
            ).first()
            
            if not program:
                raise serializers.ValidationError(
                    _("No active referral program found.")
                )
        except ReferralProgram.DoesNotExist:
            raise serializers.ValidationError(
                _("No active referral program found.")
            )
        
        # Generate unique code
        code = f"REF-{get_random_string(8).upper()}"
        while Referral.objects.filter(code=code).exists():
            code = f"REF-{get_random_string(8).upper()}"
        
        # Create referral
        referral = Referral.objects.create(
            program=program,
            referrer=user,
            referee_email=referee_email,
            code=code
        )
        
        # TODO: Send invitation email to referee
        
        return referral


class RedeemReferralCodeSerializer(serializers.Serializer):
    """Serializer for redeeming referral codes"""
    code = serializers.CharField(required=True)
    
    def validate_code(self, value):
        """Validate referral code"""
        try:
            referral = Referral.objects.get(code=value, status=Referral.PENDING)
        except Referral.DoesNotExist:
            raise serializers.ValidationError(
                _("Invalid or expired referral code.")
            )
        
        # Check if program is still valid
        if not referral.program.is_valid:
            raise serializers.ValidationError(
                _("This referral program has expired.")
            )
        
        return value
    
    def redeem(self, user):
        """Redeem the referral code"""
        code = self.validated_data['code']
        
        try:
            referral = Referral.objects.get(code=code, status=Referral.PENDING)
            
            # Check if user email matches referee email
            if user.email.lower() != referral.referee_email.lower():
                raise serializers.ValidationError(
                    _("This referral code was not issued for your email address.")
                )
            
            # Mark referral as successful
            referral.mark_successful(user)
            
            return referral
        except Referral.DoesNotExist:
            raise serializers.ValidationError(
                _("Invalid or expired referral code.")
            )