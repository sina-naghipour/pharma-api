# reviews/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from reviews.models import Review, ReviewImage
from products.models import Product, Category
from django.core.exceptions import ValidationError
from decimal import Decimal

User = get_user_model()

class ReviewModelTest(TestCase):
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
    
    def test_review_creation(self):
        """Test creating a review"""
        self.assertEqual(self.review.product, self.product)
        self.assertEqual(self.review.user, self.user)
        self.assertEqual(self.review.rating, 4)
        self.assertEqual(self.review.title, "Good product")
        self.assertEqual(self.review.comment, "This is a good product, I recommend it.")
        self.assertTrue(self.review.is_verified_purchase)
        self.assertTrue(self.review.is_approved)  # Default value
        
    def test_review_str(self):
        """Test the string representation of a review"""
        expected_str = f"Review for {self.product.name} by {self.user.email}"
        self.assertEqual(str(self.review), expected_str)
        
    def test_review_image_creation(self):
        """Test creating a review image"""
        self.assertEqual(self.review_image.review, self.review)
        self.assertEqual(self.review_image.image, 'reviews/test-image.jpg')
        self.assertEqual(self.review_image.caption, 'Product in use')
        
    def test_review_image_str(self):
        """Test the string representation of a review image"""
        expected_str = f"Image for review #{self.review.id}"
        self.assertEqual(str(self.review_image), expected_str)
        
    def test_review_rating_validation(self):
        """Test that review rating must be between 1 and 5"""
        # Test rating below minimum
        with self.assertRaises(ValidationError):
            invalid_review = Review(
                product=self.product,
                user=self.user,
                rating=0,  # Invalid rating
                title="Invalid rating",
                comment="This should not be allowed."
            )
            invalid_review.full_clean()
            
        # Test rating above maximum
        with self.assertRaises(ValidationError):
            invalid_review = Review(
                product=self.product,
                user=self.user,
                rating=6,  # Invalid rating
                title="Invalid rating",
                comment="This should not be allowed."
            )
            invalid_review.full_clean()
            
    def test_review_uniqueness(self):
        """Test that a user can only leave one review per product"""
        with self.assertRaises(ValidationError):
            duplicate_review = Review(
                product=self.product,
                user=self.user,
                rating=5,
                title="Another review",
                comment="This should not be allowed."
            )
            duplicate_review.full_clean()