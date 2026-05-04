# analytics/views.py
from django.db.models import Count, Avg, Sum, F, Q, ExpressionWrapper, fields
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from rest_framework import viewsets, status, mixins, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from datetime import timedelta, datetime
import json

from .models import (
    PageView, Event, SearchQuery, UserSession,
    Report, Dashboard, DashboardWidget, Funnel, FunnelEntry, FunnelStep
)
from .serializers import (
    PageViewSerializer, EventSerializer, SearchQuerySerializer, UserSessionSerializer,
    ReportSerializer, ReportCreateUpdateSerializer, DashboardSerializer,
    DashboardCreateUpdateSerializer, DashboardWidgetSerializer, FunnelSerializer,
    FunnelCreateUpdateSerializer, FunnelEntrySerializer, FunnelStepSerializer,
    AnalyticsSummarySerializer
)
from .permissions import IsOwnerOrAdmin, IsCreatorOrAdmin, IsReportAccessible
from .filters import (
    PageViewFilter, EventFilter, SearchQueryFilter, UserSessionFilter,
    ReportFilter, FunnelFilter
)
from .services import (
    generate_report_data, track_page_view, track_event,
    track_search_query, track_funnel_step
)


class PageViewViewSet(viewsets.ModelViewSet):
    """ViewSet for page views (admin only)"""
    queryset = PageView.objects.all()
    serializer_class = PageViewSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PageViewFilter
    search_fields = ['path', 'page_title', 'ip_address', 'country', 'city']
    ordering_fields = ['timestamp', 'load_time']
    ordering = ['-timestamp']
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def track(self, request):
        """Track a page view"""
        serializer = PageViewSerializer(data=request.data)
        if serializer.is_valid():
            # Use tracking service
            page_view = track_page_view(
                request=request,
                data=serializer.validated_data
            )
            return Response(
                PageViewSerializer(page_view).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get page view summary statistics"""
        # Get time range from query params (default to last 30 days)
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get page views in time range
        queryset = PageView.objects.filter(timestamp__gte=start_date)
        
        # Total page views
        total_views = queryset.count()
        
        # Views by date
        views_by_date = queryset.annotate(
            date=TruncDate('timestamp')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Top pages
        top_pages = queryset.values('path').annotate(
            views=Count('id')
        ).order_by('-views')[:10]
        
        # Top referrers
        top_referrers = queryset.exclude(referrer='').values('referrer').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Device breakdown
        device_breakdown = queryset.values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Browser breakdown
        browser_breakdown = queryset.values('browser').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return Response({
            'total_views': total_views,
            'views_by_date': list(views_by_date),
            'top_pages': list(top_pages),
            'top_referrers': list(top_referrers),
            'device_breakdown': list(device_breakdown),
            'browser_breakdown': list(browser_breakdown),
        })


class EventViewSet(viewsets.ModelViewSet):
    """ViewSet for events (admin only)"""
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EventFilter
    search_fields = ['category', 'action', 'label']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def track(self, request):
        """Track an event"""
        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            # Use tracking service
            event = track_event(
                request=request,
                data=serializer.validated_data
            )
            return Response(
                EventSerializer(event).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get event summary statistics"""
        # Get time range from query params (default to last 30 days)
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get events in time range
        queryset = Event.objects.filter(timestamp__gte=start_date)
        
        # Events by category
        events_by_category = queryset.values('category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Top actions
        top_actions = queryset.values('action').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Events over time
        events_by_date = queryset.annotate(
            date=TruncDate('timestamp')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return Response({
            'total_events': queryset.count(),
            'events_by_category': list(events_by_category),
            'top_actions': list(top_actions),
            'events_by_date': list(events_by_date),
        })


class SearchQueryViewSet(viewsets.ModelViewSet):
    """ViewSet for search queries (admin only)"""
    queryset = SearchQuery.objects.all()
    serializer_class = SearchQuerySerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SearchQueryFilter
    search_fields = ['query', 'category']
    ordering_fields = ['timestamp', 'result_count']
    ordering = ['-timestamp']
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def track(self, request):
        """Track a search query"""
        serializer = SearchQuerySerializer(data=request.data)
        if serializer.is_valid():
            # Use tracking service
            search_query = track_search_query(
                request=request,
                data=serializer.validated_data
            )
            return Response(
                SearchQuerySerializer(search_query).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular search queries"""
        # Get time range from query params (default to last 30 days)
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get popular queries
        popular_queries = SearchQuery.objects.filter(
            timestamp__gte=start_date
        ).values('query').annotate(
            count=Count('id'),
            avg_results=Avg('result_count')
        ).order_by('-count')[:20]
        
        # Get zero-result queries
        zero_results = SearchQuery.objects.filter(
            timestamp__gte=start_date,
            result_count=0
        ).values('query').annotate(
            count=Count('id')
        ).order_by('-count')[:20]
        
        return Response({
            'popular_queries': list(popular_queries),
            'zero_result_queries': list(zero_results),
        })


class UserSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for user sessions (admin only)"""
    queryset = UserSession.objects.all()
    serializer_class = UserSessionSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = UserSessionFilter
    search_fields = ['user__email', 'ip_address', 'country', 'city']
    ordering_fields = ['start_time', 'duration', 'page_views']
    ordering = ['-start_time']
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get session summary statistics"""
        # Get time range from query params (default to last 30 days)
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get sessions in time range
        queryset = UserSession.objects.filter(start_time__gte=start_date)
        
        # Total sessions
        total_sessions = queryset.count()
        
        # Average session duration
        avg_duration = queryset.exclude(
            duration__isnull=True
        ).aggregate(avg=Avg('duration'))
        
        # Bounce rate
        bounce_count = queryset.filter(is_bounce=True).count()
        bounce_rate = (bounce_count / total_sessions * 100) if total_sessions > 0 else 0
        
        # Sessions by date
        sessions_by_date = queryset.annotate(
            date=TruncDate('start_time')
        ).values('date').annotate(
            count=Count('id'),
            avg_pages=Avg('page_views'),
            avg_duration=Avg('duration')
        ).order_by('date')
        
        # Device breakdown
        device_breakdown = queryset.values('device_type').annotate(
            count=Count('id'),
            percentage=Count('id') * 100.0 / total_sessions
        ).order_by('-count')
        
        # Traffic sources
        traffic_sources = queryset.exclude(utm_source='').values(
            'utm_source', 'utm_medium'
        ).annotate(
            count=Count('id'),
            percentage=Count('id') * 100.0 / total_sessions
        ).order_by('-count')[:10]
        
        return Response({
            'total_sessions': total_sessions,
            'avg_duration': avg_duration['avg'],
            'bounce_rate': bounce_rate,
            'sessions_by_date': list(sessions_by_date),
            'device_breakdown': list(device_breakdown),
            'traffic_sources': list(traffic_sources),
        })


class DashboardViewSet(viewsets.ModelViewSet):
    """ViewSet for user dashboards"""
    queryset = Dashboard.objects.all()
    serializer_class = DashboardSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-is_default', 'name']
    
    def get_queryset(self):
        """Filter dashboards to user's own unless admin"""
        if self.request.user.is_staff:
            return Dashboard.objects.all()
        return Dashboard.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['create', 'update', 'partial_update']:
            return DashboardCreateUpdateSerializer
        return DashboardSerializer
    
    @action(detail=False, methods=['get'])
    def default(self, request):
        """Get user's default dashboard"""
        try:
            dashboard = Dashboard.objects.get(user=request.user, is_default=True)
            serializer = self.get_serializer(dashboard)
            return Response(serializer.data)
        except Dashboard.DoesNotExist:
            # Create a default dashboard if none exists
            dashboard = Dashboard.objects.create(
                user=request.user,
                name=_("Default Dashboard"),
                is_default=True
            )
            serializer = self.get_serializer(dashboard)
            return Response(serializer.data)


class DashboardWidgetViewSet(viewsets.ModelViewSet):
    """ViewSet for dashboard widgets"""
    queryset = DashboardWidget.objects.all()
    serializer_class = DashboardWidgetSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        """Filter widgets to user's own dashboards unless admin"""
        if self.request.user.is_staff:
            return DashboardWidget.objects.all()
        return DashboardWidget.objects.filter(dashboard__user=self.request.user)
    
    def perform_create(self, serializer):
        """Check dashboard ownership before creating widget"""
        dashboard = serializer.validated_data['dashboard']
        if dashboard.user != self.request.user and not self.request.user.is_staff:
            raise serializers.ValidationError({
                'dashboard': _("You don't have permission to add widgets to this dashboard.")
            })
        serializer.save()


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for analytics reports"""
    queryset = Report.objects.all()
    permission_classes = [IsAuthenticated, IsCreatorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReportFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'type', 'created_at', 'last_generated']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['create', 'update', 'partial_update']:
            return ReportCreateUpdateSerializer
        return ReportSerializer
    
    def get_queryset(self):
        """Filter reports based on user permissions"""
        user = self.request.user
        
        # Admins can see all reports
        if user.is_staff:
            return Report.objects.all()
        
        # Regular users can see their own reports and public reports
        return Report.objects.filter(
            Q(created_by=user) | 
            Q(is_public=True) |
            Q(shared_with=user)
        ).distinct()
    
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generate report data"""
        report = self.get_object()
        
        try:
            # Use report generation service
            data = generate_report_data(report)
            
            # Update report with new data
            report.data = data
            report.last_generated = timezone.now()
            report.save(update_fields=['data', 'last_generated'])
            
            return Response({
                'status': 'success',
                'message': _('Report generated successfully'),
                'data': data
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Share report with other users"""
        report = self.get_object()
        user_ids = request.data.get('users', [])
        
        # Check if user is the creator or admin
        if report.created_by != request.user and not request.user.is_staff:
            return Response({
                'status': 'error',
                'message': _('You do not have permission to share this report')
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Add users to shared_with
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(id__in=user_ids)
        
        report.shared_with.add(*users)
        
        return Response({
            'status': 'success',
            'message': _('Report shared successfully')
        })


class FunnelViewSet(viewsets.ModelViewSet):
    """ViewSet for conversion funnels"""
    queryset = Funnel.objects.all()
    permission_classes = [IsAuthenticated, IsCreatorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FunnelFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['create', 'update', 'partial_update']:
            return FunnelCreateUpdateSerializer
        return FunnelSerializer
    
    def get_queryset(self):
        """Filter funnels to active ones or all for admin"""
        if self.request.user.is_staff:
            return Funnel.objects.all()
        return Funnel.objects.filter(
            Q(created_by=self.request.user) | Q(is_active=True)
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def track_step(self, request, pk=None):
        """Track a funnel step completion"""
        funnel = self.get_object()
        
        # Get step data
        step_number = request.data.get('step_number')
        step_data = request.data.get('data', {})
        
        if step_number is None:
            return Response({
                'error': _('step_number is required')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            step_number = int(step_number)
        except ValueError:
            return Response({
                'error': _('step_number must be an integer')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate step number
        if step_number < 0 or step_number >= len(funnel.steps):
            return Response({
                'error': _('Invalid step_number')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Track the funnel step
        funnel_step = track_funnel_step(
            request=request,
            funnel=funnel,
            step_number=step_number,
            step_data=step_data
        )
        
        return Response(
            FunnelStepSerializer(funnel_step).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def analysis(self, request, pk=None):
        """Get funnel analysis data"""
        funnel = self.get_object()
        
        # Get time range from query params (default to last 30 days)
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get funnel entries in time range
        entries = FunnelEntry.objects.filter(
            funnel=funnel,
            started_at__gte=start_date
        )
        
        # Total entries
        total_entries = entries.count()
        
        # Completion rate
        completed = entries.filter(is_completed=True).count()
        completion_rate = (completed / total_entries * 100) if total_entries > 0 else 0
        
        # Step conversion rates
        step_counts = []
        for i in range(len(funnel.steps)):
            step_count = FunnelStep.objects.filter(
                entry__funnel=funnel,
                entry__started_at__gte=start_date,
                step_number=i
            ).count()
            
            step_counts.append({
                'step': i,
                'name': funnel.steps[i]['name'],
                'count': step_count,
                'rate': (step_count / total_entries * 100) if total_entries > 0 else 0
            })
        
        # Conversion over time
        conversion_by_date = entries.annotate(
            date=TruncDate('started_at')
        ).values('date').annotate(
            entries=Count('id'),
            completions=Count('id', filter=Q(is_completed=True)),
            rate=Count('id', filter=Q(is_completed=True)) * 100.0 / Count('id')
        ).order_by('date')
        
        return Response({
            'total_entries': total_entries,
            'completed': completed,
            'completion_rate': completion_rate,
            'steps': step_counts,
            'conversion_by_date': list(conversion_by_date),
        })


class AnalyticsDashboardViewSet(viewsets.ViewSet):
    """ViewSet for analytics dashboard data"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get analytics summary data"""
        # Get time range from query params (default to last 30 days)
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Page view stats
        page_views = PageView.objects.filter(timestamp__gte=start_date).count()
        unique_visitors = PageView.objects.filter(timestamp__gte=start_date).values(
            'session_key'
        ).distinct().count()
        
        # Session stats
        sessions = UserSession.objects.filter(start_time__gte=start_date)
        avg_duration = sessions.exclude(
            duration__isnull=True
        ).aggregate(avg=Avg('duration'))['avg'] or timedelta(0)
        
        bounce_count = sessions.filter(is_bounce=True).count()
        total_sessions = sessions.count()
        bounce_rate = (bounce_count / total_sessions * 100) if total_sessions > 0 else 0
        
        # Top pages
        top_pages = PageView.objects.filter(timestamp__gte=start_date).values(
            'path', 'page_title'
        ).annotate(
            views=Count('id')
        ).order_by('-views')[:5]
        
        # Top referrers
        top_referrers = PageView.objects.filter(
            timestamp__gte=start_date
        ).exclude(
            referrer=''
        ).values('referrer').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Device breakdown
        device_breakdown = PageView.objects.filter(
            timestamp__gte=start_date
        ).values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Browser breakdown
        browser_breakdown = PageView.objects.filter(
            timestamp__gte=start_date
        ).values('browser').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return Response({
            'time_period': f"Last {days} days",
            'page_views': page_views,
            'unique_visitors': unique_visitors,
            'average_session_duration': avg_duration,
            'bounce_rate': bounce_rate,
            'top_pages': list(top_pages),
            'top_referrers': list(top_referrers),
            'device_breakdown': {item['device_type']: item['count'] for item in device_breakdown},
            'browser_breakdown': {item['browser']: item['count'] for item in browser_breakdown},
        })