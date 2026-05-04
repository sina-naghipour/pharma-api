# reviews/tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from reviews.models import Review, ReviewImage
from products.models import Product, Category
from decimal import Decimal

User = get_user_model()

class ReviewViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123',
            first_name='Test',
            last_name='Customer'
        )
        
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='password123'
        )
        
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpassword123'
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
        
        # URLs
        self.list_url = reverse('reviews:review-list')
        self.detail_url = reverse('reviews:review-detail', args=[self.review.id])
        self.product_reviews_url = reverse('reviews:product-reviews', args=[self.product.id])
        self.helpful_url = reverse('reviews:review-mark-helpful', args=[self.review.id])
    
    def test_get_reviews(self):
        """Test retrieving a list of reviews"""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], self.review.title)
        
    def test_get_review_detail(self):
        """Test retrieving a review detail"""
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.review.title)
        self.assertEqual(response.data['rating'], self.review.rating)
        
    def test_get_product_reviews(self):
        """Test retrieving reviews for a specific product"""
        response = self.client.get(self.product_reviews_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['product'], self.product.id)
        
    def test_create_review_unauthenticated(self):
        """Test that unauthenticated users cannot create reviews"""
        review_data = {
            'product': self.product.id,
            'rating': 5,
            'title': 'Excellent product',
            'comment': 'This product exceeded my expectations.'
        }
        
        response = self.client.post(self.list_url, review_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Review.objects.count(), 1)
        
    def test_create_review_authenticated(self):
        """Test that authenticated users can create reviews"""
        self.client.force_authenticate(user=self.other_user)
        
        review_data = {
            'product': self.product.id,
            'rating': 5,
            'title': 'Excellent product',
            'comment': 'This product exceeded my expectations.'
        }
        
        response = self.client.post(self.list_url, review_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 2)
        self.assertEqual(Review.objects.filter(user=self.other_user).count(), 1)
        
    def test_update_own_review(self):
        """Test that users can update their own reviews"""
        self.client.force_authenticate(user=self.user)
        
        update_data = {'rating': 5, 'title': 'Updated title'}
        response = self.client.patch(self.detail_url, update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 5)
        self.assertEqual(self.review.title, 'Updated title')
        
    def test_update_others_review_forbidden(self):
        """Test that users cannot update others' reviews"""
        self.client.force_authenticate(user=self.other_user)
        
        update_data = {'rating': 2, 'title': 'Should not update'}
        response = self.client.patch(self.detail_url, update_data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)  # Unchanged
        self.assertEqual(self.review.title, "Good product")  # Unchanged
        
    def test_admin_can_update_any_review(self):
        """Test that admins can update any review"""
        self.client.force_authenticate(user=self.admin_user)
        
        update_data = {'is_approved': False}
        response = self.client.patch(self.detail_url, update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertFalse(self.review.is_approved)
        
    def test_delete_own_review(self):
        """Test that users can delete their own reviews"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Review.objects.count(), 0)
        
    def test_delete_others_review_forbidden(self):
        """Test that users cannot delete others' reviews"""
        self.client.force_authenticate(user=self.other_user)
        
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Review.objects.count(), 1)
        
    def test_mark_review_helpful(self):
        """Test marking a review as helpful"""
        self.client.force_authenticate(user=self.other_user)
        
        response = self.client.post(self.helpful_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.review.refresh_from_db()
        self.assertEqual(self.review.helpful_count, 1)
        
        # Test marking again doesn't increase count
        response = self.client.post(self.helpful_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.review.refresh_from_db()
        self.assertEqual(self.review.helpful_count, 1)