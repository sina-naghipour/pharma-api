# products/tests/test_filters.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from products.models import (
    Category, Product, Manufacturer
)
from decimal import Decimal

class ProductFilterTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create categories
        self.category1 = Category.objects.create(
            name='Category 1',
            slug='category-1'
        )
        self.category2 = Category.objects.create(
            name='Category 2',
            slug='category-2'
        )
        
        # Create manufacturers
        self.manufacturer1 = Manufacturer.objects.create(
            name='Manufacturer 1',
            slug='manufacturer-1'
        )
        self.manufacturer2 = Manufacturer.objects.create(
            name='Manufacturer 2',
            slug='manufacturer-2'
        )
        
        # Create products
        self.product1 = Product.objects.create(
            name='Product 1',
            slug='product-1',
            price=Decimal('10.00'),
            category=self.category1,
            manufacturer=self.manufacturer1,
            is_active=True
        )
        
        self.product2 = Product.objects.create(
            name='Product 2',
            slug='product-2',
            price=Decimal('20.00'),
            category=self.category1,
            manufacturer=self.manufacturer2,
            is_active=True
        )
        
        self.product3 = Product.objects.create(
            name='Product 3',
            slug='product-3',
            price=Decimal('30.00'),
            category=self.category2,
            manufacturer=self.manufacturer1,
            is_active=True
        )
        
        self.product4 = Product.objects.create(
            name='Inactive Product',
            slug='inactive-product',
            price=Decimal('15.00'),
            category=self.category2,
            manufacturer=self.manufacturer2,
            is_active=False
        )
        
        self.list_url = reverse('products:product-list')
    
    def test_filter_by_category(self):
        """Test filtering products by category"""
        url = f"{self.list_url}?category={self.category1.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        product_slugs = [p['slug'] for p in response.data['results']]
        self.assertIn(self.product1.slug, product_slugs)
        self.assertIn(self.product2.slug, product_slugs)
        self.assertNotIn(self.product3.slug, product_slugs)
    
    def test_filter_by_manufacturer(self):
        """Test filtering products by manufacturer"""
        url = f"{self.list_url}?manufacturer={self.manufacturer1.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        product_slugs = [p['slug'] for p in response.data['results']]
        self.assertIn(self.product1.slug, product_slugs)
        self.assertIn(self.product3.slug, product_slugs)
        self.assertNotIn(self.product2.slug, product_slugs)
    
    def test_filter_by_price_range(self):
        """Test filtering products by price range"""
        url = f"{self.list_url}?min_price=15&max_price=25"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['slug'], self.product2.slug)
    
    def test_filter_by_active_status(self):
        """Test filtering products by active status"""
        # Default should only show active products
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)
        
        # Explicitly filter for inactive
        url = f"{self.list_url}?is_active=false"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['slug'], self.product4.slug)
    
    def test_multiple_filters(self):
        """Test using multiple filters together"""
        url = f"{self.list_url}?category={self.category1.id}&manufacturer={self.manufacturer1.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['slug'], self.product1.slug)