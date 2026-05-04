# products/tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from products.models import (
    Category, Product, ProductImage, ProductVariant, 
    Attribute, AttributeValue, Manufacturer
)
from django.contrib.auth import get_user_model

User = get_user_model()

class CategoryViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123'
        )
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpassword123'
        )
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            description='Test category description'
        )
        self.list_url = reverse('products:category-list')
        self.detail_url = reverse('products:category-detail', args=[self.category.id])

    def test_get_categories(self):
        """Test retrieving a list of categories"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.category.name)

    def test_get_category_detail(self):
        """Test retrieving a category detail"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.category.name)
        self.assertEqual(response.data['slug'], self.category.slug)

    def test_create_category_unauthorized(self):
        """Test that unauthorized users cannot create categories"""
        new_category = {
            'name': 'New Category',
            'slug': 'new-category',
            'description': 'New category description'
        }
        response = self.client.post(self.list_url, new_category)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Category.objects.count(), 1)

    def test_create_category_authorized(self):
        """Test that admin users can create categories"""
        self.client.force_authenticate(user=self.admin_user)
        new_category = {
            'name': 'New Category',
            'slug': 'new-category',
            'description': 'New category description'
        }
        response = self.client.post(self.list_url, new_category)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 2)
        self.assertTrue(Category.objects.filter(slug='new-category').exists())

    def test_update_category(self):
        """Test updating a category"""
        self.client.force_authenticate(user=self.admin_user)
        update_data = {'description': 'Updated description'}
        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category.refresh_from_db()
        self.assertEqual(self.category.description, update_data['description'])

    def test_delete_category(self):
        """Test deleting a category"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(id=self.category.id).exists())


class ProductViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123'
        )
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpassword123'
        )
        
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
        
        self.list_url = reverse('products:product-list')
        self.detail_url = reverse('products:product-detail', args=[self.product.id])

    def test_get_products(self):
        """Test retrieving a list of products"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Assuming pagination
        self.assertEqual(response.data['results'][0]['name'], self.product.name)

    def test_get_product_detail(self):
        """Test retrieving a product detail"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.product.name)
        self.assertEqual(response.data['slug'], self.product.slug)
        self.assertEqual(response.data['price'], '99.99')  # Decimal as string in JSON

    def test_create_product_unauthorized(self):
        """Test that unauthorized users cannot create products"""
        new_product = {
            'name': 'New Product',
            'slug': 'new-product',
            'description': 'New product description',
            'price': 149.99,
            'category': self.category.id,
            'manufacturer': self.manufacturer.id,
            'sku': 'NEW-SKU-456'
        }
        response = self.client.post(self.list_url, new_product)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Product.objects.count(), 1)

    def test_create_product_authorized(self):
        """Test that admin users can create products"""
        self.client.force_authenticate(user=self.admin_user)
        new_product = {
            'name': 'New Product',
            'slug': 'new-product',
            'description': 'New product description',
            'price': '149.99',
            'category': self.category.id,
            'manufacturer': self.manufacturer.id,
            'sku': 'NEW-SKU-456'
        }
        response = self.client.post(self.list_url, new_product)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)
        self.assertTrue(Product.objects.filter(slug='new-product').exists())

    def test_update_product(self):
        """Test updating a product"""
        self.client.force_authenticate(user=self.admin_user)
        update_data = {'price': '129.99'}
        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(str(self.product.price), update_data['price'])

    def test_delete_product(self):
        """Test deleting a product"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())

    def test_featured_products(self):
        """Test retrieving featured products"""
        # Create a featured product
        featured_product = Product.objects.create(
            name='Featured Product',
            slug='featured-product',
            price=199.99,
            category=self.category,
            is_featured=True
        )
        
        featured_url = reverse('products:product-featured')
        response = self.client.get(featured_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], featured_product.name)

    def test_product_search(self):
        """Test searching for products"""
        # Create another product for search test
        Product.objects.create(
            name='Searchable Product',
            slug='searchable-product',
            description='This is a searchable product',
            price=49.99,
            category=self.category
        )
        
        search_url = f"{self.list_url}?search=searchable"
        response = self.client.get(search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Searchable Product')