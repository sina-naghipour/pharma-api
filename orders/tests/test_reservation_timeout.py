from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management import call_command
from io import StringIO

from orders.models import Order, OrderItem
from products.models import Product, Manufacturer

User = get_user_model()

class ReservationTimeoutTest(TestCase):
    def setUp(self):
        # Create a manufacturer
        self.manufacturer = Manufacturer.objects.create(
            name='Test Manufacturer',
            slug='test-manufacturer',
            is_approved=True
        )
        
        # Create a user (email optional)
        self.user = User.objects.create_user(
            username='testuser',
            phone_number='09123456789',
            password='pass'
        )
        
        # Create a product
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            sku='TEST001',
            manufacturer=self.manufacturer,
            price=100,
            track_inventory=True,
            stock_quantity=10,
            is_active=True
        )

    def test_expired_order_cancelled_and_stock_restored(self):
        # Create order with required fields
        order = Order.objects.create(
            user=self.user,
            status='pending',
            subtotal=self.product.price,
            total_amount=self.product.price,
            shipping_address={'city': 'Test'},
            billing_address={'city': 'Test'}
        )
        # Add order item
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            sku=self.product.sku,
            quantity=1,
            unit_price=self.product.price,
            subtotal=self.product.price,
            total_price=self.product.price
        )
        # Simulate stock deduction
        self.product.stock_quantity = 9
        self.product.save()

        # Age the order
        order.created_at = timezone.now() - timedelta(minutes=20)
        order.save(update_fields=['created_at'])

        # Run the management command
        out = StringIO()
        call_command('release_expired_orders', stdout=out)

        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(order.status, 'cancelled')
        self.assertIsNotNone(order.cancelled_at)
        self.assertIn('Reservation timeout', order.staff_notes)
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertIn(f"Cancelled order {order.order_number}", out.getvalue())

    def test_non_expired_order_not_cancelled(self):
        order = Order.objects.create(
            user=self.user,
            status='pending',
            subtotal=self.product.price,
            total_amount=self.product.price,
            shipping_address={},
            billing_address={}
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            sku=self.product.sku,
            quantity=1,
            unit_price=self.product.price,
            subtotal=self.product.price,
            total_price=self.product.price
        )
        self.product.stock_quantity = 9
        self.product.save()

        call_command('release_expired_orders')
        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(order.status, 'pending')
        self.assertEqual(self.product.stock_quantity, 9)