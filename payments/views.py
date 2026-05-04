# payments/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import (
    PaymentMethod, PaymentGateway, Payment, PaymentRefund,
    SavedPaymentMethod, PaymentWebhook, PaymentDispute
)
from .serializers import (
    PaymentMethodSerializer, PaymentGatewaySerializer, PaymentSerializer,
    PaymentCreateSerializer, PaymentRefundSerializer, PaymentRefundCreateSerializer,
    SavedPaymentMethodSerializer, PaymentWebhookSerializer, PaymentDisputeSerializer
)
from .services import PaymentProcessor
from .permissions import IsOwnerOrAdmin, IsAdminOrReadOnly

class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for payment methods
    """
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.AllowAny]
    
    @action(detail=True, methods=['post'])
    def calculate_fee(self, request, pk=None):
        """Calculate processing fee for given amount"""
        payment_method = self.get_object()
        amount = request.data.get('amount', 0)
        
        try:
            amount = float(amount)
            fee = payment_method.calculate_processing_fee(amount)
            return Response({
                'amount': amount,
                'processing_fee': fee,
                'total': amount + fee
            })
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid amount'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentGatewayViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for payment gateways
    """
    queryset = PaymentGateway.objects.filter(is_active=True)
    serializer_class = PaymentGatewaySerializer
    permission_classes = [IsAdminOrReadOnly]


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for payments
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new payment"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create payment
        payment = serializer.save()
        
        # Process payment
        processor = PaymentProcessor()
        try:
            result = processor.process_payment(payment)
            if result['success']:
                payment.status = 'completed'
                payment.gateway_transaction_id = result.get('transaction_id')
                payment.gateway_response = result.get('gateway_response', {})
                payment.processed_at = timezone.now()
            else:
                payment.status = 'failed'
                payment.gateway_response = result.get('error_details', {})
            
            payment.save()
            
            return Response(
                PaymentSerializer(payment).data,
                status=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            payment.status = 'failed'
            payment.gateway_response = {'error': str(e)}
            payment.save()
            
            return Response(
                {'error': 'Payment processing failed', 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def refund(self, request, pk=None):
        """Initiate a refund for a payment"""
        payment = self.get_object()
        
        serializer = PaymentRefundCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Create refund
        refund = serializer.save(payment=payment)
        
        # Process refund
        processor = PaymentProcessor()
        try:
            result = processor.process_refund(refund)
            if result['success']:
                refund.status = 'completed'
                refund.gateway_refund_id = result.get('refund_id')
                refund.processed_at = timezone.now()
            else:
                refund.status = 'failed'
            
            refund.gateway_response = result.get('gateway_response', {})
            refund.save()
            
            return Response(PaymentRefundSerializer(refund).data)
        
        except Exception as e:
            refund.status = 'failed'
            refund.gateway_response = {'error': str(e)}
            refund.save()
            
            return Response(
                {'error': 'Refund processing failed', 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def my_payments(self, request):
        """Get current user's payments"""
        payments = Payment.objects.filter(user=request.user)
        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)


class PaymentRefundViewSet(viewsets.ModelViewSet):
    """
    ViewSet for payment refunds
    """
    serializer_class = PaymentRefundSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return PaymentRefund.objects.all()
        return PaymentRefund.objects.filter(payment__user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentRefundCreateSerializer
        return PaymentRefundSerializer


class SavedPaymentMethodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for saved payment methods
    """
    serializer_class = SavedPaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return SavedPaymentMethod.objects.all()
        return SavedPaymentMethod.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set payment method as default"""
        saved_method = self.get_object()
        
        # Unset other default methods
        SavedPaymentMethod.objects.filter(
            user=saved_method.user,
            payment_method=saved_method.payment_method
        ).update(is_default=False)
        
        # Set this as default
        saved_method.is_default = True
        saved_method.save()
        
        return Response({'status': 'default set'})


class PaymentWebhookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for payment webhooks (admin only)
    """
    queryset = PaymentWebhook.objects.all()
    serializer_class = PaymentWebhookSerializer
    permission_classes = [permissions.IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Reprocess a webhook"""
        webhook = self.get_object()
        
        # Import webhook processor
        from .services import WebhookProcessor
        
        processor = WebhookProcessor()
        try:
            result = processor.process_webhook(webhook)
            webhook.status = 'processed' if result['success'] else 'failed'
            webhook.processed_at = timezone.now()
            webhook.error_message = result.get('error', '')
            webhook.save()
            
            return Response({'status': 'reprocessed', 'success': result['success']})
        
        except Exception as e:
            webhook.status = 'failed'
            webhook.error_message = str(e)
            webhook.save()
            
            return Response(
                {'error': 'Webhook reprocessing failed', 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentDisputeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for payment disputes (admin only)
    """
    queryset = PaymentDispute.objects.all()
    serializer_class = PaymentDisputeSerializer
    permission_classes = [permissions.IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def submit_evidence(self, request, pk=None):
        """Submit evidence for a dispute"""
        dispute = self.get_object()
        evidence = request.data.get('evidence', {})
        
        # Import dispute processor
        from .services import DisputeProcessor
        
        processor = DisputeProcessor()
        try:
            result = processor.submit_evidence(dispute, evidence)
            dispute.evidence_details = evidence
            dispute.save()
            
            return Response({'status': 'evidence submitted', 'success': result['success']})
        
        except Exception as e:
            return Response(
                {'error': 'Evidence submission failed', 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )