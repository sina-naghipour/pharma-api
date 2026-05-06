from django.contrib import admin
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    Review, ReviewImage, ReviewVote, ReviewComment,
    Question, Answer, AnswerVote
)


class ReviewImageInline(TabularInline):
    model = ReviewImage
    extra = 1


class ReviewCommentInline(TabularInline):
    model = ReviewComment
    extra = 0
    readonly_fields = ['user', 'is_staff_response', 'created_at']


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = [
        'id', 'product', 'user', 'rating', 'title',
        'status', 'is_verified_purchase', 'created_at'
    ]
    list_filter = [
        'status', 'rating', 'is_verified_purchase',
        'created_at', 'is_anonymous'
    ]
    search_fields = ['title', 'content', 'user__email', 'product__name']
    readonly_fields = [
        'helpful_votes', 'unhelpful_votes', 'created_at',
        'updated_at', 'moderated_at', 'moderated_by'
    ]
    inlines = [ReviewImageInline, ReviewCommentInline]
    actions = ['approve_reviews', 'reject_reviews']
    fieldsets = (
        ('Review Information', {
            'fields': ('product', 'user', 'rating', 'title', 'content')
        }),
        ('Status', {
            'fields': ('status', 'is_verified_purchase', 'is_anonymous')
        }),
        ('Helpfulness', {
            'fields': ('helpful_votes', 'unhelpful_votes')
        }),
        ('Moderation', {
            'fields': ('moderated_by', 'moderated_at', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def approve_reviews(self, request, queryset):
        """Approve selected reviews"""
        updated = queryset.update(
            status=Review.STATUS_APPROVED,
            moderated_by=request.user,
            moderated_at=timezone.now()
        )
        self.message_user(
            request,
            f"{updated} review(s) have been approved."
        )
    approve_reviews.short_description = "Approve selected reviews"
    
    def reject_reviews(self, request, queryset):
        """Reject selected reviews"""
        updated = queryset.update(
            status=Review.STATUS_REJECTED,
            moderated_by=request.user,
            moderated_at=timezone.now()
        )
        self.message_user(
            request,
            f"{updated} review(s) have been rejected."
        )
    reject_reviews.short_description = "Reject selected reviews"


@admin.register(ReviewComment)
class ReviewCommentAdmin(ModelAdmin):
    list_display = [
        'id', 'review', 'user', 'is_staff_response',
        'created_at'
    ]
    list_filter = ['is_staff_response', 'is_approved', 'created_at']
    search_fields = ['content', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_comments', 'disapprove_comments']
    
    def approve_comments(self, request, queryset):
        """Approve selected comments"""
        updated = queryset.update(is_approved=True)
        self.message_user(
            request,
            f"{updated} comment(s) have been approved."
        )
    approve_comments.short_description = "Approve selected comments"
    
    def disapprove_comments(self, request, queryset):
        """Disapprove selected comments"""
        updated = queryset.update(is_approved=False)
        self.message_user(
            request,
            f"{updated} comment(s) have been disapproved."
        )
    disapprove_comments.short_description = "Disapprove selected comments"


class AnswerInline(TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ['user', 'is_staff_answer', 'created_at']


@admin.register(Question)
class QuestionAdmin(ModelAdmin):
    list_display = [
        'id', 'product', 'user', 'status',
        'has_answer', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'is_anonymous']
    search_fields = ['question', 'user__email', 'product__name']
    readonly_fields = [
        'created_at', 'updated_at', 'moderated_at',
        'moderated_by', 'answer_count'
    ]
    inlines = [AnswerInline]
    actions = ['approve_questions', 'reject_questions']
    fieldsets = (
        ('Question Information', {
            'fields': ('product', 'user', 'question')
        }),
        ('Status', {
            'fields': ('status', 'is_anonymous')
        }),
        ('Moderation', {
            'fields': ('moderated_by', 'moderated_at', 'rejection_reason')
        }),
        ('Statistics', {
            'fields': ('answer_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def has_answer(self, obj):
        """Check if question has at least one answer"""
        return obj.has_answer
    has_answer.boolean = True
    
    def answer_count(self, obj):
        """Get number of answers"""
        return obj.answer_count
    
    def approve_questions(self, request, queryset):
        """Approve selected questions"""
        updated = queryset.update(
            status=Question.STATUS_APPROVED,
            moderated_by=request.user,
            moderated_at=timezone.now()
        )
        self.message_user(
            request,
            f"{updated} question(s) have been approved."
        )
    approve_questions.short_description = "Approve selected questions"
    
    def reject_questions(self, request, queryset):
        """Reject selected questions"""
        updated = queryset.update(
            status=Question.STATUS_REJECTED,
            moderated_by=request.user,
            moderated_at=timezone.now()
        )
        self.message_user(
            request,
            f"{updated} question(s) have been rejected."
        )
    reject_questions.short_description = "Reject selected questions"


@admin.register(Answer)
class AnswerAdmin(ModelAdmin):
    list_display = [
        'id', 'question', 'user', 'is_staff_answer',
        'created_at'
    ]
    list_filter = [
        'is_staff_answer', 'is_approved', 'created_at',
        'is_anonymous'
    ]
    search_fields = ['answer', 'user__email']
    readonly_fields = [
        'helpful_votes', 'unhelpful_votes', 'created_at',
        'updated_at'
    ]
    actions = ['approve_answers', 'disapprove_answers']
    fieldsets = (
        ('Answer Information', {
            'fields': ('question', 'user', 'answer')
        }),
        ('Status', {
            'fields': ('is_staff_answer', 'is_approved', 'is_anonymous')
        }),
        ('Helpfulness', {
            'fields': ('helpful_votes', 'unhelpful_votes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def approve_answers(self, request, queryset):
        """Approve selected answers"""
        updated = queryset.update(is_approved=True)
        self.message_user(
            request,
            f"{updated} answer(s) have been approved."
        )
    approve_answers.short_description = "Approve selected answers"
    
    def disapprove_answers(self, request, queryset):
        """Disapprove selected answers"""
        updated = queryset.update(is_approved=False)
        self.message_user(
            request,
            f"{updated} answer(s) have been disapproved."
        )
    disapprove_answers.short_description = "Disapprove selected answers"