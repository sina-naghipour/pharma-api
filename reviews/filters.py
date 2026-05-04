# reviews/filters.py
import django_filters
from django.db.models import Q
from .models import Review, Question


class ReviewFilter(django_filters.FilterSet):
    """Filter for Review model"""
    product = django_filters.UUIDFilter(field_name='product')
    user = django_filters.CharFilter(method='filter_user')
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')
    status = django_filters.ChoiceFilter(
        choices=Review.STATUS_CHOICES,
        field_name='status'
    )
    verified_purchase = django_filters.BooleanFilter(field_name='is_verified_purchase')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Review
        fields = [
            'product', 'user', 'rating', 'status',
            'is_verified_purchase', 'min_rating', 'max_rating',
            'created_after', 'created_before'
        ]
    
    def filter_user(self, queryset, name, value):
        """Filter by user (supports 'me' for current user)"""
        if value == 'me' and self.request and self.request.user.is_authenticated:
            return queryset.filter(user=self.request.user)
        return queryset.filter(user__id=value)


class QuestionFilter(django_filters.FilterSet):
    """Filter for Question model"""
    product = django_filters.UUIDFilter(field_name='product')
    user = django_filters.CharFilter(method='filter_user')
    status = django_filters.ChoiceFilter(
        choices=Question.STATUS_CHOICES,
        field_name='status'
    )
    has_answers = django_filters.BooleanFilter(method='filter_has_answers')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Question
        fields = [
            'product', 'user', 'status', 'has_answers',
            'created_after', 'created_before'
        ]
    
    def filter_user(self, queryset, name, value):
        """Filter by user (supports 'me' for current user)"""
        if value == 'me' and self.request and self.request.user.is_authenticated:
            return queryset.filter(user=self.request.user)
        return queryset.filter(user__id=value)
    
    def filter_has_answers(self, queryset, name, value):
        """Filter questions with or without answers"""
        if value:
            return queryset.filter(answers__is_approved=True).distinct()
        else:
            return queryset.filter(~Q(answers__is_approved=True)).distinct()