# analytics/services.py
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Count, Avg, Sum, Q, Case, When, models
from user_agents import parse
import json
from urllib.parse import urlparse, parse_qs
from datetime import timedelta, datetime
from django.db.models.functions import TruncDate
from .models import (
    PageView, Event, SearchQuery, UserSession,
    Report, Funnel, FunnelEntry, FunnelStep
)


def track_page_view(request, data=None):
    """Track a page view"""
    if data is None:
        data = {}
    
    # Get or create session
    session_key = request.session.session_key
    if not session_key:
        request.session.save()
        session_key = request.session.session_key
    
    # Extract URL components
    url = data.get('url', request.build_absolute_uri())
    parsed_url = urlparse(url)
    path = data.get('path', parsed_url.path)
    query_string = data.get('query_string', parsed_url.query)
    
    # Extract UTM parameters from query string
    query_params = parse_qs(query_string)
    utm_source = query_params.get('utm_source', [''])[0]
    utm_medium = query_params.get('utm_medium', [''])[0]
    utm_campaign = query_params.get('utm_campaign', [''])[0]
    utm_term = query_params.get('utm_term', [''])[0]
    utm_content = query_params.get('utm_content', [''])[0]
    
    # Parse user agent
    user_agent_string = data.get('user_agent', request.META.get('HTTP_USER_AGENT', ''))
    user_agent = parse(user_agent_string)
    
    # Extract device info
    device_type = 'mobile' if user_agent.is_mobile else ('tablet' if user_agent.is_tablet else 'desktop')
    browser = user_agent.browser.family
    browser_version = user_agent.browser.version_string
    operating_system = f"{user_agent.os.family} {user_agent.os.version_string}"
    
    # Create page view record
    page_view = PageView.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_key=session_key,
        url=url,
        path=path,
        query_string=query_string,
        method=data.get('method', request.method),
        page_title=data.get('page_title', ''),
        ip_address=get_client_ip(request),
        user_agent=user_agent_string,
        referrer=data.get('referrer', request.META.get('HTTP_REFERER', '')),
        device_type=device_type,
        browser=browser,
        browser_version=browser_version,
        operating_system=operating_system,
        country=data.get('country', ''),
        region=data.get('region', ''),
        city=data.get('city', ''),
        utm_source=data.get('utm_source', utm_source),
        utm_medium=data.get('utm_medium', utm_medium),
        utm_campaign=data.get('utm_campaign', utm_campaign),
        utm_term=data.get('utm_term', utm_term),
        utm_content=data.get('utm_content', utm_content),
        load_time=data.get('load_time')
    )
    
    # Set content object if provided
    if data.get('content_type') and data.get('object_id'):
        page_view.content_type = data['content_type']
        page_view.object_id = data['object_id']
        page_view.save(update_fields=['content_type', 'object_id'])
    
    # Update or create user session
    update_user_session(request, page_view)
    
    return page_view


def track_event(request, data=None):
    """Track a user event"""
    if data is None:
        data = {}
    
    # Get session
    session_key = request.session.session_key
    if not session_key:
        request.session.save()
        session_key = request.session.session_key
    
    # Create event record
    event = Event.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_key=session_key,
        category=data.get('category', Event.CATEGORY_OTHER),
        action=data.get('action', ''),
        label=data.get('label', ''),
        value=data.get('value'),
        data=data.get('data', {}),
        url=data.get('url', request.build_absolute_uri()),
        ip_address=get_client_ip(request),
        user_agent=data.get('user_agent', request.META.get('HTTP_USER_AGENT', ''))
    )
    
    # Set content object if provided
    if data.get('content_type') and data.get('object_id'):
        event.content_type = data['content_type']
        event.object_id = data['object_id']
        event.save(update_fields=['content_type', 'object_id'])
    
    # Update user session
    try:
        session = UserSession.objects.get(session_key=session_key)
        session.events = F('events') + 1
        session.is_bounce = False
        session.save(update_fields=['events', 'is_bounce'])
    except UserSession.DoesNotExist:
        pass
    
    return event


def track_search_query(request, data=None):
    """Track a search query"""
    if data is None:
        data = {}
    
    # Get session
    session_key = request.session.session_key
    if not session_key:
        request.session.save()
        session_key = request.session.session_key
    
    # Create search query record
    search_query = SearchQuery.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_key=session_key,
        query=data.get('query', ''),
        category=data.get('category', ''),
        filters=data.get('filters', {}),
        result_count=data.get('result_count', 0),
        ip_address=get_client_ip(request)
    )
    
    return search_query


def track_funnel_step(request, funnel, step_number, step_data=None):
    """Track a funnel step completion"""
    if step_data is None:
        step_data = {}
    
    # Get session
    session_key = request.session.session_key
    if not session_key:
        request.session.save()
        session_key = request.session.session_key
    
    user = request.user if request.user.is_authenticated else None
    
    # Get or create funnel entry
    try:
        if user:
            entry = FunnelEntry.objects.get(
                funnel=funnel,
                user=user,
                is_completed=False
            )
        else:
            entry = FunnelEntry.objects.get(
                funnel=funnel,
                session_key=session_key,
                user__isnull=True,
                is_completed=False
            )
    except FunnelEntry.DoesNotExist:
        # Create new entry
        entry = FunnelEntry.objects.create(
            funnel=funnel,
            user=user,
            session_key=session_key,
            current_step=0
        )
    except FunnelEntry.MultipleObjectsReturned:
        # Use the most recent entry
        if user:
            entry = FunnelEntry.objects.filter(
                funnel=funnel,
                user=user,
                is_completed=False
            ).order_by('-started_at').first()
        else:
            entry = FunnelEntry.objects.filter(
                funnel=funnel,
                session_key=session_key,
                user__isnull=True,
                is_completed=False
            ).order_by('-started_at').first()
    
    # Check if this step has already been recorded
    try:
        funnel_step = FunnelStep.objects.get(
            entry=entry,
            step_number=step_number
        )
        # Update existing step data
        funnel_step.data.update(step_data)
        funnel_step.save(update_fields=['data'])
    except FunnelStep.DoesNotExist:
        # Create new step
        step_name = funnel.steps[step_number]['name']
        funnel_step = FunnelStep.objects.create(
            entry=entry,
            step_number=step_number,
            step_name=step_name,
            data=step_data
        )
    
    # Update entry current step if this is a new step
    if step_number > entry.current_step:
        entry.current_step = step_number
        entry.save(update_fields=['current_step', 'updated_at'])
    
    # Check if funnel is complete
    if step_number == len(funnel.steps) - 1:
        entry.complete()
    
    return funnel_step


def update_user_session(request, page_view):
    """Update or create user session based on page view"""
    session_key = page_view.session_key
    
    try:
        # Update existing session
        session = UserSession.objects.get(session_key=session_key)
        session.page_views = F('page_views') + 1
        session.is_bounce = False
        session.exit_page = page_view.url
        session.end_time = timezone.now()
        session.save(update_fields=['page_views', 'is_bounce', 'exit_page', 'end_time'])
        session.update_duration()
    except UserSession.DoesNotExist:
        # Create new session
        user_agent = parse(page_view.user_agent)
        device_type = 'mobile' if user_agent.is_mobile else ('tablet' if user_agent.is_tablet else 'desktop')
        browser = user_agent.browser.family
        operating_system = f"{user_agent.os.family} {user_agent.os.version_string}"
        
        UserSession.objects.create(
            user=page_view.user,
            session_key=session_key,
            ip_address=page_view.ip_address,
            user_agent=page_view.user_agent,
            device_type=device_type,
            browser=browser,
            operating_system=operating_system,
            country=page_view.country,
            region=page_view.region,
            city=page_view.city,
            referrer=page_view.referrer,
            landing_page=page_view.url,
            exit_page=page_view.url,
            utm_source=page_view.utm_source,
            utm_medium=page_view.utm_medium,
            utm_campaign=page_view.utm_campaign,
            page_views=1,
            events=0,
            is_bounce=True
        )


def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def generate_report_data(report):
    """Generate report data based on report type and parameters"""
    # Get time range based on period
    start_date, end_date = get_report_date_range(report)
    
    # Generate data based on report type
    if report.type == Report.TYPE_SALES:
        return generate_sales_report(report, start_date, end_date)
    elif report.type == Report.TYPE_PRODUCTS:
        return generate_products_report(report, start_date, end_date)
    elif report.type == Report.TYPE_CUSTOMERS:
        return generate_customers_report(report, start_date, end_date)
    elif report.type == Report.TYPE_TRAFFIC:
        return generate_traffic_report(report, start_date, end_date)
    elif report.type == Report.TYPE_MARKETING:
        return generate_marketing_report(report, start_date, end_date)
    elif report.type == Report.TYPE_CUSTOM:
        return generate_custom_report(report, start_date, end_date)
    else:
        raise ValueError(f"Unknown report type: {report.type}")


def get_report_date_range(report):
    """Get date range for report based on period"""
    now = timezone.now()
    
    if report.period == Report.PERIOD_DAILY:
        # Last 24 hours
        start_date = now - timedelta(days=1)
        end_date = now
    
    elif report.period == Report.PERIOD_WEEKLY:
        # Last 7 days
        start_date = now - timedelta(days=7)
        end_date = now
    
    elif report.period == Report.PERIOD_MONTHLY:
        # Last 30 days
        start_date = now - timedelta(days=30)
        end_date = now
    
    elif report.period == Report.PERIOD_QUARTERLY:
        # Last 90 days
        start_date = now - timedelta(days=90)
        end_date = now
    
    elif report.period == Report.PERIOD_YEARLY:
        # Last 365 days
        start_date = now - timedelta(days=365)
        end_date = now
    
    elif report.period == Report.PERIOD_CUSTOM:
        # Custom date range
        if not report.start_date or not report.end_date:
            raise ValueError("Custom period requires start_date and end_date")
        
        start_date = timezone.make_aware(
            datetime.combine(report.start_date, datetime.min.time())
        )
        end_date = timezone.make_aware(
            datetime.combine(report.end_date, datetime.max.time())
        )
    
    else:
        raise ValueError(f"Unknown report period: {report.period}")
    
    return start_date, end_date


def generate_sales_report(report, start_date, end_date):
    """Generate sales report data"""
    from orders.models import Order, OrderItem
    
    # Get orders in date range
    orders = Order.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    # Total sales
    total_sales = orders.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Orders count
    orders_count = orders.count()
    
    # Average order value
    avg_order_value = total_sales / orders_count if orders_count > 0 else 0
    
    # Sales by date
    if report.period in [Report.PERIOD_DAILY, Report.PERIOD_WEEKLY]:
        # Daily breakdown
        sales_by_date = orders.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            sales=Sum('total_amount'),
            orders=Count('id')
        ).order_by('date')
    
    elif report.period == Report.PERIOD_MONTHLY:
        # Weekly breakdown
        from django.db.models.functions import TruncWeek
        sales_by_date = orders.annotate(
            date=TruncWeek('created_at')
        ).values('date').annotate(
            sales=Sum('total_amount'),
            orders=Count('id')
        ).order_by('date')
    
    else:
        # Monthly breakdown
        from django.db.models.functions import TruncMonth
        sales_by_date = orders.annotate(
            date=TruncMonth('created_at')
        ).values('date').annotate(
            sales=Sum('total_amount'),
            orders=Count('id')
        ).order_by('date')
    
    # Top products
    top_products = OrderItem.objects.filter(
        order__in=orders
    ).values(
        'product__id',
        'product__name'
    ).annotate(
        quantity=Sum('quantity'),
        revenue=Sum('price')
    ).order_by('-revenue')[:10]
    
    # Payment methods
    payment_methods = orders.values(
        'payment_method'
    ).annotate(
        count=Count('id'),
        total=Sum('total_amount')
    ).order_by('-total')
    
    # Status breakdown
    status_breakdown = orders.values(
        'status'
    ).annotate(
        count=Count('id'),
        total=Sum('total_amount')
    ).order_by('status')
    
    return {
        'total_sales': total_sales,
        'orders_count': orders_count,
        'avg_order_value': avg_order_value,
        'sales_by_date': list(sales_by_date),
        'top_products': list(top_products),
        'payment_methods': list(payment_methods),
        'status_breakdown': list(status_breakdown),
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'generated_at': timezone.now().isoformat()
    }


def generate_products_report(report, start_date, end_date):
    """Generate products report data"""
    from products.models import Product
    from orders.models import OrderItem
    
    # Get order items in date range
    order_items = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        order__created_at__lte=end_date
    )
    
    # Top selling products by quantity
    top_selling = order_items.values(
        'product__id',
        'product__name'
    ).annotate(
        quantity=Sum('quantity'),
        revenue=Sum('price'),
        orders=Count('order', distinct=True)
    ).order_by('-quantity')[:20]
    
    # Top revenue products
    top_revenue = order_items.values(
        'product__id',
        'product__name'
    ).annotate(
        quantity=Sum('quantity'),
        revenue=Sum('price'),
        orders=Count('order', distinct=True)
    ).order_by('-revenue')[:20]
    
    # Sales by category
    category_sales = order_items.values(
        'product__category__name'
    ).annotate(
        quantity=Sum('quantity'),
        revenue=Sum('price'),
        products=Count('product', distinct=True)
    ).order_by('-revenue')
    
    # Low stock products
    low_stock = Product.objects.filter(
        stock_quantity__lt=F('low_stock_threshold')
    ).values(
        'id',
        'name',
        'stock_quantity',
        'low_stock_threshold'
    ).order_by('stock_quantity')[:20]
    
    return {
        'top_selling': list(top_selling),
        'top_revenue': list(top_revenue),
        'category_sales': list(category_sales),
        'low_stock': list(low_stock),
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'generated_at': timezone.now().isoformat()
    }


def generate_customers_report(report, start_date, end_date):
    """Generate customers report data"""
    from django.contrib.auth import get_user_model
    from orders.models import Order
    
    User = get_user_model()
    
    # Get orders in date range
    orders = Order.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    # New customers
    new_customers = User.objects.filter(
        date_joined__gte=start_date,
        date_joined__lte=end_date
    ).count()
    
    # Active customers (placed at least one order)
    active_customers = orders.values('user').distinct().count()
    
    # Top customers by order count
    top_by_orders = orders.values(
        'user__id',
        'user__email',
        'user__first_name',
        'user__last_name'
    ).annotate(
        orders=Count('id'),
        total_spent=Sum('total_amount')
    ).order_by('-orders')[:20]
    
    # Top customers by spending
    top_by_spending = orders.values(
        'user__id',
        'user__email',
        'user__first_name',
        'user__last_name'
    ).annotate(
        orders=Count('id'),
        total_spent=Sum('total_amount')
    ).order_by('-total_spent')[:20]
    
    # Customer acquisition over time
    if report.period in [Report.PERIOD_DAILY, Report.PERIOD_WEEKLY]:
        # Daily breakdown
        acquisition = User.objects.filter(
            date_joined__gte=start_date,
            date_joined__lte=end_date
        ).annotate(
            date=TruncDate('date_joined')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
    else:
        # Monthly breakdown
        from django.db.models.functions import TruncMonth
        acquisition = User.objects.filter(
            date_joined__gte=start_date,
            date_joined__lte=end_date
        ).annotate(
            date=TruncMonth('date_joined')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
    
    return {
        'new_customers': new_customers,
        'active_customers': active_customers,
        'top_by_orders': list(top_by_orders),
        'top_by_spending': list(top_by_spending),
        'acquisition': list(acquisition),
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'generated_at': timezone.now().isoformat()
    }


def generate_traffic_report(report, start_date, end_date):
    """Generate traffic report data"""
    # Get page views in date range
    page_views = PageView.objects.filter(
        timestamp__gte=start_date,
        timestamp__lte=end_date
    )
    
    # Get sessions in date range
    sessions = UserSession.objects.filter(
        start_time__gte=start_date,
        start_time__lte=end_date
    )
    
    # Total page views
    total_views = page_views.count()
    
    # Unique visitors
    unique_visitors = page_views.values('session_key').distinct().count()
    
    # Average session duration
    avg_duration = sessions.exclude(
        duration__isnull=True
    ).aggregate(avg=Avg('duration'))['avg'] or timedelta(0)
    
    # Bounce rate
    bounce_count = sessions.filter(is_bounce=True).count()
    total_sessions = sessions.count()
    bounce_rate = (bounce_count / total_sessions * 100) if total_sessions > 0 else 0
    
    # Traffic over time
    if report.period in [Report.PERIOD_DAILY, Report.PERIOD_WEEKLY]:
        # Hourly breakdown
        from django.db.models.functions import TruncHour
        traffic_by_time = page_views.annotate(
            hour=TruncHour('timestamp')
        ).values('hour').annotate(
            views=Count('id'),
            visitors=Count('session_key', distinct=True)
        ).order_by('hour')
    else:
        # Daily breakdown
        traffic_by_time = page_views.annotate(
            date=TruncDate('timestamp')
        ).values('date').annotate(
            views=Count('id'),
            visitors=Count('session_key', distinct=True)
        ).order_by('date')
    
    # Top pages
    top_pages = page_views.values('path', 'page_title').annotate(
        views=Count('id'),
        visitors=Count('session_key', distinct=True)
    ).order_by('-views')[:20]
    
    # Traffic sources
    traffic_sources = page_views.exclude(referrer='').values('referrer').annotate(
        views=Count('id'),
        visitors=Count('session_key', distinct=True)
    ).order_by('-views')[:10]
    
    # Device breakdown
    device_breakdown = page_views.values('device_type').annotate(
        views=Count('id'),
        percentage=Count('id') * 100.0 / total_views if total_views > 0 else 0
    ).order_by('-views')
    
    # Browser breakdown
    browser_breakdown = page_views.values('browser').annotate(
        views=Count('id'),
        percentage=Count('id') * 100.0 / total_views if total_views > 0 else 0
    ).order_by('-views')
    
    return {
        'total_views': total_views,
        'unique_visitors': unique_visitors,
        'avg_duration': str(avg_duration),
        'bounce_rate': bounce_rate,
        'traffic_by_time': list(traffic_by_time),
        'top_pages': list(top_pages),
        'traffic_sources': list(traffic_sources),
        'device_breakdown': list(device_breakdown),
        'browser_breakdown': list(browser_breakdown),
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'generated_at': timezone.now().isoformat()
    }


def generate_marketing_report(report, start_date, end_date):
    """Generate marketing report data"""
    # Get page views in date range with UTM parameters
    page_views = PageView.objects.filter(
        timestamp__gte=start_date,
        timestamp__lte=end_date
    ).exclude(utm_source='')
    
    # Get sessions in date range with UTM parameters
    sessions = UserSession.objects.filter(
        start_time__gte=start_date,
        start_time__lte=end_date
    ).exclude(utm_source='')
    
    # Total marketing sessions
    total_marketing_sessions = sessions.count()
    
    # Campaign performance
    campaign_performance = sessions.values(
        'utm_source', 'utm_medium', 'utm_campaign'
    ).annotate(
        sessions=Count('id'),
        page_views=Sum('page_views'),
        avg_duration=Avg('duration'),
        bounce_rate=Sum(
            Case(When(is_bounce=True, then=1), default=0),
            output_field=models.FloatField()
        ) * 100.0 / Count('id')
    ).order_by('-sessions')
    
    # Get conversion data if available
    try:
        from orders.models import Order
        
        # Conversions by campaign
        conversions = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            session_key__in=sessions.values_list('session_key', flat=True)
        )
        
        campaign_conversions = sessions.values(
            'utm_source', 'utm_medium', 'utm_campaign'
        ).annotate(
            sessions=Count('id')
        ).annotate(
            conversions=Count(
                'session_key',
                filter=Q(session_key__in=conversions.values_list('session_key', flat=True))
            ),
            conversion_rate=Count(
                'session_key',
                filter=Q(session_key__in=conversions.values_list('session_key', flat=True))
            ) * 100.0 / Count('id'),
            revenue=Sum(
                'session_key__order__total_amount',
                filter=Q(session_key__in=conversions.values_list('session_key', flat=True))
            )
        ).order_by('-conversions')
        
    except (ImportError, RuntimeError):
        campaign_conversions = []
    
    # UTM source breakdown
    source_breakdown = page_views.values('utm_source').annotate(
        views=Count('id'),
        visitors=Count('session_key', distinct=True)
    ).order_by('-views')
    
    # UTM medium breakdown
    medium_breakdown = page_views.values('utm_medium').annotate(
        views=Count('id'),
        visitors=Count('session_key', distinct=True)
    ).order_by('-views')
    
    # UTM campaign breakdown
    campaign_breakdown = page_views.values('utm_campaign').annotate(
        views=Count('id'),
        visitors=Count('session_key', distinct=True)
    ).order_by('-views')
    
    return {
        'total_marketing_sessions': total_marketing_sessions,
        'campaign_performance': list(campaign_performance),
        'campaign_conversions': list(campaign_conversions) if campaign_conversions else [],
        'source_breakdown': list(source_breakdown),
        'medium_breakdown': list(medium_breakdown),
        'campaign_breakdown': list(campaign_breakdown),
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'generated_at': timezone.now().isoformat()
    }


def generate_custom_report(report, start_date, end_date):
    """Generate custom report data based on parameters"""
    # Get parameters
    params = report.parameters
    
    # Initialize data
    data = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'generated_at': timezone.now().isoformat()
    }
    
    # Add requested metrics based on parameters
    if params.get('include_sales', False):
        try:
            from orders.models import Order
            orders = Order.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            data['sales'] = {
                'total': orders.aggregate(total=Sum('total_amount'))['total'] or 0,
                'count': orders.count()
            }
        except (ImportError, RuntimeError):
            data['sales'] = {'error': 'Sales data not available'}
    
    if params.get('include_traffic', False):
        page_views = PageView.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        )
        data['traffic'] = {
            'total_views': page_views.count(),
            'unique_visitors': page_views.values('session_key').distinct().count()
        }
    
    if params.get('include_customers', False):
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            data['customers'] = {
                'new': User.objects.filter(
                    date_joined__gte=start_date,
                    date_joined__lte=end_date
                ).count()
            }
        except (ImportError, RuntimeError):
            data['customers'] = {'error': 'Customer data not available'}
    
    # Add any custom metrics defined in parameters
    for metric in params.get('custom_metrics', []):
        try:
            if metric['type'] == 'count':
                # Example: count of events with specific action
                if metric['source'] == 'events':
                    count = Event.objects.filter(
                        timestamp__gte=start_date,
                        timestamp__lte=end_date,
                        **metric.get('filters', {})
                    ).count()
                    data[metric['name']] = count
            elif metric['type'] == 'sum':
                # Example: sum of order values
                if metric['source'] == 'orders':
                    from orders.models import Order
                    sum_value = Order.objects.filter(
                        created_at__gte=start_date,
                        created_at__lte=end_date,
                        **metric.get('filters', {})
                    ).aggregate(sum=Sum(metric['field']))['sum'] or 0
                    data[metric['name']] = sum_value
        except Exception as e:
            data[f"{metric['name']}_error"] = str(e)
    
    return data