# support/filters.py
import django_filters
from django.db.models import Q
from .models import (
    SupportTicket, FAQ, KnowledgeBaseArticle, ContactMessage
)


class SupportTicketFilter(django_filters.FilterSet):
    """Filter for SupportTicket model"""
    status = django_filters.ChoiceFilter(choices=SupportTicket.STATUS_CHOICES)
    priority = django_filters.ChoiceFilter(choices=SupportTicket.PRIORITY_CHOICES)
    category = django_filters.UUIDFilter(field_name='category')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = django_filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = django_filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    assigned_to = django_filters.UUIDFilter(field_name='assigned_to')
    unassigned = django_filters.BooleanFilter(field_name='assigned_to', lookup_expr='isnull')
    
    class Meta:
        model = SupportTicket
        fields = [
            'status', 'priority', 'category',
            'created_after', 'created_before',
            'updated_after', 'updated_before',
            'assigned_to', 'unassigned'
        ]


class FAQFilter(django_filters.FilterSet):
    """Filter for FAQ model"""
    category = django_filters.UUIDFilter(field_name='category')
    is_published = django_filters.BooleanFilter(field_name='is_published')
    
    class Meta:
        model = FAQ
        fields = ['category', 'is_published']


class KnowledgeBaseArticleFilter(django_filters.FilterSet):
    """Filter for KnowledgeBaseArticle model"""
    category = django_filters.UUIDFilter(field_name='category')
    is_published = django_filters.BooleanFilter(field_name='is_published')
    is_featured = django_filters.BooleanFilter(field_name='is_featured')
    author = django_filters.UUIDFilter(field_name='author')
    published_after = django_filters.DateTimeFilter(field_name='published_at', lookup_expr='gte')
    published_before = django_filters.DateTimeFilter(field_name='published_at', lookup_expr='lte')
    
    class Meta:
        model = KnowledgeBaseArticle
        fields = [
            'category', 'is_published', 'is_featured',
            'author', 'published_after', 'published_before'
        ]


class ContactMessageFilter(django_filters.FilterSet):
    """Filter for ContactMessage model"""
    status = django_filters.ChoiceFilter(choices=ContactMessage.STATUS_CHOICES)
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    assigned_to = django_filters.UUIDFilter(field_name='assigned_to')
    unassigned = django_filters.BooleanFilter(field_name='assigned_to', lookup_expr='isnull')
    
    class Meta:
        model = ContactMessage
        fields = [
            'status', 'created_after', 'created_before',
            'assigned_to', 'unassigned'
        ]