import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone


class SupportCategory(models.Model):
    """Support ticket categories"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    icon = models.CharField(_('Icon'), max_length=50, blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    display_order = models.PositiveIntegerField(_('Display Order'), default=0)
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_categories',
        verbose_name=_('Assigned To')
    )
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = 'دسته پشتیبانی'
        verbose_name_plural = 'دسته‌های پشتیبانی'
        ordering = ['display_order', 'name']
        
    def __str__(self):
        return self.name


class SupportTicket(models.Model):
    """Customer support ticket model"""
    STATUS_OPEN = 'open'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_WAITING = 'waiting'
    STATUS_RESOLVED = 'resolved'
    STATUS_CLOSED = 'closed'
    
    STATUS_CHOICES = [
        (STATUS_OPEN, _('Open')),
        (STATUS_IN_PROGRESS, _('In Progress')),
        (STATUS_WAITING, _('Waiting for Customer')),
        (STATUS_RESOLVED, _('Resolved')),
        (STATUS_CLOSED, _('Closed')),
    ]
    
    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, _('Low')),
        (PRIORITY_MEDIUM, _('Medium')),
        (PRIORITY_HIGH, _('High')),
        (PRIORITY_URGENT, _('Urgent')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(_('Ticket Number'), max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets',
        verbose_name=_('User')
    )
    category = models.ForeignKey(
        SupportCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tickets',
        verbose_name=_('Category')
    )
    subject = models.CharField(_('Subject'), max_length=255)
    description = models.TextField(_('Description'))
    
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_tickets',
        verbose_name=_('Related Order')
    )
    
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_tickets',
        verbose_name=_('Related Product')
    )
    
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN
    )
    priority = models.CharField(
        _('Priority'),
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_MEDIUM
    )
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name=_('Assigned To')
    )
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    resolved_at = models.DateTimeField(_('Resolved At'), null=True, blank=True)
    closed_at = models.DateTimeField(_('Closed At'), null=True, blank=True)
    
    internal_notes = models.TextField(_('Internal Notes'), blank=True)
    
    satisfaction_rating = models.PositiveSmallIntegerField(
        _('Satisfaction Rating'),
        null=True,
        blank=True,
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]
    )
    feedback = models.TextField(_('Feedback'), blank=True)
    
    class Meta:
        verbose_name = 'تیکت پشتیبانی'
        verbose_name_plural = 'تیکت‌های پشتیبانی'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket_number']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        return f"{self.ticket_number} - {self.subject}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            date_str = timezone.now().strftime('%Y%m%d')
            last_ticket = SupportTicket.objects.filter(
                ticket_number__startswith=f'TKT-{date_str}'
            ).order_by('ticket_number').last()
            if last_ticket:
                seq = int(last_ticket.ticket_number.split('-')[-1]) + 1
            else:
                seq = 1
            self.ticket_number = f'TKT-{date_str}-{seq:05d}'
            
        if self._state.adding:
            pass
        else:
            old_ticket = SupportTicket.objects.get(pk=self.pk)
            if self.status == self.STATUS_RESOLVED and old_ticket.status != self.STATUS_RESOLVED:
                self.resolved_at = timezone.now()
            if self.status == self.STATUS_CLOSED and old_ticket.status != self.STATUS_CLOSED:
                self.closed_at = timezone.now()
            if self.status in [self.STATUS_OPEN, self.STATUS_IN_PROGRESS] and \
               old_ticket.status in [self.STATUS_RESOLVED, self.STATUS_CLOSED]:
                if self.status != self.STATUS_RESOLVED:
                    self.resolved_at = None
                if self.status != self.STATUS_CLOSED:
                    self.closed_at = None
        super().save(*args, **kwargs)
    
    @property
    def is_open(self):
        return self.status in [self.STATUS_OPEN, self.STATUS_IN_PROGRESS, self.STATUS_WAITING]
    
    @property
    def response_time(self):
        if not self.messages.exists():
            return None
        first_staff_msg = self.messages.filter(is_staff_reply=True).order_by('created_at').first()
        if not first_staff_msg:
            return None
        delta = first_staff_msg.created_at - self.created_at
        return delta
    
    @property
    def resolution_time(self):
        if not self.resolved_at:
            return None
        delta = self.resolved_at - self.created_at
        return delta


class TicketMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Ticket')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ticket_messages',
        verbose_name=_('User')
    )
    message = models.TextField(_('Message'))
    is_staff_reply = models.BooleanField(_('Staff Reply'), default=False)
    is_internal_note = models.BooleanField(_('Internal Note'), default=False)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    read_by_user = models.BooleanField(_('Read by User'), default=False)
    read_by_staff = models.BooleanField(_('Read by Staff'), default=False)
    
    class Meta:
        verbose_name = 'پیام تیکت'
        verbose_name_plural = 'پیام‌های تیکت'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['ticket']),
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        return f"Message in {self.ticket.ticket_number}"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            ticket = self.ticket
            if self.is_staff_reply and not self.is_internal_note:
                ticket.status = SupportTicket.STATUS_WAITING
                ticket.save(update_fields=['status', 'updated_at'])
            elif not self.is_staff_reply and not self.is_internal_note:
                if ticket.status in [SupportTicket.STATUS_WAITING, SupportTicket.STATUS_RESOLVED]:
                    ticket.status = SupportTicket.STATUS_OPEN
                    ticket.save(update_fields=['status', 'updated_at'])


class TicketAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name=_('Ticket')
    )
    message = models.ForeignKey(
        TicketMessage,
        on_delete=models.CASCADE,
        related_name='attachments',
        null=True,
        blank=True,
        verbose_name=_('Message')
    )
    file = models.FileField(_('File'), upload_to='support/attachments/%Y/%m/')
    filename = models.CharField(_('Filename'), max_length=255)
    file_type = models.CharField(_('File Type'), max_length=100)
    file_size = models.PositiveIntegerField(_('File Size'), help_text=_('Size in bytes'))
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ticket_attachments',
        verbose_name=_('Uploaded By')
    )
    is_staff_only = models.BooleanField(_('Staff Only'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = 'پیوست تیکت'
        verbose_name_plural = 'پیوست‌های تیکت'
        ordering = ['created_at']
        
    def __str__(self):
        return self.filename


class FAQ(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        SupportCategory,
        on_delete=models.CASCADE,
        related_name='faqs',
        verbose_name=_('Category')
    )
    question = models.CharField(_('Question'), max_length=255)
    answer = models.TextField(_('Answer'))
    
    is_published = models.BooleanField(_('Published'), default=True)
    display_order = models.PositiveIntegerField(_('Display Order'), default=0)
    
    view_count = models.PositiveIntegerField(_('View Count'), default=0)
    helpful_count = models.PositiveIntegerField(_('Helpful Count'), default=0)
    not_helpful_count = models.PositiveIntegerField(_('Not Helpful Count'), default=0)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    related_faqs = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=True,
        verbose_name=_('Related FAQs')
    )
    
    class Meta:
        verbose_name = 'سوال متداول'
        verbose_name_plural = 'سوالات متداول'
        ordering = ['category', 'display_order', 'question']
        
    def __str__(self):
        return self.question
    
    @property
    def helpfulness_score(self):
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return 0
        return (self.helpful_count / total_votes) * 100


class KnowledgeBaseCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    slug = models.SlugField(_('Slug'), max_length=100, unique=True)
    icon = models.CharField(_('Icon'), max_length=50, blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    display_order = models.PositiveIntegerField(_('Display Order'), default=0)
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Parent Category')
    )
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = 'دسته دانشنامه'
        verbose_name_plural = 'دسته‌های دانشنامه'
        ordering = ['display_order', 'name']
        
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class KnowledgeBaseArticle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('Title'), max_length=255)
    slug = models.SlugField(_('Slug'), max_length=255, unique=True)
    category = models.ForeignKey(
        KnowledgeBaseCategory,
        on_delete=models.CASCADE,
        related_name='articles',
        verbose_name=_('Category')
    )
    content = models.TextField(_('Content'))
    
    meta_description = models.TextField(_('Meta Description'), blank=True, max_length=160)
    keywords = models.CharField(_('Keywords'), max_length=255, blank=True)
    
    is_published = models.BooleanField(_('Published'), default=True)
    is_featured = models.BooleanField(_('Featured'), default=False)
    view_count = models.PositiveIntegerField(_('View Count'), default=0)
    helpful_count = models.PositiveIntegerField(_('Helpful Count'), default=0)
    not_helpful_count = models.PositiveIntegerField(_('Not Helpful Count'), default=0)
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='kb_articles',
        verbose_name=_('Author')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    published_at = models.DateTimeField(_('Published At'), null=True, blank=True)
    
    related_articles = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=True,
        verbose_name=_('Related Articles')
    )
    
    class Meta:
        verbose_name = 'مقاله دانشنامه'
        verbose_name_plural = 'مقالات دانشنامه'
        ordering = ['-is_featured', '-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_published']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def helpfulness_score(self):
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return 0
        return (self.helpful_count / total_votes) * 100
    
    @property
    def reading_time(self):
        words_per_minute = 200
        word_count = len(self.content.split())
        minutes = word_count / words_per_minute
        return max(1, round(minutes))


class ContactMessage(models.Model):
    STATUS_NEW = 'new'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_REPLIED = 'replied'
    STATUS_CLOSED = 'closed'
    
    STATUS_CHOICES = [
        (STATUS_NEW, _('New')),
        (STATUS_IN_PROGRESS, _('In Progress')),
        (STATUS_REPLIED, _('Replied')),
        (STATUS_CLOSED, _('Closed')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Name'), max_length=100)
    email = models.EmailField(_('Email'))
    phone = models.CharField(_('Phone'), max_length=20, blank=True)
    subject = models.CharField(_('Subject'), max_length=255)
    message = models.TextField(_('Message'))
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_messages',
        verbose_name=_('User')
    )
    
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW
    )
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_contact_messages',
        verbose_name=_('Assigned To')
    )
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    replied_at = models.DateTimeField(_('Replied At'), null=True, blank=True)
    
    internal_notes = models.TextField(_('Internal Notes'), blank=True)
    
    class Meta:
        verbose_name = 'پیام تماس'
        verbose_name_plural = 'پیام‌های تماس'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        return f"{self.name} - {self.subject}"


class ContactReply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_message = models.ForeignKey(
        ContactMessage,
        on_delete=models.CASCADE,
        related_name='replies',
        verbose_name=_('Contact Message')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contact_replies',
        verbose_name=_('User')
    )
    message = models.TextField(_('Message'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = 'پاسخ پیام تماس'
        verbose_name_plural = 'پاسخ‌های پیام تماس'
        ordering = ['created_at']
        
    def __str__(self):
        return f"Reply to {self.contact_message.name}"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            contact = self.contact_message
            contact.status = ContactMessage.STATUS_REPLIED
            contact.replied_at = timezone.now()
            contact.save(update_fields=['status', 'replied_at', 'updated_at'])