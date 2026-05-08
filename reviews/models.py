import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.utils import timezone


class Review(models.Model):
    """Product review model"""
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_APPROVED, _('Approved')),
        (STATUS_REJECTED, _('Rejected')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Product')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('User')
    )
    order_item = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        verbose_name=_('Order Item')
    )
    rating = models.PositiveSmallIntegerField(
        _('Rating'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(_('Title'), max_length=255)
    content = models.TextField(_('Content'))
    
    status = models.CharField(
        _('Status'),
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    is_verified_purchase = models.BooleanField(_('Verified Purchase'), default=False)
    is_anonymous = models.BooleanField(_('Anonymous'), default=False)
    
    helpful_votes = models.PositiveIntegerField(_('Helpful Votes'), default=0)
    unhelpful_votes = models.PositiveIntegerField(_('Unhelpful Votes'), default=0)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    moderated_at = models.DateTimeField(_('Moderated At'), null=True, blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_reviews',
        verbose_name=_('Moderated By')
    )
    rejection_reason = models.TextField(_('Rejection Reason'), blank=True)
    
    session_key = models.CharField(_('Session Key'), max_length=40, null=True, blank=True)
    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['rating']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Review by {self.user_display_name} for {self.product.name}"
    
    @property
    def user_display_name(self):
        if self.is_anonymous:
            return _('Anonymous')
        return self.user.get_full_name() or self.user.email.split('@')[0]
    
    @property
    def helpfulness_score(self):
        total_votes = self.helpful_votes + self.unhelpful_votes
        if total_votes == 0:
            return 0
        return (self.helpful_votes / total_votes) * 100
    
    def moderate(self, status, moderator, reason=None):
        self.status = status
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        if status == self.STATUS_REJECTED and reason:
            self.rejection_reason = reason
        self.save(update_fields=[
            'status', 'moderated_by', 'moderated_at',
            'rejection_reason', 'updated_at'
        ])


class ReviewImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Review')
    )
    image = models.ImageField(
        _('Image'),
        upload_to='reviews/%Y/%m/'
    )
    caption = models.CharField(_('Caption'), max_length=255, blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = 'تصویر نظر'
        verbose_name_plural = 'تصاویر نظرات'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Image for review {self.review.id}"


class ReviewVote(models.Model):
    VOTE_HELPFUL = 'helpful'
    VOTE_UNHELPFUL = 'unhelpful'
    
    VOTE_CHOICES = [
        (VOTE_HELPFUL, _('Helpful')),
        (VOTE_UNHELPFUL, _('Unhelpful')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name=_('Review')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_votes',
        verbose_name=_('User'),
        null=True,   # allow null for anonymous votes
        blank=True,
    )
    vote = models.CharField(
        _('Vote'),
        max_length=10,
        choices=VOTE_CHOICES
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    session_key = models.CharField(_('Session Key'), max_length=40, null=True, blank=True)
    
    class Meta:
        verbose_name = 'رأی نظر'
        verbose_name_plural = 'آراء نظرات'
        # Remove unique_together – uniqueness is handled in the view
        indexes = [
            models.Index(fields=['review']),
            models.Index(fields=['user']),
            models.Index(fields=['vote']),
            models.Index(fields=['session_key']),
        ]
    
    def __str__(self):
        if self.user:
            return f"{self.user.email} voted {self.vote} on review {self.review.id}"
        else:
            return f"Anonymous session voted {self.vote} on review {self.review.id}"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        old_vote = None
        if not is_new:
            try:
                old_vote = ReviewVote.objects.get(pk=self.pk).vote
            except ReviewVote.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if is_new:
            if self.vote == self.VOTE_HELPFUL:
                self.review.helpful_votes += 1
            else:
                self.review.unhelpful_votes += 1
        elif old_vote != self.vote:
            if self.vote == self.VOTE_HELPFUL:
                self.review.helpful_votes += 1
                self.review.unhelpful_votes -= 1
            else:
                self.review.helpful_votes -= 1
                self.review.unhelpful_votes += 1
        self.review.save(update_fields=['helpful_votes', 'unhelpful_votes', 'updated_at'])
    
    def delete(self, *args, **kwargs):
        if self.vote == self.VOTE_HELPFUL:
            self.review.helpful_votes = max(0, self.review.helpful_votes - 1)
        else:
            self.review.unhelpful_votes = max(0, self.review.unhelpful_votes - 1)
        self.review.save(update_fields=['helpful_votes', 'unhelpful_votes', 'updated_at'])
        super().delete(*args, **kwargs)

class ReviewComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Review')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_comments',
        verbose_name=_('User')
    )
    content = models.TextField(_('Content'))
    is_staff_response = models.BooleanField(_('Staff Response'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    is_approved = models.BooleanField(_('Approved'), default=False)
    session_key = models.CharField(_('Session Key'), max_length=40, null=True, blank=True)

    class Meta:
        verbose_name = 'نظر روی نظر'
        verbose_name_plural = 'نظرات روی نظر'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['review']),
            models.Index(fields=['user']),
            models.Index(fields=['is_staff_response']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.user.email} on review {self.review.id}"


class Question(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_ANSWERED = 'answered'
    STATUS_REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_APPROVED, _('Approved')),
        (STATUS_ANSWERED, _('Answered')),
        (STATUS_REJECTED, _('Rejected')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_('Product')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_('User')
    )
    question = models.TextField(_('Question'))
    status = models.CharField(
        _('Status'),
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    is_anonymous = models.BooleanField(_('Anonymous'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    moderated_at = models.DateTimeField(_('Moderated At'), null=True, blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_questions',
        verbose_name=_('Moderated By')
    )
    rejection_reason = models.TextField(_('Rejection Reason'), blank=True)
    
    class Meta:
        verbose_name = 'پرسش'
        verbose_name_plural = 'پرسش‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Question about {self.product.name} by {self.user_display_name}"
    
    @property
    def user_display_name(self):
        if self.is_anonymous:
            return _('Anonymous')
        return self.user.get_full_name() or self.user.email.split('@')[0]
    
    @property
    def has_answer(self):
        return self.answers.exists()
    
    @property
    def answer_count(self):
        return self.answers.count()
    
    def moderate(self, status, moderator, reason=None):
        self.status = status
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        if status == self.STATUS_REJECTED and reason:
            self.rejection_reason = reason
        self.save(update_fields=[
            'status', 'moderated_by', 'moderated_at',
            'rejection_reason', 'updated_at'
        ])


class Answer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name=_('Question')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name=_('User')
    )
    answer = models.TextField(_('Answer'))
    is_staff_answer = models.BooleanField(_('Staff Answer'), default=False)
    is_anonymous = models.BooleanField(_('Anonymous'), default=False)
    helpful_votes = models.PositiveIntegerField(_('Helpful Votes'), default=0)
    unhelpful_votes = models.PositiveIntegerField(_('Unhelpful Votes'), default=0)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    is_approved = models.BooleanField(_('Approved'), default=True)
    
    class Meta:
        verbose_name = 'پاسخ'
        verbose_name_plural = 'پاسخ‌ها'
        ordering = ['-is_staff_answer', '-helpful_votes', 'created_at']
        indexes = [
            models.Index(fields=['question']),
            models.Index(fields=['user']),
            models.Index(fields=['is_staff_answer']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Answer to question {self.question.id} by {self.user_display_name}"
    
    @property
    def user_display_name(self):
        if self.is_anonymous:
            return _('Anonymous')
        if self.is_staff_answer:
            return f"{self.user.get_full_name()} ({_('Staff')})"
        return self.user.get_full_name() or self.user.email.split('@')[0]
    
    @property
    def helpfulness_score(self):
        total_votes = self.helpful_votes + self.unhelpful_votes
        if total_votes == 0:
            return 0
        return (self.helpful_votes / total_votes) * 100
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.is_approved:
            self.question.status = Question.STATUS_ANSWERED
            self.question.save(update_fields=['status', 'updated_at'])


class AnswerVote(models.Model):
    VOTE_HELPFUL = 'helpful'
    VOTE_UNHELPFUL = 'unhelpful'
    
    VOTE_CHOICES = [
        (VOTE_HELPFUL, _('Helpful')),
        (VOTE_UNHELPFUL, _('Unhelpful')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name=_('Answer')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='answer_votes',
        verbose_name=_('User')
    )
    vote = models.CharField(
        _('Vote'),
        max_length=10,
        choices=VOTE_CHOICES
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = 'رأی پاسخ'
        verbose_name_plural = 'آراء پاسخ‌ها'
        unique_together = ['answer', 'user']
        indexes = [
            models.Index(fields=['answer']),
            models.Index(fields=['user']),
            models.Index(fields=['vote']),
        ]
    
    def __str__(self):
        return f"{self.user.email} voted {self.vote} on answer {self.answer.id}"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        old_vote = None
        if not is_new:
            try:
                old_vote = AnswerVote.objects.get(pk=self.pk).vote
            except AnswerVote.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if is_new:
            if self.vote == self.VOTE_HELPFUL:
                self.answer.helpful_votes += 1
            else:
                self.answer.unhelpful_votes += 1
        elif old_vote != self.vote:
            if self.vote == self.VOTE_HELPFUL:
                self.answer.helpful_votes += 1
                self.answer.unhelpful_votes -= 1
            else:
                self.answer.helpful_votes -= 1
                self.answer.unhelpful_votes += 1
        self.answer.save(update_fields=['helpful_votes', 'unhelpful_votes', 'updated_at'])
    
    def delete(self, *args, **kwargs):
        if self.vote == self.VOTE_HELPFUL:
            self.answer.helpful_votes = max(0, self.answer.helpful_votes - 1)
        else:
            self.answer.unhelpful_votes = max(0, self.answer.unhelpful_votes - 1)
        self.answer.save(update_fields=['helpful_votes', 'unhelpful_votes', 'updated_at'])
        super().delete(*args, **kwargs)