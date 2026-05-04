# orders/tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem, ShippingMethod
from products.models import Product, Category
from decimal import Decimal

User = get_user_model()

class OrderViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.customer = User.objects.create_user(
            email='customer@example.com',
            password='password123',
            first_name='Test',
            last_name='Customer'
        )
        
        self.other_customer = User.objects.create_user(
            email='other@example.com',
            password='password123'
        )
        
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpassword123'
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
        
        # Create order
        self.order = Order.objects.create(
            user=self.customer,
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
        
        # URLs
        self.list_url = reverse('orders:order-list')
        self.detail_url = reverse('orders:order-detail', args=[self.order.id])
    
    def test_get_orders_unauthenticated(self):
        """Test that unauthenticated users cannot access orders"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_customer_orders(self):
        """Test that customer can access their own orders"""
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.order.id)
    
    def test_customer_cannot_access_others_orders(self):
        """Test that customer cannot access another customer's order details"""
        self.client.force_authenticate(user=self.other_customer)
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_admin_can_access_all_orders(self):
        """Test that admin can access all orders"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_create_order(self):
        """Test creating a new order"""
        self.client.force_authenticate(user=self.customer)
        
        order_data = {
            'shipping_address': '456 New St, New City, 67890',
            'billing_address': '456 New St, New City, 67890',
            'shipping_method': self.shipping_method.id,
            'payment_method': 'credit_card',
            'items': [
                {'product': self.product1.id, 'quantity': 2},
                {'product': self.product2.id, 'quantity': 1}
            ]
        }
        
        response = self.client.post(self.list_url, order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check order was created
        self.assertEqual(Order.objects.count(), 2)
        
        # Check stock was reduced
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.stock_quantity, 8)  # 10 - 2
        self.assertEqual(self.product2.stock_quantity, 4)  # 5 - 1
    
    def test_update_order_status_by_admin(self):
        """Test that admin can update order status"""
        self.client.force_authenticate(user=self.admin_user)
        
        update_data = {'status': 'processing'}
        response = self.client.patch(self.detail_url, update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'processing')
    
    def test_customer_cannot_update_order_status(self):
        """Test that customer cannot update order status"""
        self.client.force_authenticate(user=self.customer)
        
        update_data = {'status': 'processing'}
        response = self.client.patch(self.detail_url, update_data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'pending')  # Status unchanged


class ShippingMethodViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpassword123'
        )
        
        self.shipping_method1 = ShippingMethod.objects.create(
            name='Standard Shipping',
            price=Decimal('5.00'),
            description='3-5 business days',
            is_active=True
        )
        
        self.shipping_method2 = ShippingMethod.objects.create(
            name='Express Shipping',
            price=Decimal('15.00'),
            description='1-2 business days',
            is_active=True
        )
        
        self.inactive_method = ShippingMethod.objects.create(
            name='Inactive Method',
            price=Decimal('10.00'),
            description='Not available',
            is_active=False
        )
        
        self.list_url = reverse('orders:shipping-method-list')
        self.detail_url = reverse('orders:shipping-method-detail', args=[self.shipping_method1.id])
    
    def test_get_shipping_methods(self):
        """Test retrieving a list of active shipping methods"""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Only active methods
        
        method_names = [method['name'] for method in response.data]
        self.assertIn(self.shipping_method1.name, method_names)
        self.assertIn(self.shipping_method2.name, method_names)
        self.assertNotIn(self.inactive_method.name, method_names)
    
    def test_create_shipping_method_unauthorized(self):
        """Test that unauthorized users cannot create shipping methods"""
        new_method = {
            'name': 'New Method',
            'price': '7.50',
            'description': 'New shipping method'
        }
        
        response = self.client.post(self.list_url, new_method)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(ShippingMethod.objects.count(), 3)  # Unchanged
    
    def test_create_shipping_method_authorized(self):
        """Test that admin users can create shipping methods"""
        self.client.force_authenticate(user=self.admin_user)
        
        new_method = {
            'name': 'New Method',
            'price': '7.50',
            'description': 'New shipping method',
            'is_active': True
        }
        
        response = self.client.post(self.list_url, new_method)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ShippingMethod.objects.count(), 4)
        self.assertTrue(ShippingMethod.objects.filter(name='New Method').exists())