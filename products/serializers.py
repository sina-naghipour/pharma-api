# products/serializers.py
from rest_framework import serializers
from django.utils.text import slugify
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from .models import (
    Category,
    Manufacturer,
    Product,
    Medication,
    ProductImage,
    ProductVariant,
    Batch,
    ProductTag
)
from reviews.serializers import ReviewSerializer
from reviews.models import Review


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'parent',
            'image', 'is_active', 'order', 'children',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_children(self, obj):
        """Get child categories"""
        children = Category.objects.filter(parent=obj)
        serializer = CategoryListSerializer(children, many=True)
        return serializer.data
    
    def create(self, validated_data):
        """Create category with auto-generated slug if not provided"""
        if 'slug' not in validated_data:
            validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)
    
    def validate(self, data):
        """Validate parent-child relationship"""
        # Prevent category from being its own parent
        if 'parent' in data and data['parent'] == self.instance:
            raise serializers.ValidationError({
                'parent': _("A category cannot be its own parent.")
            })
            
        return data


class CategoryListSerializer(serializers.ModelSerializer):
    """Simplified Category serializer for list views"""
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'image', 'product_count']
    
    def get_product_count(self, obj):
        """Get count of active products in this category"""
        return obj.products.filter(is_active=True).count()


class ManufacturerSerializer(serializers.ModelSerializer):
    """Serializer for Manufacturer model"""
    
    class Meta:
        model = Manufacturer
        fields = [
            'id', 'name', 'slug', 'description', 'logo',
            'country', 'website', 'founded_year', 'is_approved',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_approved']
    
    def create(self, validated_data):
        """Create manufacturer with auto-generated slug if not provided"""
        if 'slug' not in validated_data:
            validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    
    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'order']

class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer for ProductVariant model"""
    calculated_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'name', 'sku', 'price_adjustment',
            'stock_quantity', 'weight_adjustment', 'is_active',
            'calculated_price'
        ]
        read_only_fields = ['id']


class MedicationSerializer(serializers.ModelSerializer):
    """Serializer for Medication model"""
    
    class Meta:
        model = Medication
        fields = [
            'generic_name', 'dosage_form', 'strength', 'route_of_administration',
            'therapeutic_class', 'atc_code', 'registration_number',
            'indications', 'contraindications', 'side_effects',
            'warnings', 'storage_conditions', 'pregnancy_category',
            'active_ingredients', 'inactive_ingredients'
        ]


class BatchSerializer(serializers.ModelSerializer):
    """Serializer for Batch model"""
    expires_soon = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Batch
        fields = [
            'id', 'batch_number', 'manufacturing_date', 'expiry_date',
            'quantity', 'remaining_quantity', 'unit_cost', 'notes',
            'expires_soon', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate batch data"""
        # Ensure manufacturing date is before expiry date
        if (data.get('manufacturing_date') and data.get('expiry_date') and
                data['manufacturing_date'] >= data['expiry_date']):
            raise serializers.ValidationError({
                'expiry_date': _("Expiry date must be after manufacturing date.")
            })
        
        # Ensure remaining quantity is not greater than total quantity
        if (data.get('quantity') is not None and data.get('remaining_quantity') is not None and
                data['remaining_quantity'] > data['quantity']):
            raise serializers.ValidationError({
                'remaining_quantity': _("Remaining quantity cannot exceed total quantity.")
            })
        
        return data


class ProductListSerializer(serializers.ModelSerializer):
    """Simplified Product serializer for list views"""
    primary_image = serializers.SerializerMethodField()
    category_names = serializers.SerializerMethodField()
    manufacturer_name = serializers.SerializerMethodField()
    discount_percentage = serializers.IntegerField(read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'product_type',
            'price', 'compare_price', 'discount_percentage',
            'is_on_sale', 'in_stock', 'is_featured',
            'primary_image', 'category_names',
            'manufacturer_name', 'average_rating',
            'prescription_required'
        ]
    
    def get_primary_image(self, obj):
        """Get primary product image URL"""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return self.context['request'].build_absolute_uri(primary_image.image.url)
        return None
    
    def get_category_names(self, obj):
        """Get list of category names"""
        return [category.name for category in obj.categories.all()]
    
    def get_manufacturer_name(self, obj):
        """Get manufacturer name"""
        return obj.manufacturer.name
    
    def get_average_rating(self, obj):
        """Calculate average product rating"""
        reviews = obj.reviews.filter()
        if not reviews:
            return None
        return round(sum(review.rating for review in reviews) / reviews.count(), 1)


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed Product serializer"""
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    medication_details = MedicationSerializer(read_only=True)
    categories = CategoryListSerializer(many=True, read_only=True)
    manufacturer = ManufacturerSerializer(read_only=True)
    reviews = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    discount_percentage = serializers.IntegerField(read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'product_type', 'sku', 'barcode',
            'description', 'short_description', 'categories',
            'manufacturer', 'price', 'compare_price', 'discount_percentage',
            'is_on_sale', 'tax_class', 'is_taxable', 'prescription_required',
            'track_inventory', 'in_stock', 'stock_quantity', 'is_low_stock',
            'backorder_allowed', 'weight', 'length', 'max_order_quantity', 'width', 'height',
            'is_active', 'is_featured', 'published_at',
            'meta_title', 'meta_description', 'images', 'variants',
            'medication_details', 'reviews', 'tags', 'average_rating'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'published_at']
    
    def get_reviews(self, obj):
        """Get approved reviews"""
        reviews = obj.reviews.filter()
        return ReviewSerializer(reviews, many=True).data
    
    def get_tags(self, obj):
        """Get product tags"""
        return [{'id': tag.id, 'name': tag.name} for tag in obj.tags.all()]
    
    def get_average_rating(self, obj):
        """Calculate average product rating"""
        reviews = obj.reviews.filter()
        if not reviews:
            return None
        return round(sum(review.rating for review in reviews) / reviews.count(), 1)


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating products"""
    medication_details = MedicationSerializer(required=False)
    images = ProductImageSerializer(many=True, required=False)
    variants = ProductVariantSerializer(many=True, required=False)
    category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = Product
        fields = [
            'name', 'product_type', 'sku', 'barcode',
            'description', 'short_description', 'manufacturer',
            'price', 'compare_price', 'cost_price', 'tax_class',
            'is_taxable', 'prescription_required', 'track_inventory',
            'stock_quantity', 'low_stock_threshold', 'backorder_allowed',
            'weight', 'length', 'width', 'height', 'is_active',
            'is_featured', 'meta_title', 'meta_description',
            'medication_details', 'images', 'variants',
            'category_ids', 'tag_ids'
        ]
    
    def create(self, validated_data):
        """Create product with related models"""
        # Extract nested data
        medication_data = validated_data.pop('medication_details', None)
        images_data = validated_data.pop('images', [])
        variants_data = validated_data.pop('variants', [])
        category_ids = validated_data.pop('category_ids', [])
        tag_ids = validated_data.pop('tag_ids', [])
        
        # Generate slug if not provided
        if 'slug' not in validated_data:
            validated_data['slug'] = slugify(validated_data['name'])
            
            # Ensure slug is unique
            base_slug = validated_data['slug']
            counter = 1
            while Product.objects.filter(slug=validated_data['slug']).exists():
                validated_data['slug'] = f"{base_slug}-{counter}"
                counter += 1
        
        with transaction.atomic():
            # Create product
            product = Product.objects.create(**validated_data)
            
            # Add categories
            if category_ids:
                product.categories.set(category_ids)
            
            # Add tags
            if tag_ids:
                product.tags.set(tag_ids)
            
            # Create medication details if product is medication
            if medication_data and product.product_type == Product.MEDICATION:
                Medication.objects.create(product=product, **medication_data)
            
            # Create product images
            for image_data in images_data:
                ProductImage.objects.create(product=product, **image_data)
            
            # Create product variants
            for variant_data in variants_data:
                ProductVariant.objects.create(product=product, **variant_data)
            
            return product
    
    def update(self, instance, validated_data):
        """Update product with related models"""
        # Extract nested data
        medication_data = validated_data.pop('medication_details', None)
        images_data = validated_data.pop('images', None)
        variants_data = validated_data.pop('variants', None)
        category_ids = validated_data.pop('category_ids', None)
        tag_ids = validated_data.pop('tag_ids', None)
        
        with transaction.atomic():
            # Update product fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            
            # Update categories if provided
            if category_ids is not None:
                instance.categories.set(category_ids)
            
            # Update tags if provided
            if tag_ids is not None:
                instance.tags.set(tag_ids)
            
            # Update medication details
            if medication_data and instance.product_type == Product.MEDICATION:
                medication, created = Medication.objects.get_or_create(product=instance)
                for attr, value in medication_data.items():
                    setattr(medication, attr, value)
                medication.save()
            
            # Update images if provided
            if images_data is not None:
                # First, delete existing images
                instance.images.all().delete()
                
                # Then create new images
                for image_data in images_data:
                    ProductImage.objects.create(product=instance, **image_data)
            
            # Update variants if provided
            if variants_data is not None:
                # First, delete existing variants
                instance.variants.all().delete()
                
                # Then create new variants
                for variant_data in variants_data:
                    ProductVariant.objects.create(product=instance, **variant_data)
            
            return instance