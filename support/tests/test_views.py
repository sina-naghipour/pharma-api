# support/tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from support.models import Ticket, TicketMessage, FAQ, FAQCategory, KnowledgeBase, KnowledgeBaseCategory

User = get_user_model()

class TicketViewSetTest(TestCase):
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
        
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            password='password123',
            is_staff=True
        )
        
        # Create ticket
        self.ticket = Ticket.objects.create(
            user=self.user,
            subject="Order Issue",
            description="I have an issue with my recent order.",
            priority="medium",
            status="open"
        )
        
        # URLs
        self.list_url = reverse('support:ticket-list')
        self.detail_url = reverse('support:ticket-detail', args=[self.ticket.id])
        self.message_url = reverse('support:ticket-messages', args=[self.ticket.id])
    
    def test_get_tickets_unauthenticated(self):
        """Test that unauthenticated users cannot access tickets"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_get_user_tickets(self):
        """Test that user can access their own tickets"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.ticket.id)
        
    def test_staff_can_access_all_tickets(self):
        """Test that staff can access all tickets"""
        # Create another user's ticket
        other_ticket = Ticket.objects.create(
            user=self.other_user,
            subject="Another Issue",
            description="Another issue description.",
            priority="low"
        )
        
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
    def test_user_cannot_access_others_ticket(self):
        """Test that user cannot access another user's ticket details"""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_create_ticket(self):
        """Test creating a new ticket"""
        self.client.force_authenticate(user=self.user)
        
        ticket_data = {
            'subject': 'Payment Issue',
            'description': 'My payment was processed but order not confirmed.',
            'priority': 'high'
        }
        
        response = self.client.post(self.list_url, ticket_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check ticket was created
        self.assertEqual(Ticket.objects.count(), 2)
        new_ticket = Ticket.objects.get(subject='Payment Issue')
        self.assertEqual(new_ticket.user, self.user)
        self.assertEqual(new_ticket.status, 'open')
        
    def test_add_message_to_ticket(self):
        """Test adding a message to a ticket"""
        self.client.force_authenticate(user=self.user)
        
        message_data = {
            'message': 'Any updates on my issue?'
        }
        
        response = self.client.post(self.message_url, message_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check message was created
        self.assertEqual(TicketMessage.objects.count(), 1)
        message = TicketMessage.objects.first()
        self.assertEqual(message.ticket, self.ticket)
        self.assertEqual(message.user, self.user)
        self.assertEqual(message.message, 'Any updates on my issue?')
        self.assertFalse(message.is_staff_response)
        
    def test_staff_response_to_ticket(self):
        """Test staff responding to a ticket"""
        self.client.force_authenticate(user=self.staff_user)
        
        message_data = {
            'message': 'We are looking into your issue.'
        }
        
        response = self.client.post(self.message_url, message_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check message was created with staff flag
        message = TicketMessage.objects.first()
        self.assertEqual(message.user, self.staff_user)
        self.assertTrue(message.is_staff_response)
        
        # Check ticket status was updated
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'in_progress')


class FAQViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpassword123'
        )
        
        # Create FAQ category
        self.category = FAQCategory.objects.create(
            name="Orders",
            slug="orders",
            description="Frequently asked questions about orders."
        )
        
        # Create FAQs
        self.faq1 = FAQ.objects.create(
            category=self.category,
            question="How do I track my order?",
            answer="You can track your order in your account dashboard.",
            is_published=True
        )
        
        self.faq2 = FAQ.objects.create(
            category=self.category,
            question="How do I cancel my order?",
            answer="You can cancel your order from your account dashboard within 24 hours.",
            is_published=True
        )
        
        self.unpublished_faq = FAQ.objects.create(
            category=self.category,
            question="Draft FAQ",
            answer="This is not published yet.",
            is_published=False
        )
        
        # URLs
        self.list_url = reverse('support:faq-list')
        self.detail_url = reverse('support:faq-detail', args=[self.faq1.id])
        self.category_list_url = reverse('support:faq-category-list')
        self.category_detail_url = reverse('support:faq-category-detail', args=[self.category.id])
    
    def test_get_published_faqs(self):
        """Test retrieving published FAQs"""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Only published FAQs
        
    def test_get_faq_detail(self):
        """Test retrieving FAQ detail"""
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question'], self.faq1.question)
        
    def test_unpublished_faq_not_accessible(self):
        """Test that unpublished FAQs are not accessible"""
        unpublished_url = reverse('support:faq-detail', args=[self.unpublished_faq.id])
        response = self.client.get(unpublished_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_create_faq_unauthorized(self):
        """Test that unauthorized users cannot create FAQs"""
        faq_data = {
            'category': self.category.id,
            'question': 'New FAQ Question',
            'answer': 'New FAQ Answer',
            'is_published': True
        }
        
        response = self.client.post(self.list_url, faq_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_create_faq_authorized(self):
        """Test that admin users can create FAQs"""
        self.client.force_authenticate(user=self.admin_user)
        
        faq_data = {
            'category': self.category.id,
            'question': 'New FAQ Question',
            'answer': 'New FAQ Answer',
            'is_published': True
        }
        
        response = self.client.post(self.list_url, faq_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FAQ.objects.count(), 4)
        
    def test_get_faq_categories(self):
        """Test retrieving FAQ categories"""
        response = self.client.get(self.category_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.category.name)


class KnowledgeBaseViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpassword123'
        )
        
        # Create knowledge base category
        self.category = KnowledgeBaseCategory.objects.create(
            name="Getting Started",
            slug="getting-started",
            description="Articles to help you get started."
        )
        
        # Create knowledge base articles
        self.article1 = KnowledgeBase.objects.create(
            category=self.category,
            title="How to Create an Account",
            content="Follow these steps to create an account...",
            slug="how-to-create-account",
            is_published=True
        )
        
        self.article2 = KnowledgeBase.objects.create(
            category=self.category,
            title="How to Reset Password",
            content="Follow these steps to reset your password...",
            slug="how-to-reset-password",
            is_published=True
        )
        
        self.unpublished_article = KnowledgeBase.objects.create(
            category=self.category,
            title="Draft Article",
            content="This is not published yet.",
            slug="draft-article",
            is_published=False
        )
        
        # URLs
        self.list_url = reverse('support:knowledgebase-list')
        self.detail_url = reverse('support:knowledgebase-detail', args=[self.article1.slug])
        self.category_list_url = reverse('support:knowledgebase-category-list')
        self.category_detail_url = reverse('support:knowledgebase-category-detail', args=[self.category.slug])
    
    def test_get_published_articles(self):
        """Test retrieving published knowledge base articles"""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # Only published articles
        
    def test_get_article_detail(self):
        """Test retrieving article detail"""
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.article1.title)
        
    def test_unpublished_article_not_accessible(self):
        """Test that unpublished articles are not accessible"""
        unpublished_url = reverse('support:knowledgebase-detail', args=[self.unpublished_article.slug])
        response = self.client.get(unpublished_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_create_article_unauthorized(self):
        """Test that unauthorized users cannot create articles"""
        article_data = {
            'category': self.category.id,
            'title': 'New Article',
            'content': 'New article content...',
            'slug': 'new-article',
            'is_published': True
        }
        
        response = self.client.post(self.list_url, article_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_create_article_authorized(self):
        """Test that admin users can create articles"""
        self.client.force_authenticate(user=self.admin_user)
        
        article_data = {
            'category': self.category.id,
            'title': 'New Article',
            'content': 'New article content...',
            'slug': 'new-article',
            'is_published': True
        }
        
        response = self.client.post(self.list_url, article_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(KnowledgeBase.objects.count(), 4)
        
    def test_get_kb_categories(self):
        """Test retrieving knowledge base categories"""
        response = self.client.get(self.category_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.category.name)