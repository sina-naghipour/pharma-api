# analytics/filters.py
import django_filters
from django.db.models import Q
from .models import (
    PageView, Event, SearchQuery, UserSession,
    Report, Funnel
)


class PageViewFilter(django_filters.FilterSet):
    """Filter for PageView model"""
    url_contains = django_filters.CharFilter(field_name='url', lookup_expr='icontains')
    path_contains = django_filters.CharFilter(field_name='path', lookup_expr='icontains')
    start_date = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    end_date = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')
    device_type = django_filters.CharFilter(field_name='device_type')
    browser = django_filters.CharFilter(field_name='browser')
    country = django_filters.CharFilter(field_name='country')
    utm_source = django_filters.CharFilter(field_name='utm_source')
    utm_medium = django_filters.CharFilter(field_name='utm_medium')
    utm_campaign = django_filters.CharFilter(field_name='utm_campaign')
    
    class Meta:
        model = PageView
        fields = [
            'url_contains', 'path_contains', 'start_date', 'end_date',
            'device_type', 'browser', 'country', 'utm_source',
            'utm_medium', 'utm_campaign'
        ]


class EventFilter(django_filters.FilterSet):
    """Filter for Event model"""
    category = django_filters.ChoiceFilter(choices=Event.CATEGORY_CHOICES)
    action_contains = django_filters.CharFilter(field_name='action', lookup_expr='icontains')
    label_contains = django_filters.CharFilter(field_name='label', lookup_expr='icontains')
    start_date = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    end_date = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')
    
    class Meta:
        model = Event
        fields = [
            'category', 'action_contains', 'label_contains',
            'start_date', 'end_date'
        ]


class SearchQueryFilter(django_filters.FilterSet):
    """Filter for SearchQuery model"""
    query_contains = django_filters.CharFilter(field_name='query', lookup_expr='icontains')
    category = django_filters.CharFilter(field_name='category')
    min_results = django_filters.NumberFilter(field_name='result_count', lookup_expr='gte')
    max_results = django_filters.NumberFilter(field_name='result_count', lookup_expr='lte')
    start_date = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    end_date = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')
    
    class Meta:
        model = SearchQuery
        fields = [
            'query_contains', 'category', 'min_results', 'max_results',
            'start_date', 'end_date'
        ]


class UserSessionFilter(django_filters.FilterSet):
    """Filter for UserSession model"""
    start_date = django_filters.DateTimeFilter(field_name='start_time', lookup_expr='gte')
    end_date = django_filters.DateTimeFilter(field_name='start_time', lookup_expr='lte')
    min_duration = django_filters.DurationFilter(field_name='duration', lookup_expr='gte')
    max_duration = django_filters.DurationFilter(field_name='duration', lookup_expr='lte')
    min_page_views = django_filters.NumberFilter(field_name='page_views', lookup_expr='gte')
    device_type = django_filters.CharFilter(field_name='device_type')
    browser = django_filters.CharFilter(field_name='browser')
    country = django_filters.CharFilter(field_name='country')
    is_bounce = django_filters.BooleanFilter(field_name='is_bounce')
    utm_source = django_filters.CharFilter(field_name='utm_source')
    utm_medium = django_filters.CharFilter(field_name='utm_medium')
    utm_campaign = django_filters.CharFilter(field_name='utm_campaign')
    
    class Meta:
        model = UserSession
        fields = [
            'start_date', 'end_date', 'min_duration', 'max_duration',
            'min_page_views', 'device_type', 'browser', 'country',
            'is_bounce', 'utm_source', 'utm_medium', 'utm_campaign'
        ]


class ReportFilter(django_filters.FilterSet):
    """Filter for Report model"""
    type = django_filters.ChoiceFilter(choices=Report.TYPE_CHOICES)
    period = django_filters.ChoiceFilter(choices=Report.PERIOD_CHOICES)
    created_by = django_filters.UUIDFilter(field_name='created_by')
    is_public = django_filters.BooleanFilter(field_name='is_public')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    generated_after = django_filters.DateTimeFilter(field_name='last_generated', lookup_expr='gte')
    
    class Meta:
        model = Report
        fields = [
            'type', 'period', 'created_by', 'is_public',
            'created_after', 'created_before', 'generated_after'
        ]


class FunnelFilter(django_filters.FilterSet):
    """Filter for Funnel model"""
    created_by = django_filters.UUIDFilter(field_name='created_by')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Funnel
        fields = [
            'created_by', 'is_active', 'created_after', 'created_before'
        ]