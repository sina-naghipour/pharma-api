# support/views.py
from django.db.models import Q, Count, F, Sum
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, mixins, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    SupportCategory, SupportTicket, TicketMessage, TicketAttachment,
    FAQ, KnowledgeBaseCategory, KnowledgeBaseArticle,
    ContactMessage, ContactReply
)
from .serializers import (
    SupportCategorySerializer, SupportTicketListSerializer, 
    SupportTicketDetailSerializer, SupportTicketCreateSerializer,
    SupportTicketUpdateSerializer, TicketMessageSerializer,
    TicketMessageCreateSerializer, TicketAttachmentSerializer,
    TicketSatisfactionSerializer, FAQSerializer, FAQHelpfulnessSerializer,
    KnowledgeBaseCategorySerializer, KnowledgeBaseArticleListSerializer,
    KnowledgeBaseArticleDetailSerializer, KnowledgeBaseArticleCreateUpdateSerializer,
    ArticleHelpfulnessSerializer, ContactMessageSerializer,
    ContactMessageDetailSerializer, ContactReplySerializer,
    ContactReplyCreateSerializer
)
from .permissions import (
    IsOwnerOrStaffOrReadOnly, IsStaffOrCreateOnly, IsOwnerOrStaff
)
from .filters import (
    SupportTicketFilter, FAQFilter, KnowledgeBaseArticleFilter,
    ContactMessageFilter
)


class SupportCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for support categories"""
    queryset = SupportCategory.objects.all()
    serializer_class = SupportCategorySerializer
    permission_classes = [IsStaffOrCreateOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'display_order']
    ordering = ['display_order', 'name']
    
    def get_queryset(self):
        """Filter categories based on active status for non-staff users"""
        queryset = SupportCategory.objects.all()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
            
        return queryset


class SupportTicketViewSet(viewsets.ModelViewSet):
    """ViewSet for support tickets"""
    queryset = SupportTicket.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SupportTicketFilter
    search_fields = ['ticket_number', 'subject', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return SupportTicketCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SupportTicketUpdateSerializer
        elif self.action == 'list':
            return SupportTicketListSerializer
        return SupportTicketDetailSerializer
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return SupportTicket.objects.none()

        queryset = SupportTicket.objects.all()
        if self.request.user.is_authenticated:
            queryset = queryset.filter(user=self.request.user)
        else:
            queryset = queryset.none()
        return queryset
    
    def perform_create(self, serializer):
        """Set user when creating ticket"""
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """Add message to ticket"""
        ticket = self.get_object()
        serializer = TicketMessageCreateSerializer(
            data=request.data,
            context={'request': request, 'ticket': ticket}
        )
        
        if serializer.is_valid():
            # Check if internal note is being added by non-staff
            if not request.user.is_staff and serializer.validated_data.get('is_internal_note', False):
                return Response(
                    {'error': _("You don't have permission to add internal notes.")},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            message = serializer.save()
            
            # Mark all previous messages as read
            if request.user.is_staff:
                ticket.messages.filter(read_by_staff=False).update(read_by_staff=True)
            else:
                ticket.messages.filter(read_by_user=False).update(read_by_user=True)
            
            return Response(
                TicketMessageSerializer(message).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def rate_satisfaction(self, request, pk=None):
        """Rate ticket satisfaction"""
        ticket = self.get_object()
        
        # Only ticket owner can rate
        if ticket.user != request.user:
            return Response(
                {'error': _("You can only rate your own tickets.")},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Can only rate resolved or closed tickets
        if ticket.status not in [SupportTicket.STATUS_RESOLVED, SupportTicket.STATUS_CLOSED]:
            return Response(
                {'error': _("You can only rate resolved or closed tickets.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = TicketSatisfactionSerializer(ticket, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_messages_read(self, request, pk=None):
        """Mark all messages as read"""
        ticket = self.get_object()
        
        if request.user.is_staff:
            ticket.messages.filter(read_by_staff=False).update(read_by_staff=True)
        else:
            ticket.messages.filter(read_by_user=False).update(read_by_user=True)
        
        return Response({'status': 'messages marked as read'})
    
    @action(detail=False, methods=['get'])
    def my_tickets(self, request):
        """Get current user's tickets"""
        tickets = SupportTicket.objects.filter(user=request.user).order_by('-created_at')
        
        page = self.paginate_queryset(tickets)
        if page is not None:
            serializer = SupportTicketListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SupportTicketListSerializer(tickets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def stats(self, request):
        """Get ticket statistics (staff only)"""
        # Overall stats
        total_tickets = SupportTicket.objects.count()
        open_tickets = SupportTicket.objects.filter(
            status__in=[
                SupportTicket.STATUS_OPEN,
                SupportTicket.STATUS_IN_PROGRESS,
                SupportTicket.STATUS_WAITING
            ]
        ).count()
        resolved_tickets = SupportTicket.objects.filter(
            status=SupportTicket.STATUS_RESOLVED
        ).count()
        
        # Priority distribution
        priority_stats = SupportTicket.objects.values('priority').annotate(
            count=Count('id')
        ).order_by('priority')
        
        # Category distribution
        category_stats = SupportTicket.objects.values(
            'category__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Satisfaction stats
        satisfaction_stats = SupportTicket.objects.filter(
            satisfaction_rating__isnull=False
        ).values('satisfaction_rating').annotate(
            count=Count('id')
        ).order_by('satisfaction_rating')
        
        avg_satisfaction = SupportTicket.objects.filter(
            satisfaction_rating__isnull=False
        ).aggregate(avg=Sum('satisfaction_rating') / Count('satisfaction_rating'))
        
        return Response({
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'resolved_tickets': resolved_tickets,
            'priority_distribution': priority_stats,
            'category_distribution': category_stats,
            'satisfaction_stats': satisfaction_stats,
            'average_satisfaction': avg_satisfaction.get('avg')
        })


class FAQViewSet(viewsets.ModelViewSet):
    """ViewSet for FAQs"""
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    permission_classes = [IsStaffOrCreateOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FAQFilter
    search_fields = ['question', 'answer']
    ordering_fields = ['display_order', 'view_count', 'helpful_count']
    ordering = ['category', 'display_order']
    
    def get_queryset(self):
        """Filter FAQs based on published status for non-staff users"""
        queryset = FAQ.objects.all()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_published=True)
            
        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count on retrieve"""
        instance = self.get_object()
        
        # Increment view count
        instance.view_count = F('view_count') + 1
        instance.save(update_fields=['view_count'])
        instance.refresh_from_db()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        """Vote on FAQ helpfulness"""
        faq = self.get_object()
        serializer = FAQHelpfulnessSerializer(data=request.data)
        
        if serializer.is_valid():
            helpful = serializer.validated_data['helpful']
            
            if helpful:
                faq.helpful_count = F('helpful_count') + 1
            else:
                faq.not_helpful_count = F('not_helpful_count') + 1
                
            faq.save(update_fields=['helpful_count', 'not_helpful_count'])
            faq.refresh_from_db()
            
            return Response({
                'helpful_count': faq.helpful_count,
                'not_helpful_count': faq.not_helpful_count,
                'helpfulness_score': faq.helpfulness_score
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get FAQs grouped by category"""
        categories = SupportCategory.objects.filter(is_active=True)
        
        result = []
        for category in categories:
            faqs = FAQ.objects.filter(
                category=category,
                is_published=True
            ).order_by('display_order')
            
            if faqs.exists():
                result.append({
                    'category': SupportCategorySerializer(category).data,
                    'faqs': FAQSerializer(faqs, many=True).data
                })
        
        return Response(result)


class KnowledgeBaseCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for knowledge base categories"""
    queryset = KnowledgeBaseCategory.objects.all()
    serializer_class = KnowledgeBaseCategorySerializer
    permission_classes = [IsStaffOrCreateOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'display_order']
    ordering = ['display_order', 'name']
    lookup_field = 'slug'
    
    def get_queryset(self):
        """Filter categories based on active status for non-staff users"""
        queryset = KnowledgeBaseCategory.objects.all()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
            
        return queryset


class KnowledgeBaseArticleViewSet(viewsets.ModelViewSet):
    """ViewSet for knowledge base articles"""
    queryset = KnowledgeBaseArticle.objects.all()
    permission_classes = [IsStaffOrCreateOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = KnowledgeBaseArticleFilter
    search_fields = ['title', 'content', 'keywords']
    ordering_fields = ['created_at', 'updated_at', 'view_count', 'helpful_count']
    ordering = ['-is_featured', '-created_at']
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['create', 'update', 'partial_update']:
            return KnowledgeBaseArticleCreateUpdateSerializer
        elif self.action == 'list':
            return KnowledgeBaseArticleListSerializer
        return KnowledgeBaseArticleDetailSerializer
    
    def get_queryset(self):
        """Filter articles based on published status for non-staff users"""
        queryset = KnowledgeBaseArticle.objects.all()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_published=True)
            
        return queryset
    
    def perform_create(self, serializer):
        """Set author when creating article"""
        serializer.save(author=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count on retrieve"""
        instance = self.get_object()
        
        # Increment view count
        instance.view_count = F('view_count') + 1
        instance.save(update_fields=['view_count'])
        instance.refresh_from_db()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def vote(self, request, slug=None):
        """Vote on article helpfulness"""
        article = self.get_object()
        serializer = ArticleHelpfulnessSerializer(data=request.data)
        
        if serializer.is_valid():
            helpful = serializer.validated_data['helpful']
            
            if helpful:
                article.helpful_count = F('helpful_count') + 1
            else:
                article.not_helpful_count = F('not_helpful_count') + 1
                
            article.save(update_fields=['helpful_count', 'not_helpful_count'])
            article.refresh_from_db()
            
            return Response({
                'helpful_count': article.helpful_count,
                'not_helpful_count': article.not_helpful_count,
                'helpfulness_score': article.helpfulness_score
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured articles"""
        articles = KnowledgeBaseArticle.objects.filter(
            is_published=True,
            is_featured=True
        ).order_by('-created_at')
        
        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = KnowledgeBaseArticleListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = KnowledgeBaseArticleListSerializer(articles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get articles grouped by category"""
        categories = KnowledgeBaseCategory.objects.filter(is_active=True)
        
        result = []
        for category in categories:
            articles = KnowledgeBaseArticle.objects.filter(
                category=category,
                is_published=True
            ).order_by('-is_featured', '-created_at')
            
            if articles.exists():
                result.append({
                    'category': KnowledgeBaseCategorySerializer(category).data,
                    'articles': KnowledgeBaseArticleListSerializer(articles, many=True).data
                })
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most viewed articles"""
        articles = KnowledgeBaseArticle.objects.filter(
            is_published=True
        ).order_by('-view_count')[:10]
        
        serializer = KnowledgeBaseArticleListSerializer(articles, many=True)
        return Response(serializer.data)


class ContactMessageViewSet(viewsets.ModelViewSet):
    """ViewSet for contact messages"""
    queryset = ContactMessage.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ContactMessageFilter
    search_fields = ['name', 'email', 'subject', 'message']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ContactMessageSerializer
        return ContactMessageDetailSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action == 'create':
            return [AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsOwnerOrStaff()]
    
    def get_queryset(self):
        """Filter contact messages based on user role"""
        queryset = ContactMessage.objects.all()
        
        # Regular users can only see their own messages
        if not self.request.user.is_staff:
            if self.request.user.is_authenticated:
                queryset = queryset.filter(user=self.request.user)
            else:
                queryset = ContactMessage.objects.none()
                
        return queryset
    
    @action(detail=True, methods=['post'])
    def add_reply(self, request, pk=None):
        """Add reply to contact message"""
        contact_message = self.get_object()
        serializer = ContactReplyCreateSerializer(
            data=request.data,
            context={'request': request, 'contact_message': contact_message}
        )
        
        if serializer.is_valid():
            reply = serializer.save()
            return Response(
                ContactReplySerializer(reply).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def my_messages(self, request):
        """Get current user's contact messages"""
        if not request.user.is_authenticated:
            return Response(
                {'error': _("Authentication required.")},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        messages = ContactMessage.objects.filter(user=request.user).order_by('-created_at')
        
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = ContactMessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ContactMessageSerializer(messages, many=True)
        return Response(serializer.data)