# analytics/urls.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
 PageViewViewSet, EventViewSet, SearchQueryViewSet, UserSessionViewSet,
 ReportViewSet, DashboardViewSet, DashboardWidgetViewSet, FunnelViewSet,
 AnalyticsDashboardViewSet
)

# Configure router for ViewSets
router = SimpleRouter()
router.register(r'page-views', PageViewViewSet, basename='page-view')
router.register(r'events', EventViewSet, basename='event')
router.register(r'search-queries', SearchQueryViewSet, basename='search-query')
router.register(r'sessions', UserSessionViewSet, basename='user-session')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'dashboards', DashboardViewSet, basename='dashboard')
router.register(r'widgets', DashboardWidgetViewSet, basename='dashboard-widget')
router.register(r'funnels', FunnelViewSet, basename='funnel')
router.register(r'overview', AnalyticsDashboardViewSet, basename='analytics-overview')

# URL patterns with versioning
app_name = 'analytics'

urlpatterns = [
 # Include router URLs
 path('', include(router.urls)),
]