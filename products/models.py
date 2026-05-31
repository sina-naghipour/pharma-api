import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.utils import timezone
from django.db.models import Q


class Category(models.Model):
    """Product category model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Name'), max_length=100)
    slug = models.SlugField(_('Slug'), max_length=120, unique=True)
    description = models.TextField(_('Description'), blank=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children',
        verbose_name=_('Parent Category')
    )
    image = models.ImageField(
        _('Image'), 
        upload_to='categories/%Y/%m/', 
        blank=True
    )
    is_active = models.BooleanField(_('Active'), default=True)
    order = models.PositiveIntegerField(_('Display Order'), default=0)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = 'دسته‌بندی'
        verbose_name_plural = 'دسته‌بندی‌ها'
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.name

    @property
    def full_path(self):
        path = [self.name]
        parent = self.parent
        while parent:
            path.append(parent.name)
            parent = parent.parent
        return ' > '.join(reversed(path))


class Manufacturer(models.Model):
    """Pharmaceutical manufacturer model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Name'), max_length=100)
    slug = models.SlugField(_('Slug'), max_length=120, unique=True)
    description = models.TextField(_('Description'), blank=True)
    logo = models.ImageField(
        _('Logo'), 
        upload_to='manufacturers/%Y/%m/', 
        blank=True
    )
    country = models.CharField(_('Country'), max_length=100, blank=True)
    website = models.URLField(_('Website'), blank=True)
    founded_year = models.PositiveIntegerField(_('Founded Year'), null=True, blank=True)
    is_approved = models.BooleanField(_('Approved'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = 'تولیدکننده'
        verbose_name_plural = 'تولیدکنندگان'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    """Base product model for all pharmaceutical products"""
    MEDICATION = 'medication'
    MEDICAL_SUPPLY = 'medical_supply'
    SUPPLEMENT = 'supplement'
    EQUIPMENT = 'equipment'
    PERSONAL_CARE = 'personal_care'
    
    PRODUCT_TYPE_CHOICES = [
        (MEDICATION, _('Medication')),
        (MEDICAL_SUPPLY, _('Medical Supply')),
        (SUPPLEMENT, _('Supplement')),
        (EQUIPMENT, _('Equipment')),
        (PERSONAL_CARE, _('Personal Care')),
    ]
    
    NO_PRESCRIPTION = 'none'
    PRESCRIPTION_REQUIRED = 'required'
    PRESCRIPTION_OPTIONAL = 'optional'
    
    PRESCRIPTION_CHOICES = [
        (NO_PRESCRIPTION, _('No Prescription')),
        (PRESCRIPTION_REQUIRED, _('Prescription Required')),
        (PRESCRIPTION_OPTIONAL, _('Prescription Optional')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Name'), max_length=255)
    slug = models.SlugField(_('Slug'), max_length=280, unique=True)
    product_type = models.CharField(
        _('Product Type'),
        max_length=20,
        choices=PRODUCT_TYPE_CHOICES,
        default=MEDICATION
    )
    sku = models.CharField(_('SKU'), max_length=50, unique=True)
    barcode = models.CharField(_('Barcode'), max_length=50, blank=True)
    description = models.TextField(_('Description'), blank=True)
    short_description = models.TextField(_('Short Description'), blank=True)
    categories = models.ManyToManyField(
        Category,
        related_name='products',
        verbose_name=_('Categories')
    )
    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_('Manufacturer')
    )
    max_order_quantity = models.PositiveIntegerField(
        _('Maximum Order Quantity'),
        default=0,
        help_text=_('Maximum quantity a user can order in a single purchase. 0 = unlimited.')
    )
    price = models.DecimalField(
        _('Price'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    compare_price = models.DecimalField(
        _('Compare at Price'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        help_text=_('Original price before discount')
    )
    cost_price = models.DecimalField(
        _('Cost Price'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True
    )
    tax_class = models.CharField(_('Tax Class'), max_length=50, blank=True)
    is_taxable = models.BooleanField(_('Taxable'), default=True)
    prescription_required = models.CharField(
        _('Prescription Required'),
        max_length=10,
        choices=PRESCRIPTION_CHOICES,
        default=NO_PRESCRIPTION
    )
    track_inventory = models.BooleanField(_('Track Inventory'), default=True)
    in_stock = models.BooleanField(_('In Stock'), default=True)
    stock_quantity = models.IntegerField(
        _('Stock Quantity'),
        default=0,
        validators=[MinValueValidator(0)]
    )
    low_stock_threshold = models.PositiveIntegerField(
        _('Low Stock Threshold'),
        default=5
    )
    backorder_allowed = models.BooleanField(_('Backorder Allowed'), default=False)
    weight = models.DecimalField(
        _('Weight (g)'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True
    )
    length = models.DecimalField(
        _('Length (cm)'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True
    )
    width = models.DecimalField(
        _('Width (cm)'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True
    )
    height = models.DecimalField(
        _('Height (cm)'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True
    )
    is_active = models.BooleanField(_('Active'), default=True)
    is_featured = models.BooleanField(_('Featured'), default=False)
    is_approved = models.BooleanField(_('Approved'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    published_at = models.DateTimeField(_('Published At'), null=True, blank=True)
    meta_title = models.CharField(_('Meta Title'), max_length=100, blank=True)
    meta_description = models.TextField(_('Meta Description'), blank=True)
    
    class Meta:
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['sku']),
            models.Index(fields=['product_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.is_active and not self.published_at:
            self.published_at = timezone.now()
        if self.track_inventory:
            self.in_stock = self.stock_quantity > 0 or self.backorder_allowed
        super().save(*args, **kwargs)
    
    @property
    def discount_percentage(self):
        if self.compare_price and self.compare_price > self.price:
            return int(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0
    
    @property
    def is_on_sale(self):
        return self.compare_price is not None and self.compare_price > self.price
    
    @property
    def is_low_stock(self):
        if not self.track_inventory:
            return False
        return 0 < self.stock_quantity <= self.low_stock_threshold
    
    @property
    def is_out_of_stock(self):
        if not self.track_inventory:
            return False
        return self.stock_quantity <= 0


class Medication(models.Model):
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='medication_details',
        verbose_name=_('Product')
    )
    generic_name = models.CharField(_('Generic Name'), max_length=255)
    dosage_form = models.CharField(_('Dosage Form'), max_length=100)
    strength = models.CharField(_('Strength'), max_length=100)
    route_of_administration = models.CharField(_('Route of Administration'), max_length=100)
    therapeutic_class = models.CharField(_('Therapeutic Class'), max_length=255, blank=True)
    atc_code = models.CharField(_('ATC Code'), max_length=10, blank=True)
    registration_number = models.CharField(_('Registration Number'), max_length=100, blank=True)
    indications = models.TextField(_('Indications'), blank=True)
    contraindications = models.TextField(_('Contraindications'), blank=True)
    side_effects = models.TextField(_('Side Effects'), blank=True)
    warnings = models.TextField(_('Warnings'), blank=True)
    storage_conditions = models.CharField(_('Storage Conditions'), max_length=255, blank=True)
    pregnancy_category = models.CharField(_('Pregnancy Category'), max_length=2, blank=True)
    active_ingredients = models.TextField(_('Active Ingredients'), blank=True)
    inactive_ingredients = models.TextField(_('Inactive Ingredients'), blank=True)
    
    class Meta:
        verbose_name = 'جزئیات دارو'
        verbose_name_plural = 'جزئیات داروها'

    def __str__(self):
        return f"{self.product.name} - {self.dosage_form} {self.strength}"


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Product')
    )
    image = models.ImageField(_('Image'), upload_to='products/%Y/%m/')
    alt_text = models.CharField(_('Alternative Text'), max_length=255, blank=True)
    is_primary = models.BooleanField(_('Primary Image'), default=False)
    order = models.PositiveIntegerField(_('Display Order'), default=0)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = 'تصویر محصول'
        verbose_name_plural = 'تصاویر محصول'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['product', 'is_primary']),
        ]

    def __str__(self):
        return f"Image for {self.product.name}"
    
    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, 
                is_primary=True
            ).update(is_primary=False)
        if not ProductImage.objects.filter(product=self.product).exists():
            self.is_primary = True
        super().save(*args, **kwargs)


class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name=_('Product')
    )
    name = models.CharField(_('Name'), max_length=100)
    sku = models.CharField(_('SKU'), max_length=50, unique=True)
    price_adjustment = models.DecimalField(
        _('Price Adjustment'),
        max_digits=12,
        decimal_places=2,
        default=0
    )
    stock_quantity = models.IntegerField(
        _('Stock Quantity'),
        default=0,
        validators=[MinValueValidator(0)]
    )
    weight_adjustment = models.DecimalField(
        _('Weight Adjustment (g)'),
        max_digits=10,
        decimal_places=2,
        default=0
    )
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = 'تنوع محصول'
        verbose_name_plural = 'تنوع‌های محصول'
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}"
    
    @property
    def calculated_price(self):
        return self.product.price + self.price_adjustment


class Batch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='batches',
        verbose_name=_('Product')
    )
    batch_number = models.CharField(_('Batch Number'), max_length=50)
    manufacturing_date = models.DateField(_('Manufacturing Date'))
    expiry_date = models.DateField(_('Expiry Date'))
    quantity = models.PositiveIntegerField(_('Quantity'))
    remaining_quantity = models.PositiveIntegerField(_('Remaining Quantity'))
    unit_cost = models.DecimalField(
        _('Unit Cost'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    notes = models.TextField(_('Notes'), blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = 'دسته (بچ)'
        verbose_name_plural = 'دسته‌ها (بچ‌ها)'
        ordering = ['expiry_date']
        indexes = [
            models.Index(fields=['batch_number']),
            models.Index(fields=['expiry_date']),
        ]
        unique_together = ['product', 'batch_number']

    def __str__(self):
        return f"{self.product.name} - {self.batch_number}"
    
    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()
    
    @property
    def expires_soon(self):
        if self.is_expired:
            return False
        expiry_threshold = timezone.now().date() + timezone.timedelta(days=90)
        return self.expiry_date <= expiry_threshold


class ProductTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Name'), max_length=100)
    slug = models.SlugField(_('Slug'), max_length=120, unique=True)
    products = models.ManyToManyField(
        Product,
        related_name='tags',
        verbose_name=_('Products')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = 'برچسب محصول'
        verbose_name_plural = 'برچسب‌های محصول'
        ordering = ['name']

    def __str__(self):
        return self.name