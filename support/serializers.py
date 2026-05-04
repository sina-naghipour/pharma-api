# support/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import (
    SupportCategory, SupportTicket, TicketMessage, TicketAttachment,
    FAQ, KnowledgeBaseCategory, KnowledgeBaseArticle,
    ContactMessage, ContactReply
)


class SupportCategorySerializer(serializers.ModelSerializer):
    """Serializer for support categories"""
    
    class Meta:
        model = SupportCategory
        fields = [
            'id', 'name', 'description', 'icon', 
            'is_active', 'display_order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TicketAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for ticket attachments"""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TicketAttachment
        fields = [
            'id', 'file', 'file_url', 'filename', 'file_type',
            'file_size', 'uploaded_by', 'is_staff_only', 'created_at'
        ]
        read_only_fields = ['id', 'file_url', 'file_size', 'uploaded_by', 'created_at']
    
    def get_file_url(self, obj):
        """Get file URL"""
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class TicketMessageSerializer(serializers.ModelSerializer):
    """Serializer for ticket messages"""
    user_name = serializers.SerializerMethodField()
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = TicketMessage
        fields = [
            'id', 'ticket', 'user', 'user_name', 'message',
            'is_staff_reply', 'is_internal_note', 'created_at',
            'updated_at', 'read_by_user', 'read_by_staff', 'attachments'
        ]
        read_only_fields = [
            'id', 'user', 'user_name', 'is_staff_reply', 'created_at',
            'updated_at', 'read_by_user', 'read_by_staff'
        ]
    
    def get_user_name(self, obj):
        """Get user name"""
        if obj.user.get_full_name():
            return obj.user.get_full_name()
        return obj.user.email


class TicketMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ticket messages"""
    attachments = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = TicketMessage
        fields = ['message', 'is_internal_note', 'attachments']
    
    def create(self, validated_data):
        """Create ticket message with attachments"""
        attachments = validated_data.pop('attachments', [])
        ticket = self.context['ticket']
        user = self.context['request'].user
        
        # Set staff reply flag
        is_staff_reply = user.is_staff
        
        # Create message
        message = TicketMessage.objects.create(
            ticket=ticket,
            user=user,
            message=validated_data['message'],
            is_staff_reply=is_staff_reply,
            is_internal_note=validated_data.get('is_internal_note', False),
            read_by_staff=is_staff_reply,
            read_by_user=not is_staff_reply
        )
        
        # Create attachments
        for file in attachments:
            TicketAttachment.objects.create(
                ticket=ticket,
                message=message,
                file=file,
                filename=file.name,
                file_type=file.content_type,
                file_size=file.size,
                uploaded_by=user,
                is_staff_only=validated_data.get('is_internal_note', False)
            )
        
        return message


class SupportTicketListSerializer(serializers.ModelSerializer):
    """Serializer for listing support tickets"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    unread_messages = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'ticket_number', 'subject', 'status',
            'priority', 'category', 'category_name',
            'created_at', 'updated_at', 'assigned_to',
            'assigned_to_name', 'unread_messages'
        ]
        read_only_fields = fields
    
    def get_assigned_to_name(self, obj):
        """Get assigned user name"""
        if obj.assigned_to:
            if obj.assigned_to.get_full_name():
                return obj.assigned_to.get_full_name()
            return obj.assigned_to.email
        return None
    
    def get_unread_messages(self, obj):
        """Get count of unread messages"""
        request = self.context.get('request')
        if not request or not request.user:
            return 0
            
        if request.user.is_staff:
            return obj.messages.filter(read_by_staff=False).count()
        else:
            return obj.messages.filter(read_by_user=False).count()


class SupportTicketDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed view of support tickets"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    messages = TicketMessageSerializer(many=True, read_only=True)
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    response_time = serializers.SerializerMethodField()
    resolution_time = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'ticket_number', 'user', 'category', 'category_name',
            'subject', 'description', 'order', 'product',
            'status', 'priority', 'assigned_to', 'assigned_to_name',
            'created_at', 'updated_at', 'resolved_at', 'closed_at',
            'internal_notes', 'satisfaction_rating', 'feedback',
            'messages', 'attachments', 'is_open',
            'response_time', 'resolution_time'
        ]
        read_only_fields = [
            'id', 'ticket_number', 'user', 'created_at', 'updated_at',
            'resolved_at', 'closed_at', 'category_name', 'assigned_to_name',
            'is_open', 'response_time', 'resolution_time'
        ]
    
    def get_assigned_to_name(self, obj):
        """Get assigned user name"""
        if obj.assigned_to:
            if obj.assigned_to.get_full_name():
                return obj.assigned_to.get_full_name()
            return obj.assigned_to.email
        return None
    
    def get_response_time(self, obj):
        """Format response time"""
        response_time = obj.response_time
        if not response_time:
            return None
        
        hours = response_time.total_seconds() / 3600
        if hours < 1:
            minutes = int(response_time.total_seconds() / 60)
            return f"{minutes} minutes"
        else:
            return f"{hours:.1f} hours"
    
    def get_resolution_time(self, obj):
        """Format resolution time"""
        resolution_time = obj.resolution_time
        if not resolution_time:
            return None
        
        days = resolution_time.days
        hours = resolution_time.seconds / 3600
        
        if days > 0:
            return f"{days} days {int(hours)} hours"
        else:
            return f"{hours:.1f} hours"


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating support tickets"""
    attachments = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = SupportTicket
        fields = [
            'category', 'subject', 'description',
            'order', 'product', 'priority', 'attachments'
        ]
    
    def create(self, validated_data):
        """Create ticket with attachments"""
        attachments = validated_data.pop('attachments', [])
        user = self.context['request'].user
        
        # Create ticket
        ticket = SupportTicket.objects.create(
            user=user,
            **validated_data
        )
        
        # Auto-assign based on category if available
        if ticket.category and ticket.category.assigned_to:
            ticket.assigned_to = ticket.category.assigned_to
            ticket.save(update_fields=['assigned_to'])
        
        # Create attachments
        for file in attachments:
            TicketAttachment.objects.create(
                ticket=ticket,
                file=file,
                filename=file.name,
                file_type=file.content_type,
                file_size=file.size,
                uploaded_by=user
            )
        
        return ticket


class SupportTicketUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating support tickets"""
    
    class Meta:
        model = SupportTicket
        fields = [
            'category', 'subject', 'description',
            'status', 'priority', 'assigned_to',
            'internal_notes'
        ]
    
    def validate_status(self, value):
        """Validate status changes"""
        user = self.context['request'].user
        
        # Only staff can change to certain statuses
        if not user.is_staff and value in [
            SupportTicket.STATUS_RESOLVED,
            SupportTicket.STATUS_CLOSED
        ]:
            raise serializers.ValidationError(
                _("You don't have permission to set this status.")
            )
        
        return value
    
    def validate_assigned_to(self, value):
        """Validate assigned_to changes"""
        user = self.context['request'].user
        
        # Only staff can assign tickets
        if not user.is_staff and value is not None:
            raise serializers.ValidationError(
                _("You don't have permission to assign tickets.")
            )
        
        return value


class TicketSatisfactionSerializer(serializers.ModelSerializer):
    """Serializer for ticket satisfaction rating"""
    
    class Meta:
        model = SupportTicket
        fields = ['satisfaction_rating', 'feedback']


class FAQSerializer(serializers.ModelSerializer):
    """Serializer for FAQs"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    helpfulness_score = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = FAQ
        fields = [
            'id', 'category', 'category_name', 'question', 'answer',
            'is_published', 'display_order', 'view_count',
            'helpful_count', 'not_helpful_count', 'helpfulness_score',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'view_count', 'helpful_count', 'not_helpful_count',
            'helpfulness_score', 'created_at', 'updated_at'
        ]


class FAQHelpfulnessSerializer(serializers.Serializer):
    """Serializer for FAQ helpfulness voting"""
    helpful = serializers.BooleanField(required=True)


class KnowledgeBaseCategorySerializer(serializers.ModelSerializer):
    """Serializer for knowledge base categories"""
    article_count = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeBaseCategory
        fields = [
            'id', 'name', 'description', 'slug', 'icon',
            'is_active', 'display_order', 'parent',
            'created_at', 'updated_at', 'article_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'article_count']
    
    def get_article_count(self, obj):
        """Get number of published articles in this category"""
        return obj.articles.filter(is_published=True).count()


class KnowledgeBaseArticleListSerializer(serializers.ModelSerializer):
    """Serializer for listing knowledge base articles"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    author_name = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeBaseArticle
        fields = [
            'id', 'title', 'slug', 'category', 'category_name',
            'is_published', 'is_featured', 'view_count',
            'author', 'author_name', 'published_at', 'reading_time'
        ]
        read_only_fields = fields
    
    def get_author_name(self, obj):
        """Get author name"""
        if obj.author:
            if obj.author.get_full_name():
                return obj.author.get_full_name()
            return obj.author.email
        return None


class KnowledgeBaseArticleDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed view of knowledge base articles"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    author_name = serializers.SerializerMethodField()
    helpfulness_score = serializers.IntegerField(read_only=True)
    related_articles = KnowledgeBaseArticleListSerializer(many=True, read_only=True)
    
    class Meta:
        model = KnowledgeBaseArticle
        fields = [
            'id', 'title', 'slug', 'category', 'category_name',
            'content', 'meta_description', 'keywords',
            'is_published', 'is_featured', 'view_count',
            'helpful_count', 'not_helpful_count', 'helpfulness_score',
            'author', 'author_name', 'created_at', 'updated_at',
            'published_at', 'reading_time', 'related_articles'
        ]
        read_only_fields = [
            'id', 'view_count', 'helpful_count', 'not_helpful_count',
            'helpfulness_score', 'created_at', 'updated_at',
            'published_at', 'reading_time'
        ]
    
    def get_author_name(self, obj):
        """Get author name"""
        if obj.author:
            if obj.author.get_full_name():
                return obj.author.get_full_name()
            return obj.author.email
        return None


class KnowledgeBaseArticleCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating knowledge base articles"""
    
    class Meta:
        model = KnowledgeBaseArticle
        fields = [
            'title', 'slug', 'category', 'content',
            'meta_description', 'keywords',
            'is_published', 'is_featured', 'related_articles'
        ]
    
    def validate_slug(self, value):
        """Validate slug uniqueness"""
        instance = self.instance
        if instance and instance.slug == value:
            return value
            
        if KnowledgeBaseArticle.objects.filter(slug=value).exists():
            raise serializers.ValidationError(
                _("An article with this slug already exists.")
            )
        return value


class ArticleHelpfulnessSerializer(serializers.Serializer):
    """Serializer for article helpfulness voting"""
    helpful = serializers.BooleanField(required=True)


class ContactMessageSerializer(serializers.ModelSerializer):
    """Serializer for contact messages"""
    
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'phone', 'subject',
            'message', 'user', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'created_at']
    
    def create(self, validated_data):
        """Create contact message and link to user if authenticated"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        return super().create(validated_data)


class ContactMessageDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed view of contact messages"""
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'phone', 'subject',
            'message', 'user', 'status', 'assigned_to',
            'created_at', 'updated_at', 'replied_at',
            'internal_notes', 'replies'
        ]
        read_only_fields = [
            'id', 'name', 'email', 'phone', 'subject',
            'message', 'user', 'created_at', 'updated_at',
            'replied_at', 'replies'
        ]
    
    def get_replies(self, obj):
        """Get replies to contact message"""
        replies = obj.replies.all().order_by('created_at')
        return ContactReplySerializer(replies, many=True).data


class ContactReplySerializer(serializers.ModelSerializer):
    """Serializer for contact message replies"""
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ContactReply
        fields = [
            'id', 'contact_message', 'user', 'user_name',
            'message', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'user_name', 'created_at']
    
    def get_user_name(self, obj):
        """Get user name"""
        if obj.user.get_full_name():
            return obj.user.get_full_name()
        return obj.user.email


class ContactReplyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating contact message replies"""
    
    class Meta:
        model = ContactReply
        fields = ['message']
    
    def create(self, validated_data):
        """Create contact reply"""
        contact_message = self.context['contact_message']
        user = self.context['request'].user
        
        return ContactReply.objects.create(
            contact_message=contact_message,
            user=user,
            message=validated_data['message']
        )