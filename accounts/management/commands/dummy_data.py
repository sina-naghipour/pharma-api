from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
import random, uuid, decimal

# Import your models
from accounts.models import User, UserProfile, UserAddress, PharmacyLicense
from products.models import Category, Manufacturer, Product, ProductVariant, Batch, ProductTag
from orders.models import Cart, CartItem, Order, OrderItem
from promotions.models import Coupon, Promotion, PromotionProduct
from reviews.models import Review
from support.models import SupportTicket, SupportCategory
from support.models import FAQ, KnowledgeBaseCategory, KnowledgeBaseArticle, ContactMessage
from payments.models import PaymentMethod, Payment, PaymentGateway

fake = Faker()

DUMMY_TAG = "DUMMY_DATA"  # Marker so we can safely delete later

class Command(BaseCommand):
    help = "Manage dummy data: create or delete"

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["create", "delete"], help="Action to perform")

    def handle(self, *args, **options):
        action = options["action"]

        if action == "create":
            self.stdout.write(self.style.SUCCESS("Creating dummy data..."))
            self.create_dummy()
        elif action == "delete":
            self.stdout.write(self.style.WARNING("Deleting dummy data..."))
            self.delete_dummy()

    def create_dummy(self):
        # USERS
        users = []
        for _ in range(5):
            first_name = fake.first_name()
            last_name=fake.last_name()
            user = User.objects.create_user(
                email=f"dummy_{uuid.uuid4().hex[:6]}@example.com",
                first_name=fake.first_name(),
                username=first_name + last_name,
                last_name=fake.last_name(),
                user_type=random.choice(["customer", "pharmacy", "doctor"]),
                password="password123",
                is_active=True
            )
            users.append(user)
            UserProfile.objects.create(user=user, bio="Test profile", medical_conditions=f"{DUMMY_TAG}")
            UserAddress.objects.create(user=user, address_type="shipping", first_name=user.first_name,
                                       last_name=user.last_name, address_line_1=fake.street_address(),
                                       city=fake.city(), state_province=fake.state(), postal_code="12345",
                                       country="USA", is_default=True)

        # CATEGORIES & MANUFACTURERS
        cats = [Category.objects.create(name=f"{DUMMY_TAG} Cat {i}", slug=f"dummy-cat-{i}") for i in range(3)]
        mans = [Manufacturer.objects.create(name=f"{DUMMY_TAG} Man {i}", slug=f"dummy-man-{i}") for i in range(2)]

        # PRODUCTS
        products = []
        for i in range(5):
            p = Product.objects.create(
                name=f"{DUMMY_TAG} Product {i}",
                slug=f"dummy-product-{i}",
                product_type="medication",
                sku=f"DUMSKU{i}",
                manufacturer=random.choice(mans),
                price=decimal.Decimal(random.randint(10, 200)),
                stock_quantity=random.randint(10, 50),
                track_inventory=True
            )
            p.categories.set(random.sample(cats, 1))
            products.append(p)
            ProductVariant.objects.create(product=p, name="Default Variant", sku=f"DUMVAR{i}", price_adjustment=0)

        # COUPONS & PROMOTIONS
        for i in range(3):
            Coupon.objects.create(
                code=f"DUMMYCOUPON{i}",
                discount_type="percentage",
                discount_value=decimal.Decimal("10.00"),
                valid_from=timezone.now(),
                is_active=True
            )

        promo = Promotion.objects.create(
            name=f"{DUMMY_TAG} Sale", promotion_type="sale", discount_percentage=10,
            start_date=timezone.now(), is_active=True
        )
        for p in products[:2]:
            PromotionProduct.objects.create(promotion=promo, product=p, discount_percentage=5)

        # ORDERS
        for u in users:
            order = Order.objects.create(
                order_number=f"DUMMYORD{uuid.uuid4().hex[:5]}",
                user=u,
                subtotal=100,
                total_amount=120,
                shipping_address={"dummy": True},
                billing_address={"dummy": True}
            )
            OrderItem.objects.create(order=order, product=random.choice(products), quantity=2,
                                     unit_price=50, subtotal=100, total_price=100, sku="DUMSKU1",
                                     product_name="Dummy Product")

        # REVIEWS
        for p in products:
            Review.objects.create(product=p, user=random.choice(users), rating=5, title="Great Product",
                                  content=f"Test Review {DUMMY_TAG}", status="approved")

        # SUPPORT CATEGORIES & TICKETS
        sc = SupportCategory.objects.create(name=f"{DUMMY_TAG} Support", description="Dummy")
        for u in users:
            SupportTicket.objects.create(user=u, category=sc, subject="Dummy Issue", description="Testing only")

        # FAQ & Knowledge Base
        faq = FAQ.objects.create(category=sc, question="What is dummy?", answer="This is test.", is_published=True)
        kb_cat = KnowledgeBaseCategory.objects.create(name=f"{DUMMY_TAG} KB", slug=f"dummy-kb")
        KnowledgeBaseArticle.objects.create(title="Dummy Guide", slug="dummy-guide", category=kb_cat, content="Test content.")

        # PAYMENTS
        pm = PaymentMethod.objects.create(name=f"{DUMMY_TAG} Card", payment_type="credit_card")
        PaymentGateway.objects.create(name=f"{DUMMY_TAG} Stripe", gateway_type="stripe")
        Payment.objects.create(user=random.choice(users), order=random.choice(Order.objects.all()),
                               payment_method=pm, amount=100, net_amount=90, currency="USD")

        self.stdout.write(self.style.SUCCESS("Dummy data created."))

    def delete_dummy(self):
        """Delete only dummy-tagged data"""
        # Order of deletion matters due to FKs
        Review.objects.filter(content__icontains=DUMMY_TAG).delete()
        Order.objects.filter(order_number__startswith="DUMMYORD").delete()
        Product.objects.filter(name__startswith=DUMMY_TAG).delete()
        Category.objects.filter(name__startswith=DUMMY_TAG).delete()
        Manufacturer.objects.filter(name__startswith=DUMMY_TAG).delete()
        Promotion.objects.filter(name__startswith=DUMMY_TAG).delete()
        Coupon.objects.filter(code__startswith="DUMMYCOUPON").delete()
        SupportCategory.objects.filter(name__startswith=DUMMY_TAG).delete()
        FAQ.objects.filter(question__icontains="dummy").delete()
        KnowledgeBaseCategory.objects.filter(name__startswith=DUMMY_TAG).delete()
        PaymentMethod.objects.filter(name__startswith=DUMMY_TAG).delete()
        PaymentGateway.objects.filter(name__startswith=DUMMY_TAG).delete()
        User.objects.filter(email__startswith="dummy_").delete()

        self.stdout.write(self.style.SUCCESS("Dummy data deleted."))