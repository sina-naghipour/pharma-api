# payments/tests/test_services.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from payments.models import (
    PaymentMethod, PaymentGateway, Payment, PaymentRefund, PaymentWebhook
)
from payments.services import PaymentProcessor, WebhookProcessor, DisputeProcessor
from orders.models import Order
from decimal import Decimal

User = get_user_model()

class PaymentProcessorTest(TestCase):
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
            payment_type='credit_card'
        )
        
        # Create payment gateway
        self.stripe_gateway = PaymentGateway.objects.create(
            name='Stripe',
            gateway_type='stripe',
            is_active=True,
            secret_key='sk_test_123456789'
        )
        
        self.paypal_gateway = PaymentGateway.objects.create(
            name='PayPal',
            gateway_type='paypal',
            is_active=True,
            api_key='paypal_client_id',
            secret_key='paypal_client_secret',
            endpoint_url='https://api.sandbox.paypal.com'
        )
        
        # Create payment
        self.stripe_payment = Payment.objects.create(
            user=self.user,
            order=self.order,
            payment_method=self.payment_method,
            gateway=self.stripe_gateway,
            amount=Decimal('100.00'),
            currency='USD',
            billing_address='123 Test St',
            status='pending'
        )
        
        self.paypal_payment = Payment.objects.create(
            user=self.user,
            order=self.order,
            payment_method=self.payment_method,
            gateway=self.paypal_gateway,
            amount=Decimal('100.00'),
            currency='USD',
            billing_address='123 Test St',
            status='pending'
        )
        
        self.processor = PaymentProcessor()
    
    @patch('payments.services.stripe')
    def test_process_stripe_payment_success(self, mock_stripe):
        """Test successful Stripe payment processing"""
        # Mock Stripe response
        mock_intent = MagicMock()
        mock_intent.id = 'pi_test_123456789'
        mock_intent.client_secret = 'pi_test_123456789_secret_123'
        mock_intent.status = 'succeeded'
        mock_stripe.PaymentIntent.create.return_value = mock_intent
        
        result = self.processor.process_payment(self.stripe_payment)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['transaction_id'], 'pi_test_123456789')
        self.assertIn('client_secret', result['gateway_response'])
        
        # Verify Stripe was called with correct parameters
        mock_stripe.PaymentIntent.create.assert_called_once()
        call_args = mock_stripe.PaymentIntent.create.call_args[1]
        self.assertEqual(call_args['amount'], 10000)  # $100 in cents
        self.assertEqual(call_args['currency'], 'usd')
    
    @patch('payments.services.stripe')
    def test_process_stripe_payment_failure(self, mock_stripe):
        """Test failed Stripe payment processing"""
        # Mock Stripe exception
        mock_stripe.PaymentIntent.create.side_effect = Exception("Card declined")
        
        result = self.processor.process_payment(self.stripe_payment)
        
        self.assertFalse(result['success'])
        self.assertIn('Card declined', result['error'])
    
    @patch('payments.services.requests')
    def test_process_paypal_payment_success(self, mock_requests):
        """Test successful PayPal payment processing"""
        # Mock PayPal token response
        token_response = MagicMock()
        token_response.status_code = 200
        token_response.json.return_value = {'access_token': 'test_token_123'}
        
        # Mock PayPal order response
        order_response = MagicMock()
        order_response.status_code = 201
        order_response.json.return_value = {
            'id': 'paypal_order_123',
            'status': 'CREATED'
        }
        
        mock_requests.post.side_effect = [token_response, order_response]
        
        result = self.processor.process_payment(self.paypal_payment)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['transaction_id'], 'paypal_order_123')
        
        # Verify PayPal API calls
        self.assertEqual(mock_requests.post.call_count, 2)
    
    @patch('payments.services.requests')
    def test_process_paypal_payment_failure(self, mock_requests):
        """Test failed PayPal payment processing"""
        # Mock failed token response
        token_response = MagicMock()
        token_response.status_code = 401
        token_response.json.return_value = {'error': 'invalid_client'}
        
        mock_requests.post.return_value = token_response
        
        result = self.processor.process_payment(self.paypal_payment)
        
        self.assertFalse(result['success'])
        self.assertIn('PayPal', result['error'])
    
    def test_process_payment_unsupported_gateway(self):
        """Test processing payment with unsupported gateway"""
        # Create unsupported gateway
        unsupported_gateway = PaymentGateway.objects.create(
            name='Unsupported',
            gateway_type='unsupported',
            is_active=True
        )
        
        payment = Payment.objects.create(
            user=self.user,
            order=self.order,
            payment_method=self.payment_method,
            gateway=unsupported_gateway,
            amount=Decimal('100.00'),
            currency='USD',
            billing_address='123 Test St',
            status='pending'
        )
        
        result = self.processor.process_payment(payment)
        
        self.assertFalse(result['success'])
        self.assertIn('Unsupported gateway', result['error'])
    
    @patch('payments.services.stripe')
    def test_process_stripe_refund_success(self, mock_stripe):
        """Test successful Stripe refund processing"""
        # Create refund
        refund = PaymentRefund.objects.create(
            payment=self.stripe_payment,
            initiated_by=self.user,
            amount=Decimal('50.00'),
            reason='customer_request'
        )
        
        # Mock Stripe refund response
        mock_refund = MagicMock()
        mock_refund.id = 're_test_123456789'
        mock_refund.status = 'succeeded'
        mock_refund.amount = 5000  # $50 in cents
        mock_stripe.Refund.create.return_value = mock_refund
        
        result = self.processor.process_refund(refund)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['refund_id'], 're_test_123456789')
        
        # Verify Stripe refund was called correctly
        mock_stripe.Refund.create.assert_called_once()
        call_args = mock_stripe.Refund.create.call_args[1]
        self.assertEqual(call_args['amount'], 5000)  # $50 in cents


class WebhookProcessorTest(TestCase):
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
            payment_type='credit_card'
        )
        
        # Create gateway
        self.stripe_gateway = PaymentGateway.objects.create(
            name='Stripe',
            gateway_type='stripe',
            is_active=True
        )
        
        # Create payment
        self.payment = Payment.objects.create(
            user=self.user,
            order=self.order,
            payment_method=self.payment_method,
            gateway=self.stripe_gateway,
            amount=Decimal('100.00'),
            currency='USD',
            billing_address='123 Test St',
            status='pending',
            gateway_transaction_id='pi_test_123456789'
        )
        
        self.processor = WebhookProcessor()
    
    def test_process_stripe_payment_succeeded_webhook(self):
        """Test processing Stripe payment succeeded webhook"""
        # Create webhook
        webhook = PaymentWebhook.objects.create(
            gateway=self.stripe_gateway,
            event_type='payment_intent.succeeded',
            payload={
                'data': {
                    'object': {
                        'id': 'pi_test_123456789',
                        'status': 'succeeded'
                    }
                }
            },
            status='received'
        )
        
        result = self.processor.process_webhook(webhook)
        
        self.assertTrue(result['success'])
        
        # Check payment status was updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'completed')
        self.assertIsNotNone(self.payment.processed_at)
        
        # Check webhook was linked to payment
        webhook.refresh_from_db()
        self.assertEqual(webhook.payment, self.payment)
    
    def test_process_stripe_payment_failed_webhook(self):
        """Test processing Stripe payment failed webhook"""
        # Create webhook
        webhook = PaymentWebhook.objects.create(
            gateway=self.stripe_gateway,
            event_type='payment_intent.payment_failed',
            payload={
                'data': {
                    'object': {
                        'id': 'pi_test_123456789',
                        'status': 'requires_payment_method'
                    }
                }
            },
            status='received'
        )
        
        result = self.processor.process_webhook(webhook)
        
        self.assertTrue(result['success'])
        
        # Check payment status was updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'failed')
    
    def test_process_webhook_payment_not_found(self):
        """Test processing webhook when payment is not found"""
        # Create webhook with non-existent payment intent
        webhook = PaymentWebhook.objects.create(
            gateway=self.stripe_gateway,
            event_type='payment_intent.succeeded',
            payload={
                'data': {
                    'object': {
                        'id': 'pi_nonexistent_123',
                        'status': 'succeeded'
                    }
                }
            },
            status='received'
        )
        
        result = self.processor.process_webhook(webhook)
        
        # Should still succeed but log warning
        self.assertTrue(result['success'])
    
    def test_process_unsupported_gateway_webhook(self):
        """Test processing webhook from unsupported gateway"""
        # Create unsupported gateway
        unsupported_gateway = PaymentGateway.objects.create(
            name='Unsupported',
            gateway_type='unsupported',
            is_active=True
        )
        
        webhook = PaymentWebhook.objects.create(
            gateway=unsupported_gateway,
            event_type='test.event',
            payload={'test': 'data'},
            status='received'
        )
        
        result = self.processor.process_webhook(webhook)
        
        self.assertFalse(result['success'])
        self.assertIn('Unsupported gateway', result['error'])


class DisputeProcessorTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
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
        
        # Create gateway
        self.stripe_gateway = PaymentGateway.objects.create(
            name='Stripe',
            gateway_type='stripe',
            is_active=True,
            secret_key='sk_test_123456789'
        )
        
        # Create payment
        self.payment = Payment.objects.create(
            user=self.user,
            order=self.order,
            payment_method=self.payment_method,
            gateway=self.stripe_gateway,
            amount=Decimal('100.00'),
            currency='USD',
            billing_address='123 Test St',
            status='completed',
            gateway_transaction_id='pi_test_123456789'
        )
        
        # Create dispute
        from payments.models import PaymentDispute
        self.dispute = PaymentDispute.objects.create(
            payment=self.payment,
            gateway_dispute_id='dp_test_123456789',
            amount=Decimal('100.00'),
            currency='USD',
            reason='fraudulent',
            status='open'
        )
        
        self.processor = DisputeProcessor()
    
    @patch('payments.services.stripe')
    def test_submit_stripe_evidence_success(self, mock_stripe):
        """Test successful Stripe evidence submission"""
        evidence = {
            'customer_communication': 'Email thread with customer',
            'receipt': 'Receipt showing purchase',
            'shipping_documentation': 'Tracking number and delivery confirmation'
        }
        
        # Mock Stripe dispute modify
        mock_stripe.Dispute.modify.return_value = MagicMock()
        
        result = self.processor.submit_evidence(self.dispute, evidence)
        
        self.assertTrue(result['success'])
        
        # Verify Stripe was called correctly
        mock_stripe.Dispute.modify.assert_called_once_with(
            'dp_test_123456789',
            evidence=evidence
        )
    
    @patch('payments.services.stripe')
    def test_submit_stripe_evidence_failure(self, mock_stripe):
        """Test failed Stripe evidence submission"""
        evidence = {'customer_communication': 'Email thread'}
        
        # Mock Stripe exception
        mock_stripe.Dispute.modify.side_effect = Exception("Evidence submission failed")
        
        result = self.processor.submit_evidence(self.dispute, evidence)
        
        self.assertFalse(result['success'])
        self.assertIn('Evidence submission failed', result['error'])
    
    def test_submit_evidence_unsupported_gateway(self):
        """Test evidence submission for unsupported gateway"""
        # Create payment with unsupported gateway
        unsupported_gateway = PaymentGateway.objects.create(
            name='Unsupported',
            gateway_type='unsupported',
            is_active=True
        )
        
        unsupported_payment = Payment.objects.create(
            user=self.user,
            order=self.order,
            payment_method=self.payment_method,
            gateway=unsupported_gateway,
            amount=Decimal('100.00'),
            currency='USD',
            billing_address='123 Test St',
            status='completed'
        )
        
        from payments.models import PaymentDispute
        unsupported_dispute = PaymentDispute.objects.create(
            payment=unsupported_payment,
            gateway_dispute_id='dp_unsupported_123',
            amount=Decimal('100.00'),
            currency='USD',
            reason='fraudulent',
            status='open'
        )
        
        evidence = {'test': 'evidence'}
        result = self.processor.submit_evidence(unsupported_dispute, evidence)
        
        self.assertFalse(result['success'])
        self.assertIn('not supported', result['error'])