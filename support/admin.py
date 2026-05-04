# support/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import (
    SupportCategory, SupportTicket, TicketMessage, TicketAttachment,
    FAQ, KnowledgeBaseCategory, KnowledgeBaseArticle,
    ContactMessage, ContactReply
)


@admin.register(SupportCategory)
class SupportCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'display_order', 'assigned_to']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ['user', 'created_at', 'is_staff_reply', 'read_by_user', 'read_by_staff']
    fields = ['user', 'message', 'is_staff_reply', 'is_internal_note', 'created_at', 'read_by_user', 'read_by_staff']


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    readonly_fields = ['uploaded_by', 'created_at', 'file_size', 'file_type']
    fields = ['file', 'filename', 'uploaded_by', 'is_staff_only', 'created_at', 'file_size', 'file_type']


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = [
        'ticket_number', 'subject', 'user', 'category',
        'status', 'priority', 'assigned_to', 'created_at'
    ]
    list_filter = ['status', 'priority', 'category', 'created_at']
    search_fields = ['ticket_number', 'subject', 'description', 'user__email']
    readonly_fields = [
        'ticket_number', 'created_at', 'updated_at',
        'resolved_at', 'closed_at'
    ]
    inlines = [TicketMessageInline, TicketAttachmentInline]
    fieldsets = (
        ('Ticket Information', {
            'fields': ('ticket_number', 'user', 'category', 'subject', 'description')
        }),
        ('Related Items', {
            'fields': ('order', 'product')
        }),
        ('Status', {
            'fields': ('status', 'priority', 'assigned_to')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at', 'closed_at')
        }),
        ('Feedback', {
            'fields': ('satisfaction_rating', 'feedback')
        }),
        ('Internal', {
            'fields': ('internal_notes',)
        }),
    )
    actions = ['mark_in_progress', 'mark_resolved', 'mark_closed']
    
    def mark_in_progress(self, request, queryset):
        """Mark selected tickets as in progress"""
        updated = queryset.update(status=SupportTicket.STATUS_IN_PROGRESS)
        self.message_user(request, f"{updated} ticket(s) marked as in progress.")
    mark_in_progress.short_description = "Mark selected tickets as in progress"
    
    def mark_resolved(self, request, queryset):
        """Mark selected tickets as resolved"""
        updated = queryset.update(
            status=SupportTicket.STATUS_RESOLVED,
            resolved_at=timezone.now()
        )
        self.message_user(request, f"{updated} ticket(s) marked as resolved.")
    mark_resolved.short_description = "Mark selected tickets as resolved"
    
    def mark_closed(self, request, queryset):
        """Mark selected tickets as closed"""
        updated = queryset.update(
            status=SupportTicket.STATUS_CLOSED,
            closed_at=timezone.now()
        )
        self.message_user(request, f"{updated} ticket(s) marked as closed.")
    mark_closed.short_description = "Mark selected tickets as closed"


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = [
        'ticket', 'user', 'is_staff_reply',
        'is_internal_note', 'created_at'
    ]
    list_filter = ['is_staff_reply', 'is_internal_note', 'created_at']
    search_fields = ['message', 'ticket__ticket_number', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = [
        'filename', 'ticket', 'file_type',
        'file_size', 'uploaded_by', 'created_at'
    ]
    list_filter = ['file_type', 'is_staff_only', 'created_at']
    search_fields = ['filename', 'ticket__ticket_number', 'uploaded_by__email']
    readonly_fields = ['file_size', 'file_type', 'created_at']


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = [
        'question', 'category', 'is_published',
        'display_order', 'view_count', 'helpful_count'
    ]
    list_filter = ['is_published', 'category', 'created_at']
    search_fields = ['question', 'answer']
    readonly_fields = ['view_count', 'helpful_count', 'not_helpful_count', 'created_at', 'updated_at']
    filter_horizontal = ['related_faqs']
    fieldsets = (
        ('FAQ Information', {
            'fields': ('category', 'question', 'answer')
        }),
        ('Publishing', {
            'fields': ('is_published', 'display_order')
        }),
        ('Statistics', {
            'fields': ('view_count', 'helpful_count', 'not_helpful_count')
        }),
        ('Related', {
            'fields': ('related_faqs',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(KnowledgeBaseCategory)
class KnowledgeBaseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'is_active', 'display_order']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'description', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['display_order', 'name']


@admin.register(KnowledgeBaseArticle)
class KnowledgeBaseArticleAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'slug', 'category', 'is_published',
        'is_featured', 'view_count', 'author'
    ]
    list_filter = ['is_published', 'is_featured', 'category', 'created_at']
    search_fields = ['title', 'content', 'meta_description', 'keywords']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = [
        'view_count', 'helpful_count', 'not_helpful_count',
        'created_at', 'updated_at', 'published_at'
    ]
    filter_horizontal = ['related_articles']
    fieldsets = (
        ('Article Information', {
            'fields': ('title', 'slug', 'category', 'content')
        }),
        ('SEO', {
            'fields': ('meta_description', 'keywords')
        }),
        ('Publishing', {
            'fields': ('is_published', 'is_featured', 'author')
        }),
        ('Statistics', {
            'fields': ('view_count', 'helpful_count', 'not_helpful_count')
        }),
        ('Related', {
            'fields': ('related_articles',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at')
        }),
    )


class ContactReplyInline(admin.TabularInline):
    model = ContactReply
    extra = 0
    readonly_fields = ['user', 'created_at']
    fields = ['user', 'message', 'created_at']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'email', 'subject', 'status',
        'assigned_to', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at', 'updated_at', 'replied_at']
    inlines = [ContactReplyInline]
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone', 'user')
        }),
        ('Message', {
            'fields': ('subject', 'message')
        }),
        ('Status', {
            'fields': ('status', 'assigned_to')
        }),
        ('Internal', {
            'fields': ('internal_notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'replied_at')
        }),
    )
    actions = ['mark_in_progress', 'mark_replied', 'mark_closed']
    
    def mark_in_progress(self, request, queryset):
        """Mark selected messages as in progress"""
        updated = queryset.update(status=ContactMessage.STATUS_IN_PROGRESS)
        self.message_user(request, f"{updated} message(s) marked as in progress.")
    mark_in_progress.short_description = "Mark selected messages as in progress"
    
    def mark_replied(self, request, queryset):
        """Mark selected messages as replied"""
        updated = queryset.update(
            status=ContactMessage.STATUS_REPLIED,
            replied_at=timezone.now()
        )
        self.message_user(request, f"{updated} message(s) marked as replied.")
    mark_replied.short_description = "Mark selected messages as replied"
    
    def mark_closed(self, request, queryset):
        """Mark selected messages as closed"""
        updated = queryset.update(status=ContactMessage.STATUS_CLOSED)
        self.message_user(request, f"{updated} message(s) marked as closed.")
    mark_closed.short_description = "Mark selected messages as closed"