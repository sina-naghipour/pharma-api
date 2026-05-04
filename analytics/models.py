# analytics/models.py
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class PageView(models.Model):
    """Track page views"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User info (if authenticated)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='page_views',
        verbose_name=_('User')
    )
    
    # Session info
    session_key = models.CharField(_('Session Key'), max_length=40, blank=True)
    
    # Request info
    url = models.URLField(_('URL'))
    path = models.CharField(_('Path'), max_length=255)
    query_string = models.TextField(_('Query String'), blank=True)
    method = models.CharField(_('HTTP Method'), max_length=10)
    
    # Page info
    page_title = models.CharField(_('Page Title'), max_length=255, blank=True)
    
    # Generic relation to viewed object (e.g., product, category)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='page_views',
        verbose_name=_('Content Type')
    )
    object_id = models.CharField(_('Object ID'), max_length=50, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Visitor info
    ip_address = models.GenericIPAddressField(_('IP Address'), blank=True, null=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    referrer = models.URLField(_('Referrer'), blank=True)
    
    # Device info
    device_type = models.CharField(_('Device Type'), max_length=20, blank=True)
    browser = models.CharField(_('Browser'), max_length=50, blank=True)
    browser_version = models.CharField(_('Browser Version'), max_length=20, blank=True)
    operating_system = models.CharField(_('Operating System'), max_length=50, blank=True)
    
    # Location info (if available)
    country = models.CharField(_('Country'), max_length=50, blank=True)
    region = models.CharField(_('Region'), max_length=100, blank=True)
    city = models.CharField(_('City'), max_length=100, blank=True)
    
    # UTM tracking parameters
    utm_source = models.CharField(_('UTM Source'), max_length=100, blank=True)
    utm_medium = models.CharField(_('UTM Medium'), max_length=100, blank=True)
    utm_campaign = models.CharField(_('UTM Campaign'), max_length=100, blank=True)
    utm_term = models.CharField(_('UTM Term'), max_length=100, blank=True)
    utm_content = models.CharField(_('UTM Content'), max_length=100, blank=True)
    
    # Timestamps
    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True, db_index=True)
    
    # Performance metrics
    load_time = models.FloatField(_('Load Time (ms)'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Page View')
        verbose_name_plural = _('Page Views')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['path']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['session_key']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['device_type']),
        ]
    
    def __str__(self):
        return f"{self.path} - {self.timestamp}"


class Event(models.Model):
    """Track user events"""
    # Event categories
    CATEGORY_PRODUCT = 'product'
    CATEGORY_CART = 'cart'
    CATEGORY_CHECKOUT = 'checkout'
    CATEGORY_SEARCH = 'search'
    CATEGORY_USER = 'user'
    CATEGORY_NAVIGATION = 'navigation'
    CATEGORY_PROMOTION = 'promotion'
    CATEGORY_OTHER = 'other'
    
    CATEGORY_CHOICES = [
        (CATEGORY_PRODUCT, _('Product')),
        (CATEGORY_CART, _('Cart')),
        (CATEGORY_CHECKOUT, _('Checkout')),
        (CATEGORY_SEARCH, _('Search')),
        (CATEGORY_USER, _('User')),
        (CATEGORY_NAVIGATION, _('Navigation')),
        (CATEGORY_PROMOTION, _('Promotion')),
        (CATEGORY_OTHER, _('Other')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User info (if authenticated)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        verbose_name=_('User')
    )
    
    # Session info
    session_key = models.CharField(_('Session Key'), max_length=40, blank=True)
    
    # Event info
    category = models.CharField(_('Category'), max_length=20, choices=CATEGORY_CHOICES)
    action = models.CharField(_('Action'), max_length=50)
    label = models.CharField(_('Label'), max_length=255, blank=True)
    value = models.IntegerField(_('Value'), null=True, blank=True)
    
    # Additional data (stored as JSON)
    data = models.JSONField(_('Data'), default=dict, blank=True)
    
    # Generic relation to related object
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        verbose_name=_('Content Type')
    )
    object_id = models.CharField(_('Object ID'), max_length=50, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Context info
    url = models.URLField(_('URL'), blank=True)
    ip_address = models.GenericIPAddressField(_('IP Address'), blank=True, null=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    
    # Timestamps
    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = _('Event')
        verbose_name_plural = _('Events')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['session_key']),
        ]
    
    def __str__(self):
        return f"{self.category} - {self.action} - {self.timestamp}"


class SearchQuery(models.Model):
    """Track search queries"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User info (if authenticated)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='search_queries',
        verbose_name=_('User')
    )
    
    # Session info
    session_key = models.CharField(_('Session Key'), max_length=40, blank=True)
    
    # Search info
    query = models.CharField(_('Search Query'), max_length=255)
    category = models.CharField(_('Category'), max_length=50, blank=True)
    filters = models.JSONField(_('Filters'), default=dict, blank=True)
    
    # Results info
    result_count = models.IntegerField(_('Result Count'), default=0)
    
    # Timestamps
    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True)
    
    # Context info
    ip_address = models.GenericIPAddressField(_('IP Address'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('Search Query')
        verbose_name_plural = _('Search Queries')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['query']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.query} - {self.timestamp}"


class UserSession(models.Model):
    """Track user sessions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User info (if authenticated)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions',
        verbose_name=_('User')
    )
    
    # Session info
    session_key = models.CharField(_('Session Key'), max_length=40, unique=True)
    
    # Session timing
    start_time = models.DateTimeField(_('Start Time'), auto_now_add=True)
    end_time = models.DateTimeField(_('End Time'), null=True, blank=True)
    duration = models.DurationField(_('Duration'), null=True, blank=True)
    
    # Visitor info
    ip_address = models.GenericIPAddressField(_('IP Address'), blank=True, null=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    
    # Device info
    device_type = models.CharField(_('Device Type'), max_length=20, blank=True)
    browser = models.CharField(_('Browser'), max_length=50, blank=True)
    operating_system = models.CharField(_('Operating System'), max_length=50, blank=True)
    
    # Location info
    country = models.CharField(_('Country'), max_length=50, blank=True)
    region = models.CharField(_('Region'), max_length=100, blank=True)
    city = models.CharField(_('City'), max_length=100, blank=True)
    
    # Referrer info
    referrer = models.URLField(_('Referrer'), blank=True)
    landing_page = models.URLField(_('Landing Page'), blank=True)
    exit_page = models.URLField(_('Exit Page'), blank=True)
    
    # Session activity
    page_views = models.IntegerField(_('Page Views'), default=0)
    events = models.IntegerField(_('Events'), default=0)
    is_bounce = models.BooleanField(_('Is Bounce'), default=True)
    
    # UTM parameters
    utm_source = models.CharField(_('UTM Source'), max_length=100, blank=True)
    utm_medium = models.CharField(_('UTM Medium'), max_length=100, blank=True)
    utm_campaign = models.CharField(_('UTM Campaign'), max_length=100, blank=True)
    
    class Meta:
        verbose_name = _('User Session')
        verbose_name_plural = _('User Sessions')
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['start_time']),
            models.Index(fields=['is_bounce']),
        ]
    
    def __str__(self):
        if self.user:
            return f"Session for {self.user.email} - {self.start_time}"
        return f"Anonymous session - {self.start_time}"
    
    def update_duration(self):
        """Update session duration if end time is set"""
        if self.end_time:
            self.duration = self.end_time - self.start_time
            self.save(update_fields=['duration'])


class Report(models.Model):
    """Saved analytics reports"""
    # Report types
    TYPE_SALES = 'sales'
    TYPE_PRODUCTS = 'products'
    TYPE_CUSTOMERS = 'customers'
    TYPE_TRAFFIC = 'traffic'
    TYPE_MARKETING = 'marketing'
    TYPE_CUSTOM = 'custom'
    
    TYPE_CHOICES = [
        (TYPE_SALES, _('Sales')),
        (TYPE_PRODUCTS, _('Products')),
        (TYPE_CUSTOMERS, _('Customers')),
        (TYPE_TRAFFIC, _('Traffic')),
        (TYPE_MARKETING, _('Marketing')),
        (TYPE_CUSTOM, _('Custom')),
    ]
    
    # Time periods
    PERIOD_DAILY = 'daily'
    PERIOD_WEEKLY = 'weekly'
    PERIOD_MONTHLY = 'monthly'
    PERIOD_QUARTERLY = 'quarterly'
    PERIOD_YEARLY = 'yearly'
    PERIOD_CUSTOM = 'custom'
    
    PERIOD_CHOICES = [
        (PERIOD_DAILY, _('Daily')),
        (PERIOD_WEEKLY, _('Weekly')),
        (PERIOD_MONTHLY, _('Monthly')),
        (PERIOD_QUARTERLY, _('Quarterly')),
        (PERIOD_YEARLY, _('Yearly')),
        (PERIOD_CUSTOM, _('Custom')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    
    # Report configuration
    type = models.CharField(_('Type'), max_length=20, choices=TYPE_CHOICES)
    period = models.CharField(_('Period'), max_length=20, choices=PERIOD_CHOICES)
    
    # Date range for custom periods
    start_date = models.DateField(_('Start Date'), null=True, blank=True)
    end_date = models.DateField(_('End Date'), null=True, blank=True)
    
    # Report parameters
    parameters = models.JSONField(_('Parameters'), default=dict, blank=True)
    
    # Report data
    data = models.JSONField(_('Data'), default=dict, blank=True)
    last_generated = models.DateTimeField(_('Last Generated'), null=True, blank=True)
    
    # User who created the report
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_reports',
        verbose_name=_('Created By')
    )
    
    # Sharing and permissions
    is_public = models.BooleanField(_('Public'), default=False)
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='shared_reports',
        verbose_name=_('Shared With'),
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class Dashboard(models.Model):
    """User dashboards with multiple reports/widgets"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    
    # User who owns the dashboard
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dashboards',
        verbose_name=_('User')
    )
    
    # Dashboard layout and configuration
    layout = models.JSONField(_('Layout'), default=dict, blank=True)
    is_default = models.BooleanField(_('Default Dashboard'), default=False)
    
    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Dashboard')
        verbose_name_plural = _('Dashboards')
        ordering = ['-is_default', 'name']
        unique_together = [['user', 'name']]
    
    def __str__(self):
        return f"{self.name} ({self.user.email})"
    
    def save(self, *args, **kwargs):
        """Ensure only one default dashboard per user"""
        if self.is_default:
            Dashboard.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class DashboardWidget(models.Model):
    """Widgets displayed on dashboards"""
    # Widget types
    TYPE_CHART = 'chart'
    TYPE_COUNTER = 'counter'
    TYPE_TABLE = 'table'
    TYPE_MAP = 'map'
    TYPE_CUSTOM = 'custom'
    
    TYPE_CHOICES = [
        (TYPE_CHART, _('Chart')),
        (TYPE_COUNTER, _('Counter')),
        (TYPE_TABLE, _('Table')),
        (TYPE_MAP, _('Map')),
        (TYPE_CUSTOM, _('Custom')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.CASCADE,
        related_name='widgets',
        verbose_name=_('Dashboard')
    )
    name = models.CharField(_('Name'), max_length=100)
    
    # Widget configuration
    type = models.CharField(_('Type'), max_length=20, choices=TYPE_CHOICES)
    configuration = models.JSONField(_('Configuration'), default=dict)
    
    # Optional report link
    report = models.ForeignKey(
        Report,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='widgets',
        verbose_name=_('Report')
    )
    
    # Layout position
    position_x = models.PositiveSmallIntegerField(_('Position X'), default=0)
    position_y = models.PositiveSmallIntegerField(_('Position Y'), default=0)
    width = models.PositiveSmallIntegerField(_('Width'), default=1)
    height = models.PositiveSmallIntegerField(_('Height'), default=1)
    
    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Dashboard Widget')
        verbose_name_plural = _('Dashboard Widgets')
        ordering = ['dashboard', 'position_y', 'position_x']
    
    def __str__(self):
        return f"{self.name} on {self.dashboard.name}"


class Funnel(models.Model):
    """Conversion funnels"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    
    # User who created the funnel
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_funnels',
        verbose_name=_('Created By')
    )
    
    # Funnel configuration
    steps = models.JSONField(_('Steps'), default=list)
    is_active = models.BooleanField(_('Active'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Funnel')
        verbose_name_plural = _('Funnels')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class FunnelEntry(models.Model):
    """Individual entries through a funnel"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    funnel = models.ForeignKey(
        Funnel,
        on_delete=models.CASCADE,
        related_name='entries',
        verbose_name=_('Funnel')
    )
    
    # User info
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='funnel_entries',
        verbose_name=_('User')
    )
    session_key = models.CharField(_('Session Key'), max_length=40, blank=True)
    
    # Entry progress
    current_step = models.PositiveSmallIntegerField(_('Current Step'), default=0)
    is_completed = models.BooleanField(_('Completed'), default=False)
    completed_at = models.DateTimeField(_('Completed At'), null=True, blank=True)
    
    # Entry data
    data = models.JSONField(_('Data'), default=dict, blank=True)
    
    # Timestamps
    started_at = models.DateTimeField(_('Started At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Funnel Entry')
        verbose_name_plural = _('Funnel Entries')
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['funnel', 'is_completed']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"Entry for {self.funnel.name} - {self.started_at}"
    
    def complete(self):
        """Mark the funnel entry as completed"""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=['is_completed', 'completed_at', 'updated_at'])


class FunnelStep(models.Model):
    """Individual step completions within a funnel entry"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(
        FunnelEntry,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name=_('Funnel Entry')
    )
    
    # Step info
    step_number = models.PositiveSmallIntegerField(_('Step Number'))
    step_name = models.CharField(_('Step Name'), max_length=100)
    
    # Step data
    data = models.JSONField(_('Data'), default=dict, blank=True)
    
    # Timestamps
    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Funnel Step')
        verbose_name_plural = _('Funnel Steps')
        ordering = ['entry', 'step_number']
        unique_together = [['entry', 'step_number']]
    
    def __str__(self):
        return f"Step {self.step_number} ({self.step_name}) for {self.entry}"