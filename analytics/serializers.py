# analytics/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from .models import (
    PageView, Event, SearchQuery, UserSession,
    Report, Dashboard, DashboardWidget, Funnel, FunnelEntry, FunnelStep
)


class PageViewSerializer(serializers.ModelSerializer):
    """Serializer for page views"""
    
    class Meta:
        model = PageView
        fields = [
            'id', 'user', 'session_key', 'url', 'path',
            'query_string', 'method', 'page_title', 'content_type',
            'object_id', 'ip_address', 'user_agent', 'referrer',
            'device_type', 'browser', 'browser_version', 'operating_system',
            'country', 'region', 'city', 'utm_source', 'utm_medium',
            'utm_campaign', 'utm_term', 'utm_content', 'timestamp',
            'load_time'
        ]
        read_only_fields = ['id', 'timestamp']


class EventSerializer(serializers.ModelSerializer):
    """Serializer for events"""
    
    class Meta:
        model = Event
        fields = [
            'id', 'user', 'session_key', 'category', 'action',
            'label', 'value', 'data', 'content_type', 'object_id',
            'url', 'ip_address', 'user_agent', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class SearchQuerySerializer(serializers.ModelSerializer):
    """Serializer for search queries"""
    
    class Meta:
        model = SearchQuery
        fields = [
            'id', 'user', 'session_key', 'query', 'category',
            'filters', 'result_count', 'timestamp', 'ip_address'
        ]
        read_only_fields = ['id', 'timestamp']


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for user sessions"""
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'user', 'session_key', 'start_time', 'end_time',
            'duration', 'ip_address', 'user_agent', 'device_type',
            'browser', 'operating_system', 'country', 'region', 'city',
            'referrer', 'landing_page', 'exit_page', 'page_views',
            'events', 'is_bounce', 'utm_source', 'utm_medium', 'utm_campaign'
        ]
        read_only_fields = [
            'id', 'start_time', 'duration'
        ]


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """Serializer for dashboard widgets"""
    
    class Meta:
        model = DashboardWidget
        fields = [
            'id', 'dashboard', 'name', 'type', 'configuration',
            'report', 'position_x', 'position_y', 'width', 'height',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DashboardSerializer(serializers.ModelSerializer):
    """Serializer for dashboards"""
    widgets = DashboardWidgetSerializer(many=True, read_only=True)
    
    class Meta:
        model = Dashboard
        fields = [
            'id', 'name', 'description', 'user', 'layout',
            'is_default', 'created_at', 'updated_at', 'widgets'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DashboardCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating dashboards"""
    
    class Meta:
        model = Dashboard
        fields = ['name', 'description', 'layout', 'is_default']
    
    def create(self, validated_data):
        """Create dashboard and set user"""
        user = self.context['request'].user
        return Dashboard.objects.create(user=user, **validated_data)


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for reports"""
    
    class Meta:
        model = Report
        fields = [
            'id', 'name', 'description', 'type', 'period',
            'start_date', 'end_date', 'parameters', 'data',
            'last_generated', 'created_by', 'is_public',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_generated', 'created_at', 'updated_at']


class ReportCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating reports"""
    
    class Meta:
        model = Report
        fields = [
            'name', 'description', 'type', 'period',
            'start_date', 'end_date', 'parameters', 'is_public'
        ]
    
    def validate(self, data):
        """Validate report data"""
        # Validate date range for custom periods
        if data.get('period') == Report.PERIOD_CUSTOM:
            if not data.get('start_date'):
                raise serializers.ValidationError({
                    'start_date': _("Start date is required for custom periods.")
                })
            if not data.get('end_date'):
                raise serializers.ValidationError({
                    'end_date': _("End date is required for custom periods.")
                })
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError({
                    'end_date': _("End date must be after start date.")
                })
        
        return data
    
    def create(self, validated_data):
        """Create report and set created_by"""
        user = self.context['request'].user
        return Report.objects.create(created_by=user, **validated_data)


class FunnelStepSerializer(serializers.ModelSerializer):
    """Serializer for funnel steps"""
    
    class Meta:
        model = FunnelStep
        fields = [
            'id', 'entry', 'step_number', 'step_name',
            'data', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class FunnelEntrySerializer(serializers.ModelSerializer):
    """Serializer for funnel entries"""
    steps = FunnelStepSerializer(many=True, read_only=True)
    
    class Meta:
        model = FunnelEntry
        fields = [
            'id', 'funnel', 'user', 'session_key',
            'current_step', 'is_completed', 'completed_at',
            'data', 'started_at', 'updated_at', 'steps'
        ]
        read_only_fields = ['id', 'started_at', 'updated_at']


class FunnelSerializer(serializers.ModelSerializer):
    """Serializer for funnels"""
    
    class Meta:
        model = Funnel
        fields = [
            'id', 'name', 'description', 'created_by',
            'steps', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FunnelCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating funnels"""
    
    class Meta:
        model = Funnel
        fields = ['name', 'description', 'steps', 'is_active']
    
    def validate_steps(self, value):
        """Validate funnel steps"""
        if not isinstance(value, list):
            raise serializers.ValidationError(_("Steps must be a list."))
        
        if len(value) < 2:
            raise serializers.ValidationError(_("Funnel must have at least 2 steps."))
        
        # Check that each step has required fields
        for i, step in enumerate(value):
            if not isinstance(step, dict):
                raise serializers.ValidationError(
                    _("Step {0} must be an object.").format(i+1)
                )
            
            if 'name' not in step:
                raise serializers.ValidationError(
                    _("Step {0} must have a name.").format(i+1)
                )
            
            if 'event' not in step:
                raise serializers.ValidationError(
                    _("Step {0} must have an event.").format(i+1)
                )
        
        return value
    
    def create(self, validated_data):
        """Create funnel and set created_by"""
        user = self.context['request'].user
        return Funnel.objects.create(created_by=user, **validated_data)


class AnalyticsSummarySerializer(serializers.Serializer):
    """Serializer for analytics summary data"""
    time_period = serializers.CharField()
    page_views = serializers.IntegerField()
    unique_visitors = serializers.IntegerField()
    average_session_duration = serializers.DurationField()
    bounce_rate = serializers.FloatField()
    top_pages = serializers.ListField(child=serializers.DictField())
    top_referrers = serializers.ListField(child=serializers.DictField())
    device_breakdown = serializers.DictField()
    browser_breakdown = serializers.DictField()