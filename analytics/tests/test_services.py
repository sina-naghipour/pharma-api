# analytics/tests/test_services.py
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from analytics.models import PageView, Event, SearchQuery, UserSession, Report
from analytics.services import (
    track_page_view, track_event, track_search_query,
    get_client_ip, generate_report_data, get_report_date_range
)
from datetime import timedelta
import json

User = get_user_model()

class TrackingServicesTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
    def test_track_page_view(self):
        """Test tracking a page view"""
        # Create a request
        request = self.factory.get('/products/1')
        request.user = self.user
        request.session = self.client.session
        request.session.create()
        request.META = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'HTTP_REFERER': 'https://example.com',
            'REMOTE_ADDR': '127.0.0.1'
        }
        
        # Track page view
        page_view = track_page_view(request)
        
        # Check page view was created
        self.assertEqual(PageView.objects.count(), 1)
        self.assertEqual(page_view.user, self.user)
        self.assertEqual(page_view.path, '/products/1')
        self.assertEqual(page_view.method, 'GET')
        self.assertEqual(page_view.ip_address, '127.0.0.1')
        
        # Check user session was created
        self.assertEqual(UserSession.objects.count(), 1)
        session = UserSession.objects.first()
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.page_views, 1)
        self.assertTrue(session.is_bounce)
        
    def test_track_event(self):
        """Test tracking an event"""
        # Create a request
        request = self.factory.get('/products/1')
        request.user = self.user
        request.session = self.client.session
        request.session.create()
        request.META = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'REMOTE_ADDR': '127.0.0.1'
        }
        
        # Create session first
        track_page_view(request)
        
        # Track event
        event_data = {
            'category': 'product',
            'action': 'add_to_cart',
            'label': 'Product 1',
            'value': 1,
            'data': {'product_id': 1, 'quantity': 1}
        }
        event = track_event(request, event_data)
        
        # Check event was created
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.category, 'product')
        self.assertEqual(event.action, 'add_to_cart')
        self.assertEqual(event.label, 'Product 1')
        self.assertEqual(event.value, 1)
        self.assertEqual(event.data, {'product_id': 1, 'quantity': 1})
        
        # Check user session was updated
        session = UserSession.objects.first()
        self.assertEqual(session.events, 1)
        self.assertFalse(session.is_bounce)
        
    def test_track_search_query(self):
        """Test tracking a search query"""
        # Create a request
        request = self.factory.get('/search')
        request.user = self.user
        request.session = self.client.session
        request.session.create()
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        # Track search query
        search_data = {
            'query': 'aspirin',
            'category': 'products',
            'filters': {'min_price': 10, 'max_price': 50},
            'result_count': 5
        }
        search_query = track_search_query(request, search_data)
        
        # Check search query was created
        self.assertEqual(SearchQuery.objects.count(), 1)
        self.assertEqual(search_query.user, self.user)
        self.assertEqual(search_query.query, 'aspirin')
        self.assertEqual(search_query.category, 'products')
        self.assertEqual(search_query.filters, {'min_price': 10, 'max_price': 50})
        self.assertEqual(search_query.result_count, 5)
        self.assertEqual(search_query.ip_address, '127.0.0.1')
        
    def test_get_client_ip(self):
        """Test extracting client IP from request"""
        # Test with REMOTE_ADDR
        request = self.factory.get('/')
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        self.assertEqual(get_client_ip(request), '127.0.0.1')
        
        # Test with HTTP_X_FORWARDED_FOR
        request.META = {
            'HTTP_X_FORWARDED_FOR': '192.168.1.1, 10.0.0.1',
            'REMOTE_ADDR': '127.0.0.1'
        }
        self.assertEqual(get_client_ip(request), '192.168.1.1')


class ReportServicesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='analyst@example.com',
            password='password123'
        )
        
        # Create report
        self.daily_report = Report.objects.create(
            name='Daily Sales Report',
            description='Daily sales analysis',
            type='sales',
            period='daily',
            created_by=self.user
        )
        
        self.monthly_report = Report.objects.create(
            name='Monthly Sales Report',
            description='Monthly sales analysis',
            type='sales',
            period='monthly',
            created_by=self.user
        )
        
        self.custom_report = Report.objects.create(
            name='Custom Report',
            description='Custom date range report',
            type='sales',
            period='custom',
            start_date=timezone.now().date() - timedelta(days=15),
            end_date=timezone.now().date() - timedelta(days=5),
            created_by=self.user
        )
        
    def test_get_report_date_range_daily(self):
        """Test getting date range for daily report"""
        start_date, end_date = get_report_date_range(self.daily_report)
        
        # Should be last 24 hours
        self.assertAlmostEqual(
            (end_date - start_date).total_seconds(),
            24 * 60 * 60,  # 24 hours in seconds
            delta=10  # Allow small difference due to execution time
        )
        
    def test_get_report_date_range_monthly(self):
        """Test getting date range for monthly report"""
        start_date, end_date = get_report_date_range(self.monthly_report)
        
        # Should be last 30 days
        self.assertAlmostEqual(
            (end_date - start_date).total_seconds(),
            30 * 24 * 60 * 60,  # 30 days in seconds
            delta=10  # Allow small difference due to execution time
        )
        
    def test_get_report_date_range_custom(self):
        """Test getting date range for custom report"""
        start_date, end_date = get_report_date_range(self.custom_report)
        
        # Should match the custom dates
        self.assertEqual(start_date.date(), self.custom_report.start_date)
        self.assertEqual(end_date.date(), self.custom_report.end_date)