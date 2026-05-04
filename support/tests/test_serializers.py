# support/tests/test_serializers.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from support.models import Ticket, TicketMessage, FAQ, FAQCategory, KnowledgeBase, KnowledgeBaseCategory
from support.serializers import (
    TicketSerializer, TicketMessageSerializer, TicketCreateSerializer,
    FAQSerializer, FAQCategorySerializer, KnowledgeBaseSerializer, KnowledgeBaseCategorySerializer
)

User = get_user_model()

class TicketSerializerTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123',
            first_name='Test',
            last_name='Customer'
        )
        
        # Create ticket
        self.ticket = Ticket.objects.create(
            user=self.user,
            subject="Order Issue",
            description="I have an issue with my recent order.",
            priority="medium",
            status="open"
        )
        
        self.serializer = TicketSerializer(instance=self.ticket)
    
    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields"""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'user', 'subject', 'description', 'priority', 'status',
             'created_at', 'last_updated', 'messages', 'order', 'product']
        )


class TicketCreateSerializerTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
        # Ticket data for serializer
        self.ticket_data = {
            'subject': 'Payment Issue',
            'description': 'My payment was processed but order not confirmed.',
            'priority': 'high'
        }
        
        self.serializer = TicketCreateSerializer(
            data=self.ticket_data,
            context={'request': type('obj', (object,), {'user': self.user})}
        )
    
    def test_validate_success(self):
        """Test successful validation"""
        self.assertTrue(self.serializer.is_valid())
        
    def test_create_ticket(self):
        """Test creating a ticket with the serializer"""
        self.assertTrue(self.serializer.is_valid())
        ticket = self.serializer.save()
        
        self.assertEqual(ticket.user, self.user)
        self.assertEqual(ticket.subject, 'Payment Issue')
        self.assertEqual(ticket.description, 'My payment was processed but order not confirmed.')
        self.assertEqual(ticket.priority, 'high')
        self.assertEqual(ticket.status, 'open')  # Default status


class FAQSerializerTest(TestCase):
    def setUp(self):
        # Create FAQ category
        self.category = FAQCategory.objects.create(
            name="Orders",
            slug="orders",
            description="Frequently asked questions about orders."
        )
        
        # Create FAQ
        self.faq = FAQ.objects.create(
            category=self.category,
            question="How do I track my order?",
            answer="You can track your order in your account dashboard.",
            is_published=True
        )
        
        self.serializer = FAQSerializer(instance=self.faq)
    
    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields"""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'category', 'question', 'answer', 'is_published', 'created_at', 'updated_at']
        )
        
    def test_field_content(self):
        """Test field content"""
        data = self.serializer.data
        self.assertEqual(data['category'], self.category.id)
        self.assertEqual(data['question'], self.faq.question)
        self.assertEqual(data['answer'], self.faq.answer)
        self.assertEqual(data['is_published'], self.faq.is_published)


class KnowledgeBaseSerializerTest(TestCase):
    def setUp(self):
        # Create knowledge base category
        self.category = KnowledgeBaseCategory.objects.create(
            name="Getting Started",
            slug="getting-started",
            description="Articles to help you get started."
        )
        
        # Create knowledge base article
        self.article = KnowledgeBase.objects.create(
            category=self.category,
            title="How to Create an Account",
            content="Follow these steps to create an account...",
            slug="how-to-create-account",
            is_published=True
        )
        
        self.serializer = KnowledgeBaseSerializer(instance=self.article)
    
    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields"""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'category', 'title', 'content', 'slug', 'is_published', 
             'created_at', 'updated_at', 'meta_title', 'meta_description']
        )
        
    def test_field_content(self):
        """Test field content"""
        data = self.serializer.data
        self.assertEqual(data['category'], self.category.id)
        self.assertEqual(data['title'], self.article.title)
        self.assertEqual(data['content'], self.article.content)
        self.assertEqual(data['slug'], self.article.slug)
        self.assertEqual(data['is_published'], self.article.is_published)