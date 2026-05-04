# promotions/tests/test_models.py
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from promotions.models import Coupon, Discount, Campaign
from products.models import Product, Category
from datetime import timedelta
from decimal import Decimal

User = get_user_model()

class CouponModelTest(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.valid_from = self.now
        self.valid_to = self.now + timedelta(days=30)
        
        self.coupon = Coupon.objects.create(
            code='TESTCODE',
            discount_type='percentage',
            discount_value=20,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            max_uses=100,
            current_uses=0,
            min_purchase_amount=Decimal('50.00'),
            is_active=True
        )
    
    def test_coupon_creation(self):
        """Test creating a coupon"""
        self.assertEqual(self.coupon.code, 'TESTCODE')
        self.assertEqual(self.coupon.discount_type, 'percentage')
        self.assertEqual(self.coupon.discount_value, 20)
        self.assertEqual(self.coupon.max_uses, 100)
        self.assertEqual(self.coupon.current_uses, 0)
        self.assertEqual(self.coupon.min_purchase_amount, Decimal('50.00'))
        self.assertTrue(self.coupon.is_active)
    
    def test_coupon_str(self):
        """Test the string representation of a coupon"""
        self.assertEqual(str(self.coupon), 'TESTCODE')
    
    def test_is_valid(self):
        """Test coupon validity"""
        # Valid coupon
        self.assertTrue(self.coupon.is_valid())
        
        # Inactive coupon
        self.coupon.is_active = False
        self.coupon.save()
        self.assertFalse(self.coupon.is_valid())
        
        # Reset for next test
        self.coupon.is_active = True
        self.coupon.save()
        
        # Expired coupon
        self.coupon.valid_to = self.now - timedelta(days=1)
        self.coupon.save()
        self.assertFalse(self.coupon.is_valid())
        
        # Reset for next test
        self.coupon.valid_to = self.valid_to
        self.coupon.save()
        
        # Max uses reached
        self.coupon.current_uses = self.coupon.max_uses
        self.coupon.save()
        self.assertFalse(self.coupon.is_valid())
    
    def test_calculate_discount_percentage(self):
        """Test calculating percentage discount"""
        order_total = Decimal('100.00')
        expected_discount = Decimal('20.00')  # 20% of 100
        self.assertEqual(self.coupon.calculate_discount(order_total), expected_discount)
    
    def test_calculate_discount_fixed(self):
        """Test calculating fixed discount"""
        self.coupon.discount_type = 'fixed'
        self.coupon.discount_value = 15
        self.coupon.save()
        
        order_total = Decimal('100.00')
        expected_discount = Decimal('15.00')
        self.assertEqual(self.coupon.calculate_discount(order_total), expected_discount)
    
    def test_min_purchase_amount(self):
        """Test minimum purchase amount validation"""
        # Below minimum
        order_total = Decimal('40.00')
        self.assertEqual(self.coupon.calculate_discount(order_total), Decimal('0.00'))
        
        # Above minimum
        order_total = Decimal('60.00')
        expected_discount = Decimal('12.00')  # 20% of 60
        self.assertEqual(self.coupon.calculate_discount(order_total), expected_discount)


class DiscountModelTest(TestCase):
    def setUp(self):
        # Create category and product
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            price=Decimal('100.00'),
            category=self.category
        )
        
        self.now = timezone.now()
        self.valid_from = self.now
        self.valid_to = self.now + timedelta(days=30)
        
        self.discount = Discount.objects.create(
            name='Test Discount',
            discount_type='percentage',
            discount_value=25,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            is_active=True
        )
        self.discount.products.add(self.product)
    
    def test_discount_creation(self):
        """Test creating a discount"""
        self.assertEqual(self.discount.name, 'Test Discount')
        self.assertEqual(self.discount.discount_type, 'percentage')
        self.assertEqual(self.discount.discount_value, 25)
        self.assertTrue(self.discount.is_active)
        self.assertEqual(self.discount.products.count(), 1)
        self.assertEqual(self.discount.products.first(), self.product)
    
    def test_discount_str(self):
        """Test the string representation of a discount"""
        self.assertEqual(str(self.discount), 'Test Discount')
    
    def test_is_valid(self):
        """Test discount validity"""
        # Valid discount
        self.assertTrue(self.discount.is_valid())
        
        # Inactive discount
        self.discount.is_active = False
        self.discount.save()
        self.assertFalse(self.discount.is_valid())
        
        # Reset for next test
        self.discount.is_active = True
        self.discount.save()
        
        # Expired discount
        self.discount.valid_to = self.now - timedelta(days=1)
        self.discount.save()
        self.assertFalse(self.discount.is_valid())
    
    def test_calculate_discount_percentage(self):
        """Test calculating percentage discount"""
        product_price = Decimal('100.00')
        expected_discount = Decimal('25.00')  # 25% of 100
        self.assertEqual(self.discount.calculate_discount(product_price), expected_discount)
    
    def test_calculate_discount_fixed(self):
        """Test calculating fixed discount"""
        self.discount.discount_type = 'fixed'
        self.discount.discount_value = 15
        self.discount.save()
        
        product_price = Decimal('100.00')
        expected_discount = Decimal('15.00')
        self.assertEqual(self.discount.calculate_discount(product_price), expected_discount)


class CampaignModelTest(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.valid_from = self.now
        self.valid_to = self.now + timedelta(days=30)
        
        self.campaign = Campaign.objects.create(
            name='Summer Sale',
            description='Summer sale campaign',
            campaign_type='sale',
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            is_active=True
        )
    
    def test_campaign_creation(self):
        """Test creating a campaign"""
        self.assertEqual(self.campaign.name, 'Summer Sale')
        self.assertEqual(self.campaign.description, 'Summer sale campaign')
        self.assertEqual(self.campaign.campaign_type, 'sale')
        self.assertTrue(self.campaign.is_active)
    
    def test_campaign_str(self):
        """Test the string representation of a campaign"""
        self.assertEqual(str(self.campaign), 'Summer Sale')
    
    def test_is_valid(self):
        """Test campaign validity"""
        # Valid campaign
        self.assertTrue(self.campaign.is_valid())
        
        # Inactive campaign
        self.campaign.is_active = False
        self.campaign.save()
        self.assertFalse(self.campaign.is_valid())
        
        # Reset for next test
        self.campaign.is_active = True
        self.campaign.save()
        
        # Expired campaign
        self.campaign.valid_to = self.now - timedelta(days=1)
        self.campaign.save()
        self.assertFalse(self.campaign.is_valid())