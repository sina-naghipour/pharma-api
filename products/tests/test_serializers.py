# products/tests/test_serializers.py
from django.test import TestCase
from products.models import (
    Category, Product, ProductImage, ProductVariant, 
    Attribute, AttributeValue, Manufacturer
)
from products.serializers import (
    CategorySerializer, ProductSerializer, ProductDetailSerializer,
    AttributeSerializer, AttributeValueSerializer, ManufacturerSerializer
)

class CategorySerializerTest(TestCase):
    def setUp(self):
        self.parent_category = Category.objects.create(
            name='Parent Category',
            slug='parent-category',
            description='Parent category description'
        )
        self.child_category = Category.objects.create(
            name='Child Category',
            slug='child-category',
            description='Child category description',
            parent=self.parent_category
        )
        self.parent_serializer = CategorySerializer(instance=self.parent_category)
        self.child_serializer = CategorySerializer(instance=self.child_category)

    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields"""
        parent_data = self.parent_serializer.data
        self.assertCountEqual(
            parent_data.keys(),
            ['id', 'name', 'slug', 'description', 'parent', 'image', 'is_active', 'meta_title', 
             'meta_description', 'created_at', 'updated_at']
        )

    def test_parent_field_content(self):
        """Test parent field content"""
        child_data = self.child_serializer.data
        self.assertEqual(child_data['parent'], self.parent_category.id)
        self.assertEqual(child_data['name'], self.child_category.name)


class ManufacturerSerializerTest(TestCase):
    def setUp(self):
        self.manufacturer = Manufacturer.objects.create(
            name='Test Manufacturer',
            slug='test-manufacturer',
            description='Test manufacturer description',
            website='https://example.com',
            email='contact@example.com'
        )
        self.serializer = ManufacturerSerializer(instance=self.manufacturer)

    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields"""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'name', 'slug', 'description', 'website', 'email', 'logo', 
             'is_active', 'created_at', 'updated_at']
        )

    def test_field_content(self):
        """Test field content"""
        data = self.serializer.data
        self.assertEqual(data['name'], self.manufacturer.name)
        self.assertEqual(data['slug'], self.manufacturer.slug)
        self.assertEqual(data['website'], self.manufacturer.website)
        self.assertEqual(data['email'], self.manufacturer.email)


class AttributeSerializerTest(TestCase):
    def setUp(self):
        self.attribute = Attribute.objects.create(
            name='Color',
            slug='color',
            description='Product color'
        )
        self.value1 = AttributeValue.objects.create(
            attribute=self.attribute,
            value='Red',
            slug='red'
        )
        self.value2 = AttributeValue.objects.create(
            attribute=self.attribute,
            value='Blue',
            slug='blue'
        )
        self.attribute_serializer = AttributeSerializer(instance=self.attribute)
        self.value_serializer = AttributeValueSerializer(instance=self.value1)

    def test_attribute_contains_expected_fields(self):
        """Test that attribute serializer contains expected fields"""
        data = self.attribute_serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'name', 'slug', 'description', 'values', 'created_at', 'updated_at']
        )

    def test_attribute_values_included(self):
        """Test that attribute values are included in attribute serializer"""
        data = self.attribute_serializer.data
        self.assertEqual(len(data['values']), 2)
        value_slugs = [value['slug'] for value in data['values']]
        self.assertIn('red', value_slugs)
        self.assertIn('blue', value_slugs)

    def test_attribute_value_contains_expected_fields(self):
        """Test that attribute value serializer contains expected fields"""
        data = self.value_serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'attribute', 'value', 'slug', 'created_at', 'updated_at']
        )

    def test_attribute_value_field_content(self):
        """Test attribute value field content"""
        data = self.value_serializer.data
        self.assertEqual(data['value'], self.value1.value)
        self.assertEqual(data['slug'], self.value1.slug)
        self.assertEqual(data['attribute'], self.attribute.id)


class ProductSerializerTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.manufacturer = Manufacturer.objects.create(
            name='Test Manufacturer',
            slug='test-manufacturer'
        )
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            description='Test product description',
            price=99.99,
            category=self.category,
            manufacturer=self.manufacturer,
            sku='TEST-SKU-123',
            is_active=True,
            is_featured=False
        )
        self.image = ProductImage.objects.create(
            product=self.product,
            image='test-image.jpg',
            alt_text='Test image'
        )
        
        # Create attribute and variant
        self.attribute = Attribute.objects.create(
            name='Size',
            slug='size'
        )
        self.attr_value = AttributeValue.objects.create(
            attribute=self.attribute,
            value='Large',
            slug='large'
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name='Large',
            sku='TEST-SKU-123-L',
            price_adjustment=10.00,
            is_active=True
        )
        self.variant.attribute_values.add(self.attr_value)
        
        self.list_serializer = ProductSerializer(instance=self.product)
        self.detail_serializer = ProductDetailSerializer(instance=self.product)

    def test_list_serializer_contains_expected_fields(self):
        """Test that list serializer contains expected fields"""
        data = self.list_serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'name', 'slug', 'price', 'sale_price', 'category', 'thumbnail',
             'is_active', 'is_featured', 'average_rating', 'created_at']
        )

    def test_detail_serializer_contains_expected_fields(self):
        """Test that detail serializer contains expected fields"""
        data = self.detail_serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'name', 'slug', 'description', 'price', 'sale_price', 'category', 
             'manufacturer', 'sku', 'is_active', 'is_featured', 'stock_quantity', 
             'low_stock_threshold', 'weight', 'dimensions', 'meta_title', 
             'meta_description', 'images', 'variants', 'attributes', 'average_rating', 
             'created_at', 'updated_at']
        )

    def test_images_included_in_detail(self):
        """Test that images are included in detail serializer"""
        data = self.detail_serializer.data
        self.assertEqual(len(data['images']), 1)
        self.assertEqual(data['images'][0]['alt_text'], 'Test image')

    def test_variants_included_in_detail(self):
        """Test that variants are included in detail serializer"""
        data = self.detail_serializer.data
        self.assertEqual(len(data['variants']), 1)
        self.assertEqual(data['variants'][0]['name'], 'Large')
        self.assertEqual(data['variants'][0]['price_adjustment'], '10.00')