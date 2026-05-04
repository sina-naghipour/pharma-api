# payments/services.py
from django.conf import settings
from django.utils import timezone
from .models import Payment, PaymentRefund, PaymentDispute, PaymentWebhook
import logging
import requests
import json

logger = logging.getLogger(__name__)

class PaymentProcessor:
    """Service for processing payments"""
    
    def process_payment(self, payment):
        """Process a payment transaction"""
        try:
            # Determine gateway based on payment method
            gateway = payment.gateway or payment.payment_method.gateway_config.get('default_gateway')
            
            if not gateway:
                raise ValueError("No payment gateway configured")
            
            # Route to appropriate processor
            if gateway.gateway_type == 'stripe':
                return self._process_stripe_payment(payment)
            elif gateway.gateway_type == 'paypal':
                return self._process_paypal_payment(payment)
            else:
                raise ValueError(f"Unsupported gateway: {gateway.gateway_type}")
        
        except Exception as e:
            logger.error(f"Payment processing failed for {payment.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_details': {'exception': str(e)}
            }
    
    def _process_stripe_payment(self, payment):
        """Process payment via Stripe"""
        try:
            import stripe
            stripe.api_key = payment.gateway.secret_key
            
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(payment.amount * 100), # Convert to cents
                currency=payment.currency.lower(),
                payment_method_types=['card'],
                metadata={
                    'payment_id': str(payment.id),
                    'order_id': str(payment.order.id),
                    'user_id': str(payment.user.id),
                }
            )
            
            return {
                'success': True,
                'transaction_id': intent.id,
                'gateway_response': {
                    'intent_id': intent.id,
                    'client_secret': intent.client_secret,
                    'status': intent.status
                }
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_details': {'stripe_error': str(e)}
            }
    
    def _process_paypal_payment(self, payment):
        """Process payment via PayPal"""
        try:
            # PayPal API implementation
            paypal_config = payment.gateway.configuration
            
            # Create PayPal order
            order_data = {
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'amount': {
                        'currency_code': payment.currency,
                        'value': str(payment.amount)
                    },
                    'reference_id': str(payment.id)
                }]
            }
            
            # Make API call to PayPal
            response = requests.post(
                f"{payment.gateway.endpoint_url}/v2/checkout/orders",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {self._get_paypal_access_token(payment.gateway)}"
                },
                json=order_data
            )
            
            if response.status_code == 201:
                order = response.json()
                return {
                    'success': True,
                    'transaction_id': order['id'],
                    'gateway_response': order
                }
            else:
                return {
                    'success': False,
                    'error': 'PayPal order creation failed',
                    'error_details': response.json()
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_details': {'paypal_error': str(e)}
            }
    
    def _get_paypal_access_token(self, gateway):
        """Get PayPal access token"""
        try:
            response = requests.post(
                f"{gateway.endpoint_url}/v1/oauth2/token",
                headers={
                    'Accept': 'application/json',
                    'Accept-Language': 'en_US',
                },
                auth=(gateway.api_key, gateway.secret_key),
                data={'grant_type': 'client_credentials'}
            )
            
            if response.status_code == 200:
                return response.json()['access_token']
            else:
                raise Exception("Failed to get PayPal access token")
        
        except Exception as e:
            logger.error(f"PayPal token error: {str(e)}")
            raise
    
    def process_refund(self, refund):
        """Process a refund"""
        try:
            payment = refund.payment
            gateway = payment.gateway
            
            if gateway.gateway_type == 'stripe':
                return self._process_stripe_refund(refund)
            elif gateway.gateway_type == 'paypal':
                return self._process_paypal_refund(refund)
            else:
                raise ValueError(f"Unsupported gateway for refunds: {gateway.gateway_type}")
        
        except Exception as e:
            logger.error(f"Refund processing failed for {refund.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_details': {'exception': str(e)}
            }
    
    def _process_stripe_refund(self, refund):
        """Process refund via Stripe"""
        try:
            import stripe
            stripe.api_key = refund.payment.gateway.secret_key
            
            stripe_refund = stripe.Refund.create(
                payment_intent=refund.payment.gateway_transaction_id,
                amount=int(refund.amount * 100), # Convert to cents
                metadata={
                    'refund_id': str(refund.id),
                    'reason': refund.reason
                }
            )
            
            return {
                'success': True,
                'refund_id': stripe_refund.id,
                'gateway_response': {
                    'refund_id': stripe_refund.id,
                    'status': stripe_refund.status,
                    'amount': stripe_refund.amount / 100
                }
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_details': {'stripe_error': str(e)}
            }
    
    def _process_paypal_refund(self, refund):
        """Process refund via PayPal"""
        try:
            # PayPal refund implementation
            refund_data = {
                'amount': {
                    'currency_code': refund.payment.currency,
                    'value': str(refund.amount)
                },
                'note_to_payer': refund.notes or 'Refund processed'
            }
            
            response = requests.post(
                f"{refund.payment.gateway.endpoint_url}/v2/payments/captures/{refund.payment.gateway_transaction_id}/refund",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {self._get_paypal_access_token(refund.payment.gateway)}"
                },
                json=refund_data
            )
            
            if response.status_code == 201:
                paypal_refund = response.json()
                return {
                    'success': True,
                    'refund_id': paypal_refund['id'],
                    'gateway_response': paypal_refund
                }
            else:
                return {
                    'success': False,
                    'error': 'PayPal refund failed',
                    'error_details': response.json()
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_details': {'paypal_error': str(e)}
            }


class WebhookProcessor:
    """Service for processing payment webhooks"""
    
    def process_webhook(self, webhook):
        """Process a payment webhook"""
        try:
            if webhook.gateway.gateway_type == 'stripe':
                return self._process_stripe_webhook(webhook)
            elif webhook.gateway.gateway_type == 'paypal':
                return self._process_paypal_webhook(webhook)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported gateway: {webhook.gateway.gateway_type}'
                }
        
        except Exception as e:
            logger.error(f"Webhook processing failed for {webhook.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_stripe_webhook(self, webhook):
        """Process Stripe webhook"""
        try:
            event_type = webhook.event_type
            payload = webhook.payload
            
            if event_type == 'payment_intent.succeeded':
                # Update payment status
                payment_intent_id = payload['data']['object']['id']
                try:
                    payment = Payment.objects.get(gateway_transaction_id=payment_intent_id)
                    payment.status = 'completed'
                    payment.processed_at = timezone.now()
                    payment.save()
                    webhook.payment = payment
                except Payment.DoesNotExist:
                    logger.warning(f"Payment not found for Stripe intent: {payment_intent_id}")
            
            elif event_type == 'payment_intent.payment_failed':
                # Update payment status
                payment_intent_id = payload['data']['object']['id']
                try:
                    payment = Payment.objects.get(gateway_transaction_id=payment_intent_id)
                    payment.status = 'failed'
                    payment.save()
                    webhook.payment = payment
                except Payment.DoesNotExist:
                    logger.warning(f"Payment not found for Stripe intent: {payment_intent_id}")
            
            return {'success': True}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_paypal_webhook(self, webhook):
        """Process PayPal webhook"""
        try:
            event_type = webhook.event_type
            payload = webhook.payload
            
            if event_type == 'PAYMENT.CAPTURE.COMPLETED':
                # Update payment status
                resource = payload.get('resource', {})
                custom_id = resource.get('custom_id')
                
                if custom_id:
                    try:
                        payment = Payment.objects.get(id=custom_id)
                        payment.status = 'completed'
                        payment.processed_at = timezone.now()
                        payment.save()
                        webhook.payment = payment
                    except Payment.DoesNotExist:
                        logger.warning(f"Payment not found for PayPal custom_id: {custom_id}")
            
            return {'success': True}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}


class DisputeProcessor:
    """Service for processing payment disputes"""
    
    def submit_evidence(self, dispute, evidence):
        """Submit evidence for a dispute"""
        try:
            if dispute.payment.gateway.gateway_type == 'stripe':
                return self._submit_stripe_evidence(dispute, evidence)
            else:
                return {
                    'success': False,
                    'error': f'Dispute evidence not supported for {dispute.payment.gateway.gateway_type}'
                }
        
        except Exception as e:
            logger.error(f"Evidence submission failed for dispute {dispute.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _submit_stripe_evidence(self, dispute, evidence):
        """Submit evidence to Stripe"""
        try:
            import stripe
            stripe.api_key = dispute.payment.gateway.secret_key
            
            stripe.Dispute.modify(
                dispute.gateway_dispute_id,
                evidence=evidence
            )
            
            return {'success': True}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}