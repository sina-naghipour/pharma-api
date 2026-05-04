# orders/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem, ShippingMethod, PaymentMethod
from products.models import Product, Category
from decimal import Decimal

User = get_user_model()

class OrderModelTest(TestCase):
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
        
        # Create shipping and payment methods
        self.shipping_method = ShippingMethod.objects.create(
            name='Standard Shipping',
            price=Decimal('5.00'),
            description='3-5 business days'
        )
        
        self.payment_method = PaymentMethod.objects.create(
            name='Credit Card',
            is_active=True
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

    def test_order_creation(self):
        """Test creating an order"""
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.status, 'pending')
        self.assertEqual(self.order.shipping_method, self.shipping_method)
        self.assertEqual(self.order.payment_method, 'credit_card')
        self.assertEqual(self.order.subtotal, Decimal('25.00'))
        self.assertEqual(self.order.shipping_cost, Decimal('5.00'))
        self.assertEqual(self.order.tax, Decimal('2.50'))
        self.assertEqual(self.order.total_amount, Decimal('32.50'))
    
    def test_order_str(self):
        """Test the string representation of an order"""
        expected_str = f"Order #{self.order.id} - {self.user.email}"
        self.assertEqual(str(self.order), expected_str)
    
    def test_order_item_creation(self):
        """Test creating order items"""
        self.assertEqual(self.order_item1.order, self.order)
        self.assertEqual(self.order_item1.product, self.product1)
        self.assertEqual(self.order_item1.quantity, 1)
        self.assertEqual(self.order_item1.price, Decimal('10.00'))
        
        self.assertEqual(self.order_item2.order, self.order)
        self.assertEqual(self.order_item2.product, self.product2)
        self.assertEqual(self.order_item2.quantity, 1)
        self.assertEqual(self.order_item2.price, Decimal('15.00'))
    
    def test_order_item_str(self):
        """Test the string representation of an order item"""
        expected_str = f"{self.product1.name} x 1"
        self.assertEqual(str(self.order_item1), expected_str)
    
    def test_order_item_total(self):
        """Test calculating order item total"""
        self.assertEqual(self.order_item1.get_total(), Decimal('10.00'))
        self.assertEqual(self.order_item2.get_total(), Decimal('15.00'))
    
    def test_shipping_method_str(self):
        """Test the string representation of a shipping method"""
        self.assertEqual(str(self.shipping_method), 'Standard Shipping')
    
    def test_payment_method_str(self):
        """Test the string representation of a payment method"""
        self.assertEqual(str(self.payment_method), 'Credit Card')


class OrderStatusTransitionTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
        # Create order
        self.order = Order.objects.create(
            user=self.user,
            status='pending',
            shipping_address='123 Test St, Test City, 12345',
            billing_address='123 Test St, Test City, 12345',
            payment_method='credit_card',
            subtotal=Decimal('25.00'),
            shipping_cost=Decimal('5.00'),
            tax=Decimal('2.50'),
            total_amount=Decimal('32.50')
        )
    
    def test_order_status_transition(self):
        """Test order status transitions"""
        # Pending -> Processing
        self.order.status = 'processing'
        self.order.save()
        self.assertEqual(self.order.status, 'processing')
        
        # Processing -> Shipped
        self.order.status = 'shipped'
        self.order.save()
        self.assertEqual(self.order.status, 'shipped')
        
        # Shipped -> Delivered
        self.order.status = 'delivered'
        self.order.save()
        self.assertEqual(self.order.status, 'delivered')
    
    def test_order_cancellation(self):
        """Test order cancellation"""
        self.order.status = 'cancelled'
        self.order.save()
        self.assertEqual(self.order.status, 'cancelled')