from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Order, Refund, Shipment
from payments.models import Payment

@receiver(post_save, sender=Order)
def order_status_changed(sender, instance, created, **kwargs):
    """Send notifications when order status changes"""
    if not created and instance.user.email:
        if instance.status == Order.STATUS_PAID and instance.paid_at:
            try:
                subject = 'Your payment has been confirmed'
                message = f'Thank you for your order. Your payment of {instance.total_amount} has been confirmed.'
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")
        
        elif instance.status == Order.STATUS_SHIPPED and instance.shipped_at:
            try:
                subject = 'Your order has been shipped'
                message = f'Your order {instance.order_number} has been shipped. Tracking number: {instance.tracking_number}'
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")
        
        elif instance.status == Order.STATUS_DELIVERED and instance.delivered_at:
            try:
                subject = 'Your order has been delivered'
                message = f'Your order {instance.order_number} has been delivered. Thank you for shopping with us!'
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")
        
        elif instance.status == Order.STATUS_CANCELLED and instance.cancelled_at:
            try:
                subject = 'Your order has been cancelled'
                message = f'Your order {instance.order_number} has been cancelled.'
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")

@receiver(post_save, sender=Order)
def prescription_verified_email(sender, instance, created, **kwargs):
    """Send email when prescription is verified (only when changed from False to True)"""
    if not created and instance.user.email and instance.prescription_verified:
        # Check if this is an update (not a new order) and prescription_verified changed
        try:
            old = Order.objects.get(pk=instance.pk)
            if not old.prescription_verified and instance.prescription_verified:
                send_mail(
                    'تأیید نسخه پزشکی',
                    f'نسخه پزشکی سفارش {instance.order_number} تأیید شد. سفارش شما در حال پردازش است.',
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.user.email],
                    fail_silently=True,
                )
        except Order.DoesNotExist:
            pass  # New order, no email

@receiver(post_save, sender=Payment)
def payment_status_changed(sender, instance, created, **kwargs):
    """Handle payment status changes"""
    if not created and instance.status == Payment.STATUS_COMPLETED:
        order = instance.order
        if order.status in [Order.STATUS_PENDING, Order.STATUS_PAYMENT_PROCESSING]:
            order.status = Order.STATUS_PAID
            order.paid_at = instance.updated_at
            order.payment_id = instance.transaction_id
            order.save(update_fields=['status', 'paid_at', 'payment_id', 'updated_at'])

@receiver(post_save, sender=Refund)
def refund_status_changed(sender, instance, created, **kwargs):
    """Handle refund status changes"""
    if not created and instance.status == Refund.STATUS_COMPLETED:
        if instance.order.user.email:
            try:
                subject = 'Your refund has been processed'
                message = f'Your refund of {instance.amount} for order {instance.order.order_number} has been processed.'
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.order.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")

@receiver(post_save, sender=Shipment)
def shipment_status_changed(sender, instance, created, **kwargs):
    """Handle shipment status changes"""
    if not created:
        order = instance.order
        
        if instance.status == Shipment.STATUS_SHIPPED and not order.shipped_at:
            order.status = Order.STATUS_SHIPPED
            order.shipped_at = instance.shipped_at
            order.tracking_number = instance.tracking_number
            order.shipping_carrier = instance.carrier
            order.save(update_fields=[
                'status', 'shipped_at', 'tracking_number',
                'shipping_carrier', 'updated_at'
            ])
        
        elif instance.status == Shipment.STATUS_DELIVERED and not order.delivered_at:
            order.status = Order.STATUS_DELIVERED
            order.delivered_at = instance.delivered_at
            order.save(update_fields=['status', 'delivered_at', 'updated_at'])