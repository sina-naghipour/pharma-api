import logging
from celery import shared_task
from django.utils import timezone
from .models import Order

logger = logging.getLogger(__name__)

@shared_task
def release_expired_reservations():
    """
    Release stock for unpaid orders older than 15 minutes.
    Called automatically every 5 minutes.
    """
    cutoff = timezone.now() - timezone.timedelta(minutes=15)
    expired_orders = Order.objects.filter(
        status=Order.STATUS_PENDING,
        created_at__lte=cutoff,
        paid_at__isnull=True
    )
    cancelled_count = 0
    for order in expired_orders:
        try:
            order.cancel(reason="Reservation timeout - no payment within 15 minutes")
            cancelled_count += 1
            logger.info(f"Auto-cancelled order {order.order_number} due to timeout")
        except Exception as e:
            logger.error(f"Failed to auto-cancel order {order.order_number}: {e}")
    return f"Cancelled {cancelled_count} expired orders"