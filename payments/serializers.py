# payments/serializers.py
from rest_framework import serializers
from .models import (
    PaymentMethod, PaymentGateway, Payment, PaymentRefund, 
    SavedPaymentMethod, PaymentWebhook, PaymentDispute
)
from decimal import Decimal

class PaymentMethodSerializer(serializers.ModelSerializer):
    processing_fee_display = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'payment_type', 'description', 'is_active',
            'processing_fee', 'processing_fee_percentage', 'min_amount', 
            'max_amount', 'processing_fee_display', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_processing_fee_display(self, obj):
        """Get human-readable processing fee"""
        if obj.processing_fee > 0 and obj.processing_fee_percentage > 0:
            return f"${obj.processing_fee} + {obj.processing_fee_percentage}%"
        elif obj.processing_fee > 0:
            return f"${obj.processing_fee}"
        elif obj.processing_fee_percentage > 0:
            return f"{obj.processing_fee_percentage}%"
        return "Free"


class PaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGateway
        fields = [
            'id', 'name', 'gateway_type', 'is_active', 'is_test_mode',
            'supported_currencies', 'created_at'
        ]
        read_only_fields = ['created_at']



class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments"""
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    method = serializers.CharField(source='payment_method.name', read_only=True)
    transaction_id = serializers.CharField(source='transaction.reference', read_only=True)

    def get_transaction_id(self, obj):
        # Adjust based on your business logic
        return getattr(obj, 'gateway_transaction_id', None)

    def get_method(self, obj):
        return obj.payment_method.name if obj.payment_method else None
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'amount', 'method', 'method_display',
            'status', 'status_display', 'transaction_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields

class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'order', 'payment_method', 'amount', 'currency', 'billing_address',
            'payment_details'
        ]
    
    def create(self, validated_data):
        # Set user from request context
        validated_data['user'] = self.context['request'].user
        
        # Calculate processing fee
        payment_method = validated_data['payment_method']
        amount = validated_data['amount']
        processing_fee = payment_method.calculate_processing_fee(amount)
        validated_data['processing_fee'] = processing_fee
        
        return super().create(validated_data)
    
    def validate_amount(self, value):
        """Validate payment amount"""
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0")
        return value
    
    def validate(self, data):
        """Validate payment data"""
        payment_method = data.get('payment_method')
        amount = data.get('amount')
        
        if payment_method and amount:
            # Check minimum amount
            if amount < payment_method.min_amount:
                raise serializers.ValidationError(
                    f"Amount must be at least {payment_method.min_amount}"
                )
            
            # Check maximum amount
            if payment_method.max_amount and amount > payment_method.max_amount:
                raise serializers.ValidationError(
                    f"Amount cannot exceed {payment_method.max_amount}"
                )
        
        return data


class PaymentRefundSerializer(serializers.ModelSerializer):
    payment_id = serializers.CharField(source='payment.id', read_only=True)
    initiated_by_email = serializers.CharField(source='initiated_by.email', read_only=True)
    
    class Meta:
        model = PaymentRefund
        fields = [
            'id', 'payment', 'payment_id', 'initiated_by', 'initiated_by_email',
            'amount', 'reason', 'notes', 'status', 'gateway_refund_id',
            'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'payment_id', 'initiated_by_email', 'gateway_refund_id',
            'created_at', 'updated_at', 'processed_at'
        ]


class PaymentRefundCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRefund
        fields = ['payment', 'amount', 'reason', 'notes']
    
    def create(self, validated_data):
        validated_data['initiated_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate(self, data):
        """Validate refund data"""
        payment = data.get('payment')
        amount = data.get('amount')
        
        if payment and amount:
            # Check if payment is refundable
            if payment.status not in ['completed']:
                raise serializers.ValidationError("Only completed payments can be refunded")
            
            # Check refund amount
            total_refunded = sum(
                refund.amount for refund in payment.refunds.filter(status='completed')
            )
            available_amount = payment.amount - total_refunded
            
            if amount > available_amount:
                raise serializers.ValidationError(
                    f"Refund amount cannot exceed available amount: {available_amount}"
                )
        
        return data


class SavedPaymentMethodSerializer(serializers.ModelSerializer):
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SavedPaymentMethod
        fields = [
            'id', 'payment_method', 'payment_method_name', 'card_type',
            'last_four_digits', 'expiry_month', 'expiry_year', 'cardholder_name',
            'account_identifier', 'is_default', 'is_verified', 'display_name',
            'created_at'
        ]
        read_only_fields = [
            'id', 'payment_method_name', 'display_name', 'is_verified', 'created_at'
        ]
    
    def get_display_name(self, obj):
        """Get display name for saved payment method"""
        return str(obj)


class PaymentWebhookSerializer(serializers.ModelSerializer):
    gateway_name = serializers.CharField(source='gateway.name', read_only=True)
    
    class Meta:
        model = PaymentWebhook
        fields = [
            'id', 'gateway', 'gateway_name', 'webhook_id', 'event_type',
            'status', 'payment', 'processed_at', 'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'gateway_name', 'created_at']


class PaymentDisputeSerializer(serializers.ModelSerializer):
    payment_id = serializers.CharField(source='payment.id', read_only=True)
    
    class Meta:
        model = PaymentDispute
        fields = [
            'id', 'payment', 'payment_id', 'gateway_dispute_id', 'amount',
            'currency', 'reason', 'status', 'evidence_due_by', 'created_at'
        ]
        read_only_fields = ['id', 'payment_id', 'created_at']