from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from .models import (
    Category, Manufacturer, Product, Medication, ProductImage,
    ProductVariant, Batch, ProductTag
)


class ProductImageInline(TabularInline):
    """Inline for product images"""
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary', 'order']
    readonly_fields = ['created_at']
    show_change_link = True


class ProductVariantInline(TabularInline):
    """Inline for product variants"""
    model = ProductVariant
    extra = 1
    fields = ['name', 'sku', 'price_adjustment', 'stock_quantity', 'is_active']
    readonly_fields = ['created_at']


class BatchInline(TabularInline):
    """Inline for product batches"""
    model = Batch
    extra = 0
    fields = ['batch_number', 'manufacturing_date', 'expiry_date', 
              'quantity', 'remaining_quantity', 'unit_cost']
    readonly_fields = ['created_at', 'updated_at']


class MedicationInline(StackedInline):
    """Inline for medication details (only for medication products)"""
    model = Medication
    can_delete = False
    verbose_name = _('Medication Details')
    verbose_name_plural = _('Medication Details')
    fieldsets = (
        (None, {
            'fields': ('generic_name', 'dosage_form', 'strength', 'route_of_administration')
        }),
        (_('Classification'), {
            'fields': ('therapeutic_class', 'atc_code')
        }),
        (_('Regulatory'), {
            'fields': ('registration_number',)
        }),
        (_('Safety & Usage'), {
            'fields': ('indications', 'contraindications', 'side_effects', 
                      'warnings', 'storage_conditions', 'pregnancy_category')
        }),
        (_('Composition'), {
            'fields': ('active_ingredients', 'inactive_ingredients')
        }),
    )


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'is_active', 'order', 'created_at']
    list_filter = ['is_active', 'parent', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']
    ordering = ['order', 'name']
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
        (_('Hierarchy'), {
            'fields': ('parent',)
        }),
        (_('Display'), {
            'fields': ('image', 'is_active', 'order')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Manufacturer)
class ManufacturerAdmin(ModelAdmin):
    list_display = ['name', 'slug', 'country', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'country', 'created_at']
    search_fields = ['name', 'slug', 'description', 'country']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_approved']
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
        (_('Contact & Info'), {
            'fields': ('logo', 'country', 'website', 'founded_year')
        }),
        (_('Status'), {
            'fields': ('is_approved',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ['name', 'sku', 'product_type', 'price', 'in_stock', 
                    'is_active', 'is_featured', 'created_at']
    list_filter = ['product_type', 'is_active', 'is_featured', 'in_stock', 
                   'prescription_required', 'track_inventory', 'created_at']
    search_fields = ['name', 'slug', 'sku', 'barcode', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'in_stock', 'is_active', 'is_featured']
    readonly_fields = ['created_at', 'updated_at', 'published_at', 
                       'discount_percentage', 'is_on_sale', 'is_low_stock']
    inlines = [ProductImageInline, ProductVariantInline, BatchInline, MedicationInline]
    filter_horizontal = ['categories']
    raw_id_fields = ['manufacturer']
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'product_type', 'sku', 'barcode', 
                      'description', 'short_description')
        }),
        (_('Categories & Manufacturer'), {
            'fields': ('categories', 'manufacturer')
        }),
        (_('Pricing'), {
            'fields': ('price', 'compare_price', 'cost_price', 
                      'discount_percentage', 'is_on_sale')
        }),
        (_('Inventory'), {
            'fields': ('track_inventory', 'in_stock', 'stock_quantity', 
                      'low_stock_threshold', 'backorder_allowed', 'is_low_stock')
        }),
        (_('Shipping'), {
            'fields': ('weight', 'length', 'width', 'height')
        }),
        (_('Tax & Prescription'), {
            'fields': ('tax_class', 'is_taxable', 'prescription_required')
        }),
        (_('Visibility & SEO'), {
            'fields': ('is_active', 'is_featured', 'is_approved', 'published_at',
                      'meta_title', 'meta_description')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['make_active', 'make_inactive', 'make_featured', 'make_unfeatured']

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    make_active.short_description = _("Activate selected products")

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    make_inactive.short_description = _("Deactivate selected products")

    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
    make_featured.short_description = _("Mark selected as featured")

    def make_unfeatured(self, request, queryset):
        queryset.update(is_featured=False)
    make_unfeatured.short_description = _("Unmark featured from selected")


@admin.register(ProductImage)
class ProductImageAdmin(ModelAdmin):
    list_display = ['product', 'image_preview', 'is_primary', 'order', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['product__name', 'alt_text']
    list_editable = ['is_primary', 'order']
    readonly_fields = ['created_at']
    raw_id_fields = ['product']
    fieldsets = (
        (None, {
            'fields': ('product', 'image', 'alt_text', 'is_primary', 'order')
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;" />', obj.image.url)
        return "-"
    image_preview.short_description = _('Preview')


@admin.register(ProductVariant)
class ProductVariantAdmin(ModelAdmin):
    list_display = ['product', 'name', 'sku', 'price_adjustment', 
                    'stock_quantity', 'is_active', 'calculated_price']
    list_filter = ['is_active', 'created_at']
    search_fields = ['product__name', 'name', 'sku']
    list_editable = ['price_adjustment', 'stock_quantity', 'is_active']
    readonly_fields = ['calculated_price', 'created_at', 'updated_at']
    raw_id_fields = ['product']
    fieldsets = (
        (None, {
            'fields': ('product', 'name', 'sku')
        }),
        (_('Pricing & Stock'), {
            'fields': ('price_adjustment', 'calculated_price', 'stock_quantity')
        }),
        (_('Shipping'), {
            'fields': ('weight_adjustment',)
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Batch)
class BatchAdmin(ModelAdmin):
    list_display = ['product', 'batch_number', 'manufacturing_date', 'expiry_date',
                    'quantity', 'remaining_quantity', 'is_expired']
    list_filter = ['expiry_date', 'manufacturing_date', 'created_at']
    search_fields = ['batch_number', 'product__name']
    readonly_fields = ['is_expired', 'expires_soon', 'created_at', 'updated_at']
    raw_id_fields = ['product']
    fieldsets = (
        (None, {
            'fields': ('product', 'batch_number')
        }),
        (_('Dates'), {
            'fields': ('manufacturing_date', 'expiry_date', 'is_expired', 'expires_soon')
        }),
        (_('Quantities'), {
            'fields': ('quantity', 'remaining_quantity', 'unit_cost')
        }),
        (_('Notes'), {
            'fields': ('notes',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = _('Expired')


@admin.register(ProductTag)
class ProductTagAdmin(ModelAdmin):
    list_display = ['name', 'slug', 'product_count', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']
    filter_horizontal = ['products']
    fieldsets = (
        (None, {
            'fields': ('name', 'slug')
        }),
        (_('Products'), {
            'fields': ('products',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = _('Number of products')