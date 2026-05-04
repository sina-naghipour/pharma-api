# orders/tests/test_serializers.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from orders.models import Order, OrderItem, ShippingMethod
from orders.serializers import (
    OrderSerializer, OrderItemSerializer, 
    OrderCreateSerializer, ShippingMethodSerializer
)
from products.models import Product, Category
from decimal import Decimal

User = get_user_model()

class OrderSerializerTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123',
            first_name='Test',
            last_name='Customer'
        )
        
        # Create category and products
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product1 = Product.objects.create(
            name='Product 1',
            slug='product-1',
            price=Decimal('10.00'),
            category=self.category
        )
        
        self.product2 = Product.objects.create(
            name='Product 2',
            slug='product-2',
            price=Decimal('15.00'),
            category=self.category
        )
        
        # Create shipping method
        self.shipping_method = ShippingMethod.objects.create(
            name='Standard Shipping',
            price=Decimal('5.00'),
            description='3-5 business days'
        )
        
        # Create order
        self.order = Order.objects.create(
            user=self.user,
            status='pending',
            shipping_address='123 Test St, Test City, 12345',
            billing_address='123 Test St, Test City, 12345',
            shipping_method=self.shipping_method,
            payment_method='credit_card',
            subtotal=Decimal('25.00'),
            shipping_cost=Decimal('5.00'),
            tax=Decimal('2.50'),
            total_amount=Decimal('32.50')
        )
        
        # Create order items
        self.order_item1 = OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=1,
            price=Decimal('10.00')
        )
        
        self.order_item2 = OrderItem.objects.create(
            order=self.order,
            product=self.product2,
            quantity=1,
            price=Decimal('15.00')
        )
        
        self.serializer = OrderSerializer(instance=self.order)
    
    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields"""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'user', 'status', 'shipping_address', 'billing_address',
             'shipping_method', 'payment_method', 'subtotal', 'shipping_cost',
             'tax', 'total_amount', 'items', 'created_at', 'updated_at',
             'tracking_number', 'notes']
        )
    
    def test_items_included(self):
        """Test that order items are included in serializer"""
        data = self.serializer.data
        self.assertEqual(len(data['items']), 2)
        item_products = [item['product'] for item in data['items']]
        self.assertIn(self.product1.id, item_products)
        self.assertIn(self.product2.id, item_products)


class OrderCreateSerializerTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
        # Create category and products
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product1 = Product.objects.create(
            name='Product 1',
            slug='product-1',
            price=Decimal('10.00'),
            category=self.category,
            stock_quantity=10
        )
        
        self.product2 = Product.objects.create(
            name='Product 2',
            slug='product-2',
            price=Decimal('15.00'),
            category=self.category,
            stock_quantity=5
        )
        
        # Create shipping method
        self.shipping_method = ShippingMethod.objects.create(
            name='Standard Shipping',
            price=Decimal('5.00'),
            description='3-5 business days'
        )
        
        # Order data for serializer
        self.order_data = {
            'shipping_address': '123 Test St, Test City, 12345',
            'billing_address': '123 Test St, Test City, 12345',
            'shipping_method': self.shipping_method.id,
            'payment_method': 'credit_card',
            'items': [
                {'product': self.product1.id, 'quantity': 2},
                {'product': self.product2.id, 'quantity': 1}
            ]
        }
        
        self.serializer = OrderCreateSerializer(
            data=self.order_data,
            context={'request': type('obj', (object,), {'user': self.user})}
        )
    
    def test_validate_success(self):
        """Test successful validation"""
        self.assertTrue(self.serializer.is_valid())
    
    def test_create_order(self):
        """Test creating an order with the serializer"""
        self.assertTrue(self.serializer.is_valid())
        order = self.serializer.save()
        
        # Check order details
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.shipping_address, self.order_data['shipping_address'])
        self.assertEqual(order.shipping_method, self.shipping_method)
        self.assertEqual(order.payment_method, self.order_data['payment_method'])
        
        # Check order items
        self.assertEqual(order.items.count(), 2)
        
        # Check calculated totals
        self.assertEqual(order.subtotal, Decimal('35.00'))  # 2*10 + 1*15
        self.assertEqual(order.shipping_cost, Decimal('5.00'))
        
        # Check stock reduction
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.stock_quantity, 8)  # 10 - 2
        self.assertEqual(self.product2.stock_quantity, 4)  # 5 - 1
    
    def test_validate_insufficient_stock(self):
        """Test validation fails when product has insufficient stock"""
        # Update order data with quantity exceeding stock
        self.order_data['items'][1]['quantity'] = 10  # Product2 only has 5 in stock
        
        serializer = OrderCreateSerializer(
            data=self.order_data,
            context={'request': type('obj', (object,), {'user': self.user})}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('items', serializer.errors)


class ShippingMethodSerializerTest(TestCase):
    def setUp(self):
        self.shipping_method = ShippingMethod.objects.create(
            name='Express Shipping',
            price=Decimal('15.00'),
            description='1-2 business days',
            is_active=True
        )
        self.serializer = ShippingMethodSerializer(instance=self.shipping_method)
    
    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields"""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'name', 'price', 'description', 'estimated_days', 'is_active']
        )
    
    def test_field_content(self):
        """Test field content"""
        data = self.serializer.data
        self.assertEqual(data['name'], self.shipping_method.name)
        self.assertEqual(data['price'], '15.00')
        self.assertEqual(data['description'], self.shipping_method.description)