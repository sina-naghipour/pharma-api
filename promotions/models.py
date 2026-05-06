import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings


class Coupon(models.Model):
    """Coupon model for order discounts"""
    PERCENTAGE = 'percentage'
    FIXED_AMOUNT = 'fixed'
    
    DISCOUNT_TYPE_CHOICES = [
        (PERCENTAGE, _('Percentage')),
        (FIXED_AMOUNT, _('Fixed Amount')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(_('Coupon Code'), max_length=50, unique=True)
    description = models.TextField(_('Description'), blank=True)
    
    discount_type = models.CharField(
        _('Discount Type'),
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default=PERCENTAGE
    )
    discount_value = models.DecimalField(
        _('Discount Value'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    minimum_order_amount = models.DecimalField(
        _('Minimum Order Amount'),
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    maximum_discount_amount = models.DecimalField(
        _('Maximum Discount Amount'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    usage_limit = models.PositiveIntegerField(
        _('Usage Limit'),
        null=True,
        blank=True,
        help_text=_('Maximum number of times this coupon can be used')
    )
    usage_limit_per_user = models.PositiveIntegerField(
        _('Usage Limit Per User'),
        null=True,
        blank=True,
        help_text=_('Maximum number of times a user can use this coupon')
    )
    used_count = models.PositiveIntegerField(_('Used Count'), default=0)
    
    valid_from = models.DateTimeField(_('Valid From'))
    valid_until = models.DateTimeField(_('Valid Until'), null=True, blank=True)
    
    is_active = models.BooleanField(_('Active'), default=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    first_time_customers_only = models.BooleanField(_('First Time Customers Only'), default=False)
    
    applicable_products = models.ManyToManyField(
        'products.Product',
        blank=True,
        related_name='applicable_coupons',
        verbose_name=_('Applicable Products')
    )
    applicable_categories = models.ManyToManyField(
        'products.Category',
        blank=True,
        related_name='applicable_coupons',
        verbose_name=_('Applicable Categories')
    )
    
    class Meta:
        verbose_name = 'کوپن'
        verbose_name_plural = 'کوپن‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.get_discount_type_display()} {self.discount_value}"
    
    @property
    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active and
            (self.valid_from is None or self.valid_from <= now) and
            (self.valid_until is None or now <= self.valid_until)
        )
    
    @property
    def is_expired(self):
        return self.valid_until is not None and self.valid_until < timezone.now()
    
    @property
    def is_fully_redeemed(self):
        return self.usage_limit and self.used_count >= self.usage_limit
    
    def calculate_discount(self, order_total):
        if not self.is_valid or order_total < self.minimum_order_amount:
            return Decimal('0.00')
        
        if self.discount_type == self.PERCENTAGE:
            discount = order_total * self.discount_value / 100
            if self.maximum_discount_amount:
                discount = min(discount, self.maximum_discount_amount)
        else:
            discount = min(self.discount_value, order_total)
        
        return discount.quantize(Decimal('0.01'))
    
    def can_be_used_by(self, user):
        if not user or not user.is_authenticated:
            return False
        
        if self.first_time_customers_only and user.orders.filter(status__in=[
            'paid', 'preparing', 'shipped', 'delivered'
        ]).exists():
            return False
        
        if self.usage_limit_per_user:
            user_usage_count = CouponUsage.objects.filter(
                coupon=self,
                user=user
            ).count()
            if user_usage_count >= self.usage_limit_per_user:
                return False
        
        return True
    
    def record_usage(self, user, order):
        self.used_count += 1
        self.save(update_fields=['used_count', 'updated_at'])
        
        CouponUsage.objects.create(
            coupon=self,
            user=user,
            order=order,
            discount_amount=order.coupon_discount
        )


class CouponUsage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name='usages',
        verbose_name=_('Coupon')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='coupon_usages',
        verbose_name=_('User')
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='coupon_usages',
        verbose_name=_('Order')
    )
    discount_amount = models.DecimalField(
        _('Discount Amount'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    used_at = models.DateTimeField(_('Used At'), auto_now_add=True)
    
    class Meta:
        verbose_name = 'استفاده از کوپن'
        verbose_name_plural = 'استفاده‌های کوپن'
        ordering = ['-used_at']
        indexes = [
            models.Index(fields=['coupon']),
            models.Index(fields=['user']),
            models.Index(fields=['order']),
        ]
        unique_together = ['coupon', 'order']
    
    def __str__(self):
        return f"{self.coupon.code} used by {self.user.email} on {self.used_at.date()}"


class Promotion(models.Model):
    SALE = 'sale'
    BOGO = 'bogo'
    BUNDLE = 'bundle'
    FLASH_SALE = 'flash_sale'
    CLEARANCE = 'clearance'
    NEW_ARRIVAL = 'new_arrival'
    
    PROMOTION_TYPE_CHOICES = [
        (SALE, _('Sale')),
        (BOGO, _('Buy One Get One')),
        (BUNDLE, _('Bundle Offer')),
        (FLASH_SALE, _('Flash Sale')),
        (CLEARANCE, _('Clearance')),
        (NEW_ARRIVAL, _('New Arrival')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Promotion Name'), max_length=255)
    description = models.TextField(_('Description'), blank=True)
    promotion_type = models.CharField(
        _('Promotion Type'),
        max_length=20,
        choices=PROMOTION_TYPE_CHOICES,
        default=SALE
    )
    
    discount_percentage = models.DecimalField(
        _('Discount Percentage'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True
    )
    
    start_date = models.DateTimeField(_('Start Date'))
    end_date = models.DateTimeField(_('End Date'), null=True, blank=True)
    
    is_active = models.BooleanField(_('Active'), default=True)
    
    banner_image = models.ImageField(
        _('Banner Image'),
        upload_to='promotions/%Y/%m/',
        blank=True
    )
    banner_text = models.CharField(_('Banner Text'), max_length=255, blank=True)
    highlight_color = models.CharField(_('Highlight Color'), max_length=20, blank=True)
    
    products = models.ManyToManyField(
        'products.Product',
        through='PromotionProduct',
        related_name='promotions',
        verbose_name=_('Products')
    )
    categories = models.ManyToManyField(
        'products.Category',
        blank=True,
        related_name='promotions',
        verbose_name=_('Categories')
    )
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = 'تبلیغات'
        verbose_name_plural = 'تبلیغات'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['promotion_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active and
            self.start_date <= now and
            (self.end_date is None or now <= self.end_date)
        )
    
    @property
    def is_expired(self):
        return self.end_date and timezone.now() > self.end_date
    
    @property
    def days_remaining(self):
        if not self.end_date:
            return None
        now = timezone.now()
        if now > self.end_date:
            return 0
        delta = self.end_date - now
        return delta.days


class PromotionProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name='promotion_products',
        verbose_name=_('Promotion')
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='product_promotions',
        verbose_name=_('Product')
    )
    
    discount_percentage = models.DecimalField(
        _('Discount Percentage'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True,
        help_text=_('Overrides promotion discount if set')
    )
    discount_price = models.DecimalField(
        _('Discount Price'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
        help_text=_('Fixed discount price')
    )
    
    buy_quantity = models.PositiveIntegerField(_('Buy Quantity'), default=1)
    get_quantity = models.PositiveIntegerField(_('Get Quantity'), default=0)
    get_discount_percentage = models.DecimalField(
        _('Get Item Discount Percentage'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=100,
        help_text=_('Discount for the free/discounted item in BOGO offers')
    )
    
    display_order = models.PositiveIntegerField(_('Display Order'), default=0)
    
    class Meta:
        verbose_name = 'محصول تبلیغاتی'
        verbose_name_plural = 'محصولات تبلیغاتی'
        ordering = ['display_order']
        unique_together = ['promotion', 'product']
    
    def __str__(self):
        return f"{self.promotion.name} - {self.product.name}"
    
    def get_discount_price(self):
        if self.discount_price:
            return self.discount_price
        
        if self.discount_percentage:
            discount_pct = self.discount_percentage
        elif self.promotion.discount_percentage:
            discount_pct = self.promotion.discount_percentage
        else:
            return None
        
        return self.product.price * (1 - discount_pct / 100)


class RewardPoint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reward_points',
        verbose_name=_('User')
    )
    points_balance = models.PositiveIntegerField(_('Points Balance'), default=0)
    lifetime_points = models.PositiveIntegerField(_('Lifetime Points'), default=0)
    last_activity_date = models.DateTimeField(_('Last Activity Date'), auto_now=True)
    
    class Meta:
        verbose_name = 'امتیاز جایزه'
        verbose_name_plural = 'امتیازات جایزه'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['points_balance']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.points_balance} points"
    
    def add_points(self, points, reason, reference=None):
        self.points_balance += points
        self.lifetime_points += points
        self.save(update_fields=['points_balance', 'lifetime_points', 'last_activity_date'])
        
        RewardPointTransaction.objects.create(
            user=self.user,
            points=points,
            transaction_type=RewardPointTransaction.EARNED,
            reason=reason,
            reference=reference
        )
    
    def deduct_points(self, points, reason, reference=None):
        if points > self.points_balance:
            raise ValueError(_("Insufficient points balance"))
        
        self.points_balance -= points
        self.save(update_fields=['points_balance', 'last_activity_date'])
        
        RewardPointTransaction.objects.create(
            user=self.user,
            points=points,
            transaction_type=RewardPointTransaction.REDEEMED,
            reason=reason,
            reference=reference
        )
    
    @property
    def tier(self):
        if self.lifetime_points >= 10000:
            return 'platinum'
        elif self.lifetime_points >= 5000:
            return 'gold'
        elif self.lifetime_points >= 1000:
            return 'silver'
        else:
            return 'bronze'


class RewardPointTransaction(models.Model):
    EARNED = 'earned'
    REDEEMED = 'redeemed'
    EXPIRED = 'expired'
    ADJUSTED = 'adjusted'
    
    TRANSACTION_TYPE_CHOICES = [
        (EARNED, _('Earned')),
        (REDEEMED, _('Redeemed')),
        (EXPIRED, _('Expired')),
        (ADJUSTED, _('Adjusted')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reward_transactions',
        verbose_name=_('User')
    )
    points = models.IntegerField(_('Points'))
    transaction_type = models.CharField(
        _('Transaction Type'),
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES
    )
    reason = models.CharField(_('Reason'), max_length=255)
    reference = models.CharField(_('Reference'), max_length=255, blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = 'تراکنش امتیاز'
        verbose_name_plural = 'تراکنش‌های امتیاز'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.transaction_type} {self.points} points"


class ReferralProgram(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Program Name'), max_length=255)
    description = models.TextField(_('Description'), blank=True)
    
    referrer_reward_points = models.PositiveIntegerField(
        _('Referrer Reward Points'),
        default=100
    )
    referee_reward_points = models.PositiveIntegerField(
        _('Referee Reward Points'),
        default=50
    )
    referee_discount_percentage = models.DecimalField(
        _('Referee Discount Percentage'),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=10
    )
    
    start_date = models.DateTimeField(_('Start Date'))
    end_date = models.DateTimeField(_('End Date'), null=True, blank=True)
    
    is_active = models.BooleanField(_('Active'), default=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = 'برنامه ارجاع'
        verbose_name_plural = 'برنامه‌های ارجاع'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active and
            self.start_date <= now and
            (self.end_date is None or now <= self.end_date)
        )


class Referral(models.Model):
    PENDING = 'pending'
    SUCCESSFUL = 'successful'
    EXPIRED = 'expired'
    
    STATUS_CHOICES = [
        (PENDING, _('Pending')),
        (SUCCESSFUL, _('Successful')),
        (EXPIRED, _('Expired')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(
        ReferralProgram,
        on_delete=models.PROTECT,
        related_name='referrals',
        verbose_name=_('Referral Program')
    )
    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referrals_made',
        verbose_name=_('Referrer')
    )
    referee_email = models.EmailField(_('Referee Email'))
    referee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals_received',
        verbose_name=_('Referee')
    )
    status = models.CharField(
        _('Status'),
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING
    )
    code = models.CharField(_('Referral Code'), max_length=20, unique=True)
    referred_at = models.DateTimeField(_('Referred At'), auto_now_add=True)
    completed_at = models.DateTimeField(_('Completed At'), null=True, blank=True)
    
    class Meta:
        verbose_name = 'ارجاع'
        verbose_name_plural = 'ارجاع‌ها'
        ordering = ['-referred_at']
        indexes = [
            models.Index(fields=['referrer']),
            models.Index(fields=['referee']),
            models.Index(fields=['code']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.referrer.email} referred {self.referee_email}"
    
    def mark_successful(self, referee):
        if self.status != self.PENDING:
            return
        
        self.referee = referee
        self.status = self.SUCCESSFUL
        self.completed_at = timezone.now()
        self.save(update_fields=['referee', 'status', 'completed_at'])
        
        if self.program.is_valid:
            try:
                referrer_points, created = RewardPoint.objects.get_or_create(user=self.referrer)
                referrer_points.add_points(
                    self.program.referrer_reward_points,
                    _("Successful referral"),
                    f"Referral:{self.id}"
                )
            except Exception as e:
                print(f"Failed to reward referrer: {e}")
            
            try:
                referee_points, created = RewardPoint.objects.get_or_create(user=referee)
                referee_points.add_points(
                    self.program.referee_reward_points,
                    _("Joining through referral"),
                    f"Referral:{self.id}"
                )
                
                from django.utils.crypto import get_random_string
                code = f"REF-{get_random_string(8).upper()}"
                
                Coupon.objects.create(
                    code=code,
                    description=_("Welcome discount from referral"),
                    discount_type=Coupon.PERCENTAGE,
                    discount_value=self.program.referee_discount_percentage,
                    valid_from=timezone.now(),
                    valid_until=timezone.now() + timezone.timedelta(days=30),
                    usage_limit=1,
                    usage_limit_per_user=1,
                    first_time_customers_only=True
                )
            except Exception as e:
                print(f"Failed to reward referee: {e}")