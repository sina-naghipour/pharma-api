# products/tests/test_models.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from products.models import (
    Category, Product, ProductImage, ProductVariant, 
    Attribute, AttributeValue, Manufacturer, ProductStock
)

class CategoryModelTest(TestCase):
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

    def test_category_creation(self):
        """Test creating a category"""
        self.assertEqual(self.parent_category.name, 'Parent Category')
        self.assertEqual(self.parent_category.slug, 'parent-category')
        self.assertIsNone(self.parent_category.parent)
        
        self.assertEqual(self.child_category.name, 'Child Category')
        self.assertEqual(self.child_category.parent, self.parent_category)

    def test_category_str(self):
        """Test the string representation of a category"""
        self.assertEqual(str(self.parent_category), 'Parent Category')
        self.assertEqual(str(self.child_category), 'Child Category')

    def test_category_hierarchy(self):
        """Test category hierarchy relationships"""
        self.assertEqual(list(self.parent_category.children.all()), [self.child_category])
        self.assertEqual(self.child_category.parent, self.parent_category)

    def test_category_slug_unique(self):
        """Test that category slug must be unique"""
        with self.assertRaises(ValidationError):
            duplicate_category = Category(
                name='Duplicate Category',
                slug='parent-category',  # Same as parent_category
                description='Duplicate category description'
            )
            duplicate_category.full_clean()


class ManufacturerModelTest(TestCase):
    def setUp(self):
        self.manufacturer = Manufacturer.objects.create(
            name='Test Manufacturer',
            slug='test-manufacturer',
            description='Test manufacturer description',
            website='https://example.com',
            email='contact@example.com'
        )

    def test_manufacturer_creation(self):
        """Test creating a manufacturer"""
        self.assertEqual(self.manufacturer.name, 'Test Manufacturer')
        self.assertEqual(self.manufacturer.slug, 'test-manufacturer')
        self.assertEqual(self.manufacturer.website, 'https://example.com')
        self.assertEqual(self.manufacturer.email, 'contact@example.com')

    def test_manufacturer_str(self):
        """Test the string representation of a manufacturer"""
        self.assertEqual(str(self.manufacturer), 'Test Manufacturer')


class AttributeModelTest(TestCase):
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

    def test_attribute_creation(self):
        """Test creating an attribute"""
        self.assertEqual(self.attribute.name, 'Color')
        self.assertEqual(self.attribute.slug, 'color')

    def test_attribute_str(self):
        """Test the string representation of an attribute"""
        self.assertEqual(str(self.attribute), 'Color')

    def test_attribute_value_creation(self):
        """Test creating attribute values"""
        self.assertEqual(self.value1.value, 'Red')
        self.assertEqual(self.value1.attribute, self.attribute)
        self.assertEqual(self.value2.value, 'Blue')
        self.assertEqual(self.value2.attribute, self.attribute)

    def test_attribute_value_str(self):
        """Test the string representation of attribute values"""
        self.assertEqual(str(self.value1), 'Color: Red')
        self.assertEqual(str(self.value2), 'Color: Blue')


class ProductModelTest(TestCase):
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
        
        # Create stock entry
        self.stock = ProductStock.objects.create(
            product=self.product,
            quantity=100,
            location='Warehouse A'
        )

    def test_product_creation(self):
        """Test creating a product"""
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.slug, 'test-product')
        self.assertEqual(self.product.price, 99.99)
        self.assertEqual(self.product.category, self.category)
        self.assertEqual(self.product.manufacturer, self.manufacturer)
        self.assertEqual(self.product.sku, 'TEST-SKU-123')
        self.assertTrue(self.product.is_active)
        self.assertFalse(self.product.is_featured)

    def test_product_str(self):
        """Test the string representation of a product"""
        self.assertEqual(str(self.product), 'Test Product')

    def test_product_image(self):
        """Test product image relationship"""
        self.assertEqual(self.product.images.count(), 1)
        self.assertEqual(self.product.images.first(), self.image)
        self.assertEqual(self.image.alt_text, 'Test image')
        self.assertEqual(str(self.image), 'Image for Test Product')

    def test_product_variant(self):
        """Test product variant relationship"""
        self.assertEqual(self.product.variants.count(), 1)
        self.assertEqual(self.product.variants.first(), self.variant)
        self.assertEqual(self.variant.name, 'Large')
        self.assertEqual(self.variant.price_adjustment, 10.00)
        self.assertEqual(str(self.variant), 'Test Product - Large')
        
        # Test variant attribute values
        self.assertEqual(self.variant.attribute_values.count(), 1)
        self.assertEqual(self.variant.attribute_values.first(), self.attr_value)

    def test_product_stock(self):
        """Test product stock relationship"""
        self.assertEqual(self.product.stock_records.count(), 1)
        self.assertEqual(self.product.stock_records.first(), self.stock)
        self.assertEqual(self.stock.quantity, 100)
        self.assertEqual(self.stock.location, 'Warehouse A')
        self.assertEqual(str(self.stock), 'Stock for Test Product (100 units)')