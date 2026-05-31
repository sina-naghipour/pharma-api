from django.core.management.base import BaseCommand
from django.utils import timezone
from orders.models import Order

class Command(BaseCommand):
    help = 'Release inventory for unpaid orders older than 15 minutes'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timezone.timedelta(minutes=15)
        expired_orders = Order.objects.filter(
            status=Order.STATUS_PENDING,
            created_at__lte=cutoff,
            paid_at__isnull=True
        )
        count = 0
        for order in expired_orders:
            try:
                order.cancel(reason="Reservation timeout - no payment within 15 minutes")
                self.stdout.write(self.style.SUCCESS(f"Cancelled order {order.order_number}"))
                count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to cancel {order.order_number}: {e}"))
        self.stdout.write(self.style.SUCCESS(f"Total cancelled: {count}"))