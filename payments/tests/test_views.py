# payments/tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from payments.models import PaymentMethod, Payment, PaymentRefund, SavedPaymentMethod
from orders.models import Order
from decimal import Decimal

User = get_user_model()

class PaymentMethodViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create payment methods
        self.payment_method1 = PaymentMethod.objects.create(
            name='Credit Card',
            payment_type='credit_card',
            processing_fee=Decimal('2.50'),
            is_active=True
        )
        
        self.payment_method2 = PaymentMethod.objects.create(
            name='PayPal',
            payment_type='paypal',
            processing_fee_percentage=Decimal('3.5'),
            is_active=True
        )
        
        self.inactive_method = PaymentMethod.objects.create(
            name='Inactive Method',
            payment_type='other',
            is_active=False
        )
        
        self.list_url = reverse('payments:paymentmethod-list')
        self.detail_url = reverse('payments:paymentmethod-detail', args=[self.payment_method1.id])
        self.calculate_fee_url = reverse('payments:paymentmethod-calculate-fee', args=[self.payment_method1.id])
    
    def test_get_payment_methods(self):
        """Test retrieving active payment methods"""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Only active methods
        
        method_names = [method['name'] for method in response.data]
        self.assertIn(self.payment_method1.name, method_names)
        self.assertIn(self.payment_method2.name, method_names)
        self.assertNotIn(self.inactive_method.name, method_names)
    
    def test_calculate_processing_fee(self):
        """Test calculating processing fee"""
        data = {'amount': 100}
        response = self.client.post(self.calculate_fee_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], 100)
        self.assertEqual(response.data['processing_fee'], 2.50)
        self.assertEqual(response.data['total'], 102.50)


class PaymentViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='password123'
        )
        
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpassword123'
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
            min_amount=Decimal('10.00')
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
        
        # URLs
        self.list_url = reverse('payments:payment-list')
        self.detail_url = reverse('payments:payment-detail', args=[self.payment.id])
        self.refund_url = reverse('payments:payment-refund', args=[self.payment.id])
        self.my_payments_url = reverse('payments:payment-my-payments')
    
    def test_get_payments_unauthenticated(self):
        """Test that unauthenticated users cannot access payments"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_user_payments(self):
        """Test that user can access their own payments"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.payment.id))
    
    def test_admin_can_access_all_payments(self):
        """Test that admin can access all payments"""
        # Create another user's payment
        other_order = Order.objects.create(
            user=self.other_user,
            status='pending',
            total_amount=Decimal('50.00')
        )
        
        other_payment = Payment.objects.create(
            user=self.other_user,
            order=other_order,
            payment_method=self.payment_method,
            amount=Decimal('50.00'),
            currency='USD',
            billing_address='456 Other St',
            status='pending'
        )
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_create_payment(self):
        """Test creating a new payment"""
        self.client.force_authenticate(user=self.user)
        
        payment_data = {
            'order': self.order.id,
            'payment_method': self.payment_method.id,
            'amount': '75.00',
            'currency': 'USD',
            'billing_address': '789 New St, New City, 54321'
        }
        
        response = self.client.post(self.list_url, payment_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check payment was created
        self.assertEqual(Payment.objects.count(), 2)
    
    def test_refund_payment_admin_only(self):
        """Test that only admin can initiate refunds"""
        self.client.force_authenticate(user=self.user)
        
        refund_data = {
            'amount': '25.00',
            'reason': 'customer_request',
            'notes': 'Customer requested refund'
        }
        
        response = self.client.post(self.refund_url, refund_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test admin can create refund
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(self.refund_url, refund_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check refund was created
        self.assertEqual(PaymentRefund.objects.count(), 1)
    
    def test_my_payments_endpoint(self):
        """Test my payments endpoint"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.my_payments_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.payment.id))


class SavedPaymentMethodViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
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
            cardholder_name='John Doe',
            is_default=True
        )
        
        # URLs
        self.list_url = reverse('payments:saved-method-list')
        self.detail_url = reverse('payments:saved-method-detail', args=[self.saved_method.id])
        self.set_default_url = reverse('payments:saved-method-set-default', args=[self.saved_method.id])
    
    
def test_get_saved_methods_unauthenticated(self):
    """Test that unauthenticated users cannot access saved methods"""
    response = self.client.get(self.list_url)
    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
def test_get_user_saved_methods(self):
    """Test that user can access their own saved methods"""
    self.client.force_authenticate(user=self.user)
    response = self.client.get(self.list_url)
    
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(len(response.data), 1)
    self.assertEqual(response.data[0]['id'], self.saved_method.id)
    
def test_create_saved_method(self):
    """Test creating a saved payment method"""
    self.client.force_authenticate(user=self.user)
    
    method_data = {
    'payment_method': self.payment_method.id,
    'card_type': 'mastercard',
    'last_four_digits': '5678',
    'expiry_month': 12,
    'expiry_year': 2025,
    'cardholder_name': 'Jane Doe',
    'gateway_token': 'tok_987654321'
    }
    
    response = self.client.post(self.list_url, method_data)
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    # Check saved method was created
    self.assertEqual(SavedPaymentMethod.objects.count(), 2)
    new_method = SavedPaymentMethod.objects.get(last_four_digits='5678')
    self.assertEqual(new_method.user, self.user)
    
def test_set_default_method(self):
    """Test setting a payment method as default"""
    # Create another saved method
    other_method = SavedPaymentMethod.objects.create(
    user=self.user,
    payment_method=self.payment_method,
    card_type='mastercard',
    last_four_digits='5678',
    cardholder_name='Jane Doe',
    is_default=False
    )
    
    self.client.force_authenticate(user=self.user)
    
    # Set other method as default
    set_default_url = reverse('payments:saved-method-set-default', args=[other_method.id])
    response = self.client.post(set_default_url)
    
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    # Check that other method is now default and original is not
    self.saved_method.refresh_from_db()
    other_method.refresh_from_db()
    
    self.assertFalse(self.saved_method.is_default)
    self.assertTrue(other_method.is_default)
    
def test_delete_saved_method(self):
    """Test deleting a saved payment method"""
    self.client.force_authenticate(user=self.user)
    
    response = self.client.delete(self.detail_url)
    self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    # Check saved method was deleted
    self.assertEqual(SavedPaymentMethod.objects.count(), 0)