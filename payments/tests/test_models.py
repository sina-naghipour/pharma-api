# payments/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from payments.models import (
    PaymentMethod, PaymentGateway, Payment, PaymentRefund,
    SavedPaymentMethod, PaymentWebhook, PaymentDispute
)
from orders.models import Order
from products.models import Product, Category
from decimal import Decimal

User = get_user_model()

class PaymentMethodModelTest(TestCase):
    def setUp(self):
        self.payment_method = PaymentMethod.objects.create(
            name='Credit Card',
            payment_type='credit_card',
            description='Credit card payment',
            processing_fee=Decimal('2.50'),
            processing_fee_percentage=Decimal('2.9'),
            min_amount=Decimal('1.00'),
            max_amount=Decimal('10000.00'),
            is_active=True
        )
    
    def test_payment_method_creation(self):
        """Test creating a payment method"""
        self.assertEqual(self.payment_method.name, 'Credit Card')
        self.assertEqual(self.payment_method.payment_type, 'credit_card')
        self.assertEqual(self.payment_method.processing_fee, Decimal('2.50'))
        self.assertEqual(self.payment_method.processing_fee_percentage, Decimal('2.9'))
        self.assertTrue(self.payment_method.is_active)
    
    def test_calculate_processing_fee(self):
        """Test processing fee calculation"""
        # Test with $100 amount
        amount = Decimal('100.00')
        expected_fee = Decimal('2.50') + (amount * Decimal('2.9') / 100)
        calculated_fee = self.payment_method.calculate_processing_fee(amount)
        self.assertEqual(calculated_fee, expected_fee)
    
    def test_payment_method_str(self):
        """Test string representation"""
        self.assertEqual(str(self.payment_method), 'Credit Card')


class PaymentGatewayModelTest(TestCase):
    def setUp(self):
        self.gateway = PaymentGateway.objects.create(
            name='Stripe Gateway',
            gateway_type='stripe',
            is_active=True,
            is_test_mode=True,
            api_key='pk_test_123',
            secret_key='sk_test_123',
            supported_currencies=['USD', 'EUR']
        )
    
    def test_gateway_creation(self):
        """Test creating a payment gateway"""
        self.assertEqual(self.gateway.name, 'Stripe Gateway')
        self.assertEqual(self.gateway.gateway_type, 'stripe')
        self.assertTrue(self.gateway.is_active)
        self.assertTrue(self.gateway.is_test_mode)
        self.assertEqual(self.gateway.supported_currencies, ['USD', 'EUR'])
    
    def test_gateway_str(self):
        """Test string representation"""
        expected_str = "Stripe Gateway (Test)"
        self.assertEqual(str(self.gateway), expected_str)


class PaymentModelTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
        # Create category and product
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            price=Decimal('50.00'),
            category=self.category
        )
        
        # Create order
        self.order = Order.objects.create(
            user=self.user,
            status='pending',
            total_amount=Decimal('100.00')
        )
        
        # Create payment method and gateway
        self.payment_method = PaymentMethod.objects.create(
            name='Credit Card',
            payment_type='credit_card',
            processing_fee=Decimal('2.50')
        )
        
        self.gateway = PaymentGateway.objects.create(
            name='Stripe',
            gateway_type='stripe'
        )
        
        # Create payment
        self.payment = Payment.objects.create(
            user=self.user,
            order=self.order,
            payment_method=self.payment_method,
            gateway=self.gateway,
            amount=Decimal('100.00'),
            currency='USD',
            processing_fee=Decimal('2.50'),
            billing_address='123 Test St, Test City, 12345',
            status='pending'
        )
    
    def test_payment_creation(self):
        """Test creating a payment"""
        self.assertEqual(self.payment.user, self.user)
        self.assertEqual(self.payment.order, self.order)
        self.assertEqual(self.payment.payment_method, self.payment_method)
        self.assertEqual(self.payment.gateway, self.gateway)
        self.assertEqual(self.payment.amount, Decimal('100.00'))
        self.assertEqual(self.payment.currency, 'USD')
        self.assertEqual(self.payment.processing_fee, Decimal('2.50'))
        self.assertEqual(self.payment.net_amount, Decimal('97.50'))
        self.assertEqual(self.payment.status, 'pending')
    
    def test_payment_str(self):
        """Test string representation"""
        expected_str = f"Payment {self.payment.id} - 100.00 USD"
        self.assertEqual(str(self.payment), expected_str)


class PaymentRefundModelTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
        # Create staff user
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            password='password123',
            is_staff=True
        )
        
        # Create order
        self.order = Order.objects.create(
            user=self.user,
            status='completed',
            total_amount=Decimal('100.00')
        )
        
        # Create payment method
        self.payment_method = PaymentMethod.objects.create(
            name='Credit Card',
            payment_type='credit_card'
        )
        
        # Create payment
        self.payment = Payment.objects.create(
            user=self.user,
            order=self.order,
            payment_method=self.payment_method,
            amount=Decimal('100.00'),
            currency='USD',
            billing_address='123 Test St',
            status='completed'
        )
        
        # Create refund
        self.refund = PaymentRefund.objects.create(
            payment=self.payment,
            initiated_by=self.staff_user,
            amount=Decimal('50.00'),
            reason='customer_request',
            notes='Customer requested partial refund',
            status='pending'
        )
    
    def test_refund_creation(self):
        """Test creating a refund"""
        self.assertEqual(self.refund.payment, self.payment)
        self.assertEqual(self.refund.initiated_by, self.staff_user)
        self.assertEqual(self.refund.amount, Decimal('50.00'))
        self.assertEqual(self.refund.reason, 'customer_request')
        self.assertEqual(self.refund.notes, 'Customer requested partial refund')
        self.assertEqual(self.refund.status, 'pending')
    
    def test_refund_str(self):
        """Test string representation"""
        expected_str = f"Refund {self.refund.id} - 50.00"
        self.assertEqual(str(self.refund), expected_str)


class SavedPaymentMethodModelTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
        # Create payment method
        self.payment_method = PaymentMethod.objects.create(
            name='Credit Card',
            payment_type='credit_card'
        )
        
        # Create saved payment method
        self.saved_method = SavedPaymentMethod.objects.create(
            user=self.user,
            payment_method=self.payment_method,
            card_type='visa',
            last_four_digits='1234',
            expiry_month=12,
            expiry_year=2025,
            cardholder_name='John Doe',
            gateway_token='tok_123456789',
            is_default=True
        )
    
    def test_saved_method_creation(self):
        """Test creating a saved payment method"""
        self.assertEqual(self.saved_method.user, self.user)
        self.assertEqual(self.saved_method.payment_method, self.payment_method)
        self.assertEqual(self.saved_method.card_type, 'visa')
        self.assertEqual(self.saved_method.last_four_digits, '1234')
        self.assertEqual(self.saved_method.expiry_month, 12)
        self.assertEqual(self.saved_method.expiry_year, 2025)
        self.assertEqual(self.saved_method.cardholder_name, 'John Doe')
        self.assertTrue(self.saved_method.is_default)
    
    def test_saved_method_str(self):
        """Test string representation"""
        expected_str = "Visa ending in 1234"
        self.assertEqual(str(self.saved_method), expected_str)