# analytics/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from analytics.models import (
    PageView, Event, SearchQuery, UserSession,
    Report, Dashboard, DashboardWidget, Funnel, FunnelEntry, FunnelStep
)
from datetime import timedelta
import json

User = get_user_model()

class PageViewModelTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
        # Create page view
        self.page_view = PageView.objects.create(
            user=self.user,
            session_key='test_session_key',
            url='https://example.com/products/1',
            path='/products/1',
            query_string='ref=homepage',
            method='GET',
            page_title='Product Detail',
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            referrer='https://example.com',
            device_type='desktop',
            browser='Chrome',
            browser_version='92.0.4515.159',
            operating_system='Windows 10',
            country='US',
            region='CA',
            city='San Francisco',
            utm_source='email',
            utm_medium='newsletter',
            utm_campaign='summer_sale',
            load_time=1.25
        )
    
    def test_page_view_creation(self):
        """Test creating a page view"""
        self.assertEqual(self.page_view.user, self.user)
        self.assertEqual(self.page_view.session_key, 'test_session_key')
        self.assertEqual(self.page_view.url, 'https://example.com/products/1')
        self.assertEqual(self.page_view.path, '/products/1')
        self.assertEqual(self.page_view.query_string, 'ref=homepage')
        self.assertEqual(self.page_view.method, 'GET')
        self.assertEqual(self.page_view.page_title, 'Product Detail')
        self.assertEqual(self.page_view.ip_address, '127.0.0.1')
        self.assertEqual(self.page_view.device_type, 'desktop')
        self.assertEqual(self.page_view.browser, 'Chrome')
        self.assertEqual(self.page_view.utm_source, 'email')
        self.assertEqual(self.page_view.utm_campaign, 'summer_sale')
        self.assertEqual(self.page_view.load_time, 1.25)
        
    def test_page_view_str(self):
        """Test the string representation of a page view"""
        expected_str = f"PageView: {self.page_view.path} by {self.user.email}"
        self.assertEqual(str(self.page_view), expected_str)


class EventModelTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
        # Create event
        self.event = Event.objects.create(
            user=self.user,
            session_key='test_session_key',
            category='product',
            action='add_to_cart',
            label='Product 1',
            value=1,
            data={'product_id': 1, 'quantity': 1},
            url='https://example.com/products/1',
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        )
    
    def test_event_creation(self):
        """Test creating an event"""
        self.assertEqual(self.event.user, self.user)
        self.assertEqual(self.event.session_key, 'test_session_key')
        self.assertEqual(self.event.category, 'product')
        self.assertEqual(self.event.action, 'add_to_cart')
        self.assertEqual(self.event.label, 'Product 1')
        self.assertEqual(self.event.value, 1)
        self.assertEqual(self.event.data, {'product_id': 1, 'quantity': 1})
        self.assertEqual(self.event.url, 'https://example.com/products/1')
        self.assertEqual(self.event.ip_address, '127.0.0.1')
        
    def test_event_str(self):
        """Test the string representation of an event"""
        expected_str = f"Event: {self.event.category} - {self.event.action} by {self.user.email}"
        self.assertEqual(str(self.event), expected_str)


class UserSessionModelTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='password123'
        )
        
        # Create user session
        self.start_time = timezone.now() - timedelta(minutes=30)
        self.end_time = timezone.now()
        
        self.session = UserSession.objects.create(
            user=self.user,
            session_key='test_session_key',
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            device_type='desktop',
            browser='Chrome',
            operating_system='Windows 10',
            country='US',
            region='CA',
            city='San Francisco',
            referrer='https://google.com',
            landing_page='https://example.com',
            exit_page='https://example.com/products',
            utm_source='google',
            utm_medium='cpc',
            utm_campaign='search_campaign',
            start_time=self.start_time,
            end_time=self.end_time,
            page_views=5,
            events=2,
            is_bounce=False
        )
    
    def test_session_creation(self):
        """Test creating a user session"""
        self.assertEqual(self.session.user, self.user)
        self.assertEqual(self.session.session_key, 'test_session_key')
        self.assertEqual(self.session.ip_address, '127.0.0.1')
        self.assertEqual(self.session.device_type, 'desktop')
        self.assertEqual(self.session.browser, 'Chrome')
        self.assertEqual(self.session.utm_source, 'google')
        self.assertEqual(self.session.utm_campaign, 'search_campaign')
        self.assertEqual(self.session.page_views, 5)
        self.assertEqual(self.session.events, 2)
        self.assertFalse(self.session.is_bounce)
        
    def test_session_str(self):
        """Test the string representation of a user session"""
        expected_str = f"Session: {self.session.session_key} by {self.user.email}"
        self.assertEqual(str(self.session), expected_str)
        
    def test_duration_calculation(self):
        """Test session duration calculation"""
        expected_duration = self.end_time - self.start_time
        self.session.update_duration()
        self.assertEqual(self.session.duration, expected_duration)


class ReportModelTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='analyst@example.com',
            password='password123'
        )
        
        # Create report
        self.report = Report.objects.create(
            name='Monthly Sales Report',
            description='Monthly sales analysis',
            type='sales',
            period='monthly',
            created_by=self.user,
            parameters={'include_tax': True, 'group_by': 'product'},
            data={'total_sales': 12500, 'orders_count': 250},
            is_public=True
        )
    
    def test_report_creation(self):
        """Test creating a report"""
        self.assertEqual(self.report.name, 'Monthly Sales Report')
        self.assertEqual(self.report.description, 'Monthly sales analysis')
        self.assertEqual(self.report.type, 'sales')
        self.assertEqual(self.report.period, 'monthly')
        self.assertEqual(self.report.created_by, self.user)
        self.assertEqual(self.report.parameters, {'include_tax': True, 'group_by': 'product'})
        self.assertEqual(self.report.data, {'total_sales': 12500, 'orders_count': 250})
        self.assertTrue(self.report.is_public)
        
    def test_report_str(self):
        """Test the string representation of a report"""
        self.assertEqual(str(self.report), 'Monthly Sales Report')


class DashboardModelTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='analyst@example.com',
            password='password123'
        )
        
        # Create report
        self.report = Report.objects.create(
            name='Monthly Sales Report',
            description='Monthly sales analysis',
            type='sales',
            period='monthly',
            created_by=self.user,
            data={'total_sales': 12500},
            is_public=True
        )
        
        # Create dashboard
        self.dashboard = Dashboard.objects.create(
            name='Sales Dashboard',
            description='Sales overview dashboard',
            user=self.user,
            layout='grid',
            is_default=True
        )
        
        # Create dashboard widget
        self.widget = DashboardWidget.objects.create(
            dashboard=self.dashboard,
            name='Sales Overview',
            type='chart',
            report=self.report,
            configuration={'chart_type': 'bar', 'data_field': 'sales_by_date'},
            position_x=0,
            position_y=0,
            width=6,
            height=4
        )
    
    def test_dashboard_creation(self):
        """Test creating a dashboard"""
        self.assertEqual(self.dashboard.name, 'Sales Dashboard')
        self.assertEqual(self.dashboard.description, 'Sales overview dashboard')
        self.assertEqual(self.dashboard.user, self.user)
        self.assertEqual(self.dashboard.layout, 'grid')
        self.assertTrue(self.dashboard.is_default)
        
    def test_dashboard_str(self):
        """Test the string representation of a dashboard"""
        self.assertEqual(str(self.dashboard), 'Sales Dashboard')
        
    def test_widget_creation(self):
        """Test creating a dashboard widget"""
        self.assertEqual(self.widget.dashboard, self.dashboard)
        self.assertEqual(self.widget.name, 'Sales Overview')
        self.assertEqual(self.widget.type, 'chart')
        self.assertEqual(self.widget.report, self.report)
        self.assertEqual(self.widget.configuration, {'chart_type': 'bar', 'data_field': 'sales_by_date'})
        self.assertEqual(self.widget.position_x, 0)
        self.assertEqual(self.widget.position_y, 0)
        self.assertEqual(self.widget.width, 6)
        self.assertEqual(self.widget.height, 4)
        
    def test_widget_str(self):
        """Test the string representation of a dashboard widget"""
        self.assertEqual(str(self.widget), 'Sales Overview')


class FunnelModelTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='analyst@example.com',
            password='password123'
        )
        
        # Create funnel
        self.funnel = Funnel.objects.create(
            name='Checkout Funnel',
            description='Checkout process funnel',
            created_by=self.user,
            steps=[
                {'name': 'View Cart', 'url_pattern': '/cart/'},
                {'name': 'Enter Shipping', 'url_pattern': '/checkout/shipping/'},
                {'name': 'Enter Payment', 'url_pattern': '/checkout/payment/'},
                {'name': 'Confirm Order', 'url_pattern': '/checkout/confirm/'},
                {'name': 'Order Complete', 'url_pattern': '/checkout/complete/'}
            ],
            is_active=True
        )
        
        # Create funnel entry
        self.entry = FunnelEntry.objects.create(
            funnel=self.funnel,
            user=self.user,
            session_key='test_session_key',
            current_step=2,
            data={'cart_id': 123},
            is_completed=False
        )
        
        # Create funnel steps
        self.step1 = FunnelStep.objects.create(
            entry=self.entry,
            step_number=0,
            step_name='View Cart',
            data={'cart_items': 3}
        )
        
        self.step2 = FunnelStep.objects.create(
            entry=self.entry,
            step_number=1,
            step_name='Enter Shipping',
            data={'shipping_method': 'standard'}
        )
        
        self.step3 = FunnelStep.objects.create(
            entry=self.entry,
            step_number=2,
            step_name='Enter Payment',
            data={'payment_method': 'credit_card'}
        )
    
    def test_funnel_creation(self):
        """Test creating a funnel"""
        self.assertEqual(self.funnel.name, 'Checkout Funnel')
        self.assertEqual(self.funnel.description, 'Checkout process funnel')
        self.assertEqual(self.funnel.created_by, self.user)
        self.assertEqual(len(self.funnel.steps), 5)
        self.assertEqual(self.funnel.steps[0]['name'], 'View Cart')
        self.assertTrue(self.funnel.is_active)
        
    def test_funnel_str(self):
        """Test the string representation of a funnel"""
        self.assertEqual(str(self.funnel), 'Checkout Funnel')
        
    def test_funnel_entry_creation(self):
        """Test creating a funnel entry"""
        self.assertEqual(self.entry.funnel, self.funnel)
        self.assertEqual(self.entry.user, self.user)
        self.assertEqual(self.entry.session_key, 'test_session_key')
        self.assertEqual(self.entry.current_step, 2)
        self.assertEqual(self.entry.data, {'cart_id': 123})
        self.assertFalse(self.entry.is_completed)
        
    def test_funnel_entry_str(self):
        """Test the string representation of a funnel entry"""
        expected_str = f"Entry for {self.funnel.name} by {self.user.email}"
        self.assertEqual(str(self.entry), expected_str)
        
    def test_funnel_step_creation(self):
        """Test creating funnel steps"""
        self.assertEqual(self.step1.entry, self.entry)
        self.assertEqual(self.step1.step_number, 0)
        self.assertEqual(self.step1.step_name, 'View Cart')
        self.assertEqual(self.step1.data, {'cart_items': 3})
        
        self.assertEqual(self.step3.step_number, 2)
        self.assertEqual(self.step3.step_name, 'Enter Payment')
        self.assertEqual(self.step3.data, {'payment_method': 'credit_card'})
        
    def test_funnel_step_str(self):
        """Test the string representation of a funnel step"""
        expected_str = f"Step {self.step1.step_number} ({self.step1.step_name}) for Entry #{self.entry.id}"
        self.assertEqual(str(self.step1), expected_str)
        
    def test_complete_funnel(self):
        """Test completing a funnel"""
        self.assertFalse(self.entry.is_completed)
        self.assertIsNone(self.entry.completed_at)
        
        self.entry.complete()
        
        self.assertTrue(self.entry.is_completed)
        self.assertIsNotNone(self.entry.completed_at)