# analytics/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import (
    PageView, Event, SearchQuery, UserSession,
    Report, Dashboard, DashboardWidget, Funnel, FunnelEntry, FunnelStep
)


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = [
        'path', 'user', 'session_key', 'device_type',
        'browser', 'country', 'timestamp'
    ]
    list_filter = ['device_type', 'browser', 'method', 'timestamp']
    search_fields = ['path', 'user__email', 'session_key', 'ip_address', 'country']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'session_key', 'url', 'path', 'page_title')
        }),
        ('Request Info', {
            'fields': ('query_string', 'method', 'content_type', 'object_id')
        }),
        ('Visitor Info', {
            'fields': ('ip_address', 'user_agent', 'referrer')
        }),
        ('Device Info', {
            'fields': ('device_type', 'browser', 'browser_version', 'operating_system')
        }),
        ('Location Info', {
            'fields': ('country', 'region', 'city')
        }),
        ('UTM Parameters', {
            'fields': ('utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content')
        }),
        ('Performance', {
            'fields': ('load_time',)
        }),
        ('Timestamps', {
            'fields': ('timestamp',)
        }),
    )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'category', 'action', 'label', 'user',
        'session_key', 'timestamp'
    ]
    list_filter = ['category', 'action', 'timestamp']
    search_fields = ['label', 'user__email', 'session_key', 'ip_address']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']
    fieldsets = (
        ('Event Info', {
            'fields': ('category', 'action', 'label', 'value')
        }),
        ('User Info', {
            'fields': ('user', 'session_key', 'ip_address', 'user_agent')
        }),
        ('Related Object', {
            'fields': ('content_type', 'object_id', 'url')
        }),
        ('Additional Data', {
            'fields': ('data',)
        }),
        ('Timestamps', {
            'fields': ('timestamp',)
        }),
    )


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = [
        'query', 'category', 'result_count', 'user',
        'session_key', 'timestamp'
    ]
    list_filter = ['category', 'result_count', 'timestamp']
    search_fields = ['query', 'user__email', 'session_key']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'session_key', 'start_time', 'duration',
        'page_views', 'events', 'is_bounce', 'device_type'
    ]
    list_filter = ['device_type', 'browser', 'is_bounce', 'start_time']
    search_fields = ['user__email', 'session_key', 'ip_address', 'country']
    date_hierarchy = 'start_time'
    readonly_fields = ['start_time', 'duration']
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'session_key', 'ip_address', 'user_agent')
        }),
        ('Session Timing', {
            'fields': ('start_time', 'end_time', 'duration')
        }),
        ('Device Info', {
            'fields': ('device_type', 'browser', 'operating_system')
        }),
        ('Location Info', {
            'fields': ('country', 'region', 'city')
        }),
        ('Referrer Info', {
            'fields': ('referrer', 'landing_page', 'exit_page')
        }),
        ('Session Activity', {
            'fields': ('page_views', 'events', 'is_bounce')
        }),
        ('UTM Parameters', {
            'fields': ('utm_source', 'utm_medium', 'utm_campaign')
        }),
    )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'type', 'period', 'created_by',
        'is_public', 'last_generated', 'created_at'
    ]
    list_filter = ['type', 'period', 'is_public', 'created_at']
    search_fields = ['name', 'description', 'created_by__email']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'last_generated']
    filter_horizontal = ['shared_with']
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Report Configuration', {
            'fields': ('type', 'period', 'start_date', 'end_date', 'parameters')
        }),
        ('Report Data', {
            'fields': ('data', 'last_generated')
        }),
        ('Sharing', {
            'fields': ('is_public', 'shared_with')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['generate_reports']
    
    def generate_reports(self, request, queryset):
        """Generate selected reports"""
        from .services import generate_report_data
        import traceback
        
        success_count = 0
        error_count = 0
        
        for report in queryset:
            try:
                data = generate_report_data(report)
                report.data = data
                report.last_generated = timezone.now()
                report.save(update_fields=['data', 'last_generated'])
                success_count += 1
            except Exception as e:
                error_count += 1
                self.message_user(
                    request,
                    f"Error generating report '{report.name}': {str(e)}",
                    level='ERROR'
                )
        
        if success_count:
            self.message_user(
                request,
                f"Successfully generated {success_count} report(s)."
            )
        
        if error_count:
            self.message_user(
                request,
                f"Failed to generate {error_count} report(s). See above for details.",
                level='WARNING'
            )
        
    generate_reports.short_description = "Generate selected reports"


class DashboardWidgetInline(admin.TabularInline):
    model = DashboardWidget
    extra = 1
    fields = ['name', 'type', 'configuration', 'report', 'position_x', 'position_y', 'width', 'height']


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_default', 'created_at']
    list_filter = ['is_default', 'created_at']
    search_fields = ['name', 'description', 'user__email']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    inlines = [DashboardWidgetInline]
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'user')
        }),
        ('Configuration', {
            'fields': ('layout', 'is_default')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'dashboard', 'type', 'report', 'position_x', 'position_y']
    list_filter = ['type', 'created_at']
    search_fields = ['name', 'dashboard__name', 'dashboard__user__email']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'dashboard', 'type')
        }),
        ('Configuration', {
            'fields': ('configuration', 'report')
        }),
        ('Layout', {
            'fields': ('position_x', 'position_y', 'width', 'height')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


class FunnelStepInline(admin.TabularInline):
    model = FunnelStep
    extra = 0
    fields = ['step_number', 'step_name', 'data', 'timestamp']
    readonly_fields = ['timestamp']
    ordering = ['step_number']


@admin.register(FunnelEntry)
class FunnelEntryAdmin(admin.ModelAdmin):
    list_display = [
        'funnel', 'user', 'session_key', 'current_step',
        'is_completed', 'started_at', 'completed_at'
    ]
    list_filter = ['funnel', 'is_completed', 'started_at']
    search_fields = ['user__email', 'session_key']
    date_hierarchy = 'started_at'
    readonly_fields = ['started_at', 'updated_at']
    inlines = [FunnelStepInline]
    fieldsets = (
        ('Basic Info', {
            'fields': ('funnel', 'user', 'session_key')
        }),
        ('Progress', {
            'fields': ('current_step', 'is_completed', 'completed_at')
        }),
        ('Data', {
            'fields': ('data',)
        }),
        ('Timestamps', {
            'fields': ('started_at', 'updated_at')
        }),
    )


@admin.register(Funnel)
class FunnelAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'created_by__email']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Configuration', {
            'fields': ('steps', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['activate_funnels', 'deactivate_funnels']
    
    def activate_funnels(self, request, queryset):
        """Activate selected funnels"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} funnel(s) activated successfully.")
    activate_funnels.short_description = "Activate selected funnels"
    
    def deactivate_funnels(self, request, queryset):
        """Deactivate selected funnels"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} funnel(s) deactivated successfully.")
    deactivate_funnels.short_description = "Deactivate selected funnels"