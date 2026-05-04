# support/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from support.models import Ticket, TicketMessage, FAQ, FAQCategory, KnowledgeBase, KnowledgeBaseCategory
from django.utils import timezone

User = get_user_model()

class TicketModelTest(TestCase):
    def setUp(self):
        # Create users
        self.customer = User.objects.create_user(
            email='customer@example.com',
            password='password123',
            first_name='Test',
            last_name='Customer'
        )
        
        self.staff = User.objects.create_user(
            email='staff@example.com',
            password='password123',
            is_staff=True
        )
        
        # Create ticket
        self.ticket = Ticket.objects.create(
            user=self.customer,
            subject="Order Issue",
            description="I have an issue with my recent order.",
            priority="medium",
            status="open"
        )
        
        # Create ticket message
        self.message = TicketMessage.objects.create(
            ticket=self.ticket,
            user=self.customer,
            message="Can you please help with my order?"
        )
        
        self.staff_message = TicketMessage.objects.create(
            ticket=self.ticket,
            user=self.staff,
            message="I'll look into this for you.",
            is_staff_response=True
        )
    
    def test_ticket_creation(self):
        """Test creating a ticket"""
        self.assertEqual(self.ticket.user, self.customer)
        self.assertEqual(self.ticket.subject, "Order Issue")
        self.assertEqual(self.ticket.description, "I have an issue with my recent order.")
        self.assertEqual(self.ticket.priority, "medium")
        self.assertEqual(self.ticket.status, "open")
        
    def test_ticket_str(self):
        """Test the string representation of a ticket"""
        expected_str = f"Ticket #{self.ticket.id}: Order Issue"
        self.assertEqual(str(self.ticket), expected_str)
        
    def test_ticket_message_creation(self):
        """Test creating ticket messages"""
        self.assertEqual(self.message.ticket, self.ticket)
        self.assertEqual(self.message.user, self.customer)
        self.assertEqual(self.message.message, "Can you please help with my order?")
        self.assertFalse(self.message.is_staff_response)
        
        self.assertEqual(self.staff_message.ticket, self.ticket)
        self.assertEqual(self.staff_message.user, self.staff)
        self.assertEqual(self.staff_message.message, "I'll look into this for you.")
        self.assertTrue(self.staff_message.is_staff_response)
        
    def test_ticket_message_str(self):
        """Test the string representation of a ticket message"""
        expected_str = f"Message on Ticket #{self.ticket.id} by {self.customer.email}"
        self.assertEqual(str(self.message), expected_str)
        
    def test_ticket_last_updated(self):
        """Test that ticket last_updated is updated when messages are added"""
        original_updated = self.ticket.last_updated
        
        # Add a new message
        new_message = TicketMessage.objects.create(
            ticket=self.ticket,
            user=self.staff,
            message="Any updates from your side?",
            is_staff_response=True
        )
        
        self.ticket.refresh_from_db()
        self.assertGreater(self.ticket.last_updated, original_updated)


class FAQModelTest(TestCase):
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
    
    def test_faq_category_creation(self):
        """Test creating an FAQ category"""
        self.assertEqual(self.category.name, "Orders")
        self.assertEqual(self.category.slug, "orders")
        self.assertEqual(self.category.description, "Frequently asked questions about orders.")
        
    def test_faq_category_str(self):
        """Test the string representation of an FAQ category"""
        self.assertEqual(str(self.category), "Orders")
        
    def test_faq_creation(self):
        """Test creating an FAQ"""
        self.assertEqual(self.faq.category, self.category)
        self.assertEqual(self.faq.question, "How do I track my order?")
        self.assertEqual(self.faq.answer, "You can track your order in your account dashboard.")
        self.assertTrue(self.faq.is_published)
        
    def test_faq_str(self):
        """Test the string representation of an FAQ"""
        self.assertEqual(str(self.faq), "How do I track my order?")


class KnowledgeBaseModelTest(TestCase):
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
    
    def test_kb_category_creation(self):
        """Test creating a knowledge base category"""
        self.assertEqual(self.category.name, "Getting Started")
        self.assertEqual(self.category.slug, "getting-started")
        self.assertEqual(self.category.description, "Articles to help you get started.")
        
    def test_kb_category_str(self):
        """Test the string representation of a knowledge base category"""
        self.assertEqual(str(self.category), "Getting Started")
        
    def test_kb_article_creation(self):
        """Test creating a knowledge base article"""
        self.assertEqual(self.article.category, self.category)
        self.assertEqual(self.article.title, "How to Create an Account")
        self.assertEqual(self.article.content, "Follow these steps to create an account...")
        self.assertEqual(self.article.slug, "how-to-create-account")
        self.assertTrue(self.article.is_published)
        
    def test_kb_article_str(self):
        """Test the string representation of a knowledge base article"""
        self.assertEqual(str(self.article), "How to Create an Account")