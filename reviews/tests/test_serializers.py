# reviews/tests/test_serializers.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from reviews.models import Review, ReviewImage
from reviews.serializers import ReviewSerializer, ReviewCreateSerializer, ReviewImageSerializer
from products.models import Product, Category
from decimal import Decimal

User = get_user_model()

class ReviewSerializerTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123',
            first_name='Test',
            last_name='Customer'
        )
        
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
        
        # Create review
        self.review = Review.objects.create(
            product=self.product,
            user=self.user,
            rating=4,
            title="Good product",
            comment="This is a good product, I recommend it.",
            is_verified_purchase=True
        )
        
        # Create review image
        self.review_image = ReviewImage.objects.create(
            review=self.review,
            image='reviews/test-image.jpg',
            caption='Product in use'
        )
        
        self.serializer = ReviewSerializer(instance=self.review)
    
    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields"""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'product', 'user', 'rating', 'title', 'comment', 
             'is_verified_purchase', 'is_approved', 'images', 
             'helpful_count', 'created_at', 'updated_at', 'user_name']
        )
        
    def test_user_name_field(self):
        """Test that user_name field is correctly populated"""
        data = self.serializer.data
        expected_name = f"{self.user.first_name} {self.user.last_name}"
        self.assertEqual(data['user_name'], expected_name)
        
    def test_images_included(self):
        """Test that images are included in serializer"""
        data = self.serializer.data
        self.assertEqual(len(data['images']), 1)
        self.assertEqual(data['images'][0]['caption'], 'Product in use')


class ReviewCreateSerializerTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
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
        
        # Review data for serializer
        self.review_data = {
            'product': self.product.id,
            'rating': 5,
            'title': 'Excellent product',
            'comment': 'This product exceeded my expectations.'
        }
        
        self.serializer = ReviewCreateSerializer(
            data=self.review_data,
            context={'request': type('obj', (object,), {'user': self.user})}
        )
    
    def test_validate_success(self):
        """Test successful validation"""
        self.assertTrue(self.serializer.is_valid())
        
    def test_create_review(self):
        """Test creating a review with the serializer"""
        self.assertTrue(self.serializer.is_valid())
        review = self.serializer.save()
        
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.title, 'Excellent product')
        self.assertEqual(review.comment, 'This product exceeded my expectations.')
        self.assertFalse(review.is_verified_purchase)  # Default unless specified
        
    def test_invalid_rating(self):
        """Test validation fails with invalid rating"""
        self.review_data['rating'] = 6  # Invalid rating
        serializer = ReviewCreateSerializer(
            data=self.review_data,
            context={'request': type('obj', (object,), {'user': self.user})}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('rating', serializer.errors)


class ReviewImageSerializerTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
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
        
        # Create review
        self.review = Review.objects.create(
            product=self.product,
            user=self.user,
            rating=4,
            title="Good product",
            comment="This is a good product, I recommend it."
        )
        
        # Create review image
        self.review_image = ReviewImage.objects.create(
            review=self.review,
            image='reviews/test-image.jpg',
            caption='Product in use'
        )
        
        self.serializer = ReviewImageSerializer(instance=self.review_image)
    
    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields"""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'review', 'image', 'caption', 'created_at']
        )
        
    def test_field_content(self):
        """Test field content"""
        data = self.serializer.data
        self.assertEqual(data['review'], self.review.id)
        self.assertEqual(data['caption'], 'Product in use')