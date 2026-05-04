# payments/tests/test_serializers.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from payments.models import PaymentMethod, Payment, PaymentRefund
from payments.serializers import (
    PaymentMethodSerializer, PaymentCreateSerializer, PaymentRefundCreateSerializer
)
from orders.models import Order
from decimal import Decimal

User = get_user_model()

class PaymentMethodSerializerTest(TestCase):
    def setUp(self):
        self.payment_method = PaymentMethod.objects.create(
            name='Credit Card',
            payment_type='credit_card',
            description='Credit card payment',
            processing_fee=Decimal('2.50'),
            processing_fee_percentage=Decimal('2.9'),
            is_active=True
        )
        self.serializer = PaymentMethodSerializer(instance=self.payment_method)
    
    def test_contains_expected_fields(self):
        """Test serializer contains expected fields"""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'name', 'payment_type', 'description', 'is_active',
             'processing_fee', 'processing_fee_percentage', 'min_amount',
             'max_amount', 'processing_fee_display', 'created_at']
        )
    
    def test_processing_fee_display(self):
        """Test processing fee display field"""
        data = self.serializer.data
        expected_display = "$2.50 + 2.9%"
        self.assertEqual(data['processing_fee_display'], expected_display)


class PaymentCreateSerializerTest(TestCase):
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
            total_amount=Decimal('100.00')
        )
        
        # Create payment method
        self.payment_method = PaymentMethod.objects.create(
            name='Credit Card',
            payment_type='credit_card',
            processing_fee=Decimal('2.50'),
            min_amount=Decimal('10.00'),
            max_amount=Decimal('5000.00')
        )
        
        # Payment data
        self.payment_data = {
            'order': self.order.id,
            'payment_method': self.payment_method.id,
            'amount': '100.00',
            'currency': 'USD',
            'billing_address': '123 Test St, Test City, 12345'
        }
        
        self.serializer = PaymentCreateSerializer(
            data=self.payment_data,
            context={'request': type('obj', (object,), {'user': self.user})}
        )
    
    def test_validate_success(self):
        """Test successful validation"""
        self.assertTrue(self.serializer.is_valid())
    
    def test_create_payment(self):
        """Test creating payment with serializer"""
        self.assertTrue(self.serializer.is_valid())
        payment = self.serializer.save()
        
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.order, self.order)
        self.assertEqual(payment.payment_method, self.payment_method)
        self.assertEqual(payment.amount, Decimal('100.00'))
        self.assertEqual(payment.processing_fee, Decimal('2.50'))
    
    def test_validate_amount_below_minimum(self):
        """Test validation fails for amount below minimum"""
        self.payment_data['amount'] = '5.00'  # Below minimum of 10.00
        serializer = PaymentCreateSerializer(
            data=self.payment_data,
            context={'request': type('obj', (object,), {'user': self.user})}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('Amount must be at least', str(serializer.errors))
    
    def test_validate_amount_above_maximum(self):
        """Test validation fails for amount above maximum"""
        self.payment_data['amount'] = '6000.00'  # Above maximum of 5000.00
        serializer = PaymentCreateSerializer(
            data=self.payment_data,
            context={'request': type('obj', (object,), {'user': self.user})}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('Amount cannot exceed', str(serializer.errors))


class PaymentRefundCreateSerializerTest(TestCase):
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
        
        # Refund data
        self.refund_data = {
            'payment': self.payment.id,
            'amount': '50.00',
            'reason': 'customer_request',
            'notes': 'Customer requested refund'
        }
        
        self.serializer = PaymentRefundCreateSerializer(
            data=self.refund_data,
            context={'request': type('obj', (object,), {'user': self.staff_user})}
        )
    
    def test_validate_success(self):
        """Test successful validation"""
        self.assertTrue(self.serializer.is_valid())
    
    def test_create_refund(self):
        """Test creating refund with serializer"""
        self.assertTrue(self.serializer.is_valid())
        refund = self.serializer.save()
        
        self.assertEqual(refund.payment, self.payment)
        self.assertEqual(refund.initiated_by, self.staff_user)
        self.assertEqual(refund.amount, Decimal('50.00'))
        self.assertEqual(refund.reason, 'customer_request')
    
    def test_validate_refund_amount_exceeds_available(self):
        """Test validation fails when refund amount exceeds available amount"""
        self.refund_data['amount'] = '150.00'  # More than payment amount
        serializer = PaymentRefundCreateSerializer(
            data=self.refund_data,
            context={'request': type('obj', (object,), {'user': self.staff_user})}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('Refund amount cannot exceed', str(serializer.errors))
    
    def test_validate_payment_not_refundable(self):
        """Test validation fails for non-completed payment"""
        # Create pending payment
        pending_payment = Payment.objects.create(
            user=self.user,
            order=self.order,
            payment_method=self.payment_method,
            amount=Decimal('100.00'),
            currency='USD',
            billing_address='123 Test St',
            status='pending'
        )
        
        self.refund_data['payment'] = pending_payment.id
        serializer = PaymentRefundCreateSerializer(
            data=self.refund_data,
            context={'request': type('obj', (object,), {'user': self.staff_user})}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('Only completed payments can be refunded', str(serializer.errors))