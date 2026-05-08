from django.db.models import Q, Count, Avg
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, mixins, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Review, ReviewImage, ReviewVote, ReviewComment,
    Question, Answer, AnswerVote
)
from .serializers import (
    ReviewSerializer, ReviewCreateSerializer, ReviewUpdateSerializer,
    ReviewImageSerializer, ReviewVoteSerializer, ReviewCommentSerializer,
    ReviewCommentCreateSerializer, QuestionSerializer, QuestionCreateSerializer,
    QuestionUpdateSerializer, AnswerSerializer, AnswerCreateSerializer,
    AnswerUpdateSerializer, AnswerVoteSerializer, ProductRatingSummarySerializer
)
from .permissions import (
    IsOwnerOrReadOnly, IsModeratorOrReadOnly, 
    CanReviewProduct, CanAnswerQuestion
)
from .filters import ReviewFilter, QuestionFilter


class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for managing reviews"""
    queryset = Review.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReviewFilter
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'rating', 'helpful_votes']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ReviewCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return ReviewUpdateSerializer
        return ReviewSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action == 'create':
            return [AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        elif self.action in ['moderate']:
            return [IsAuthenticated(), IsModeratorOrReadOnly()]
        return super().get_permissions()
    
    def get_queryset(self):
        """Filter reviews based on user role and status"""
        queryset = Review.objects.all()
        
        # For regular users, only show approved reviews
        if not self.request.user.is_staff:
            # If viewing own reviews, show all statuses
            if self.action == 'list' and self.request.query_params.get('user') == 'me':
                queryset = queryset.filter(user=self.request.user)
            else:
                queryset = queryset.filter(status=Review.STATUS_APPROVED)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set user when creating review"""
        serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def vote(self, request, pk=None):
        """Vote on review helpfulness (supports authenticated and anonymous users)"""
        from django.utils.translation import gettext_lazy as __
        review = self.get_object()
        
        if request.user.is_authenticated and review.user == request.user:
            return Response(
                {'error': __("You cannot vote on your own review.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ReviewVoteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        vote_value = serializer.validated_data['vote']
        
        if request.user.is_authenticated:
            user = request.user
            session_key = None
            existing_vote = ReviewVote.objects.filter(review=review, user=user).first()
        else:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user, _ = User.objects.get_or_create(
                username='anonymous',
                defaults={
                    'email': 'anonymous@example.com',
                    'first_name': 'ناشناس',
                    'last_name': '',
                    'is_active': True
                }
            )
            session_key = request.session.session_key
            if not session_key:
                request.session.save()
                session_key = request.session.session_key
            existing_vote = ReviewVote.objects.filter(review=review, session_key=session_key).first()
        
        if existing_vote:
            existing_vote.vote = vote_value
            existing_vote.save()
            message = __("Your vote has been updated.")
        else:
            ReviewVote.objects.create(
                review=review,
                user=user,
                session_key=session_key if not request.user.is_authenticated else None,
                vote=vote_value
            )
            message = __("Your vote has been recorded.")
        
        serializer_review = self.get_serializer(review)
        return Response({
            'message': message,
            'review': serializer_review.data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def add_comment(self, request, pk=None):
        """Add comment to review (supports anonymous users)"""
        review = self.get_object()
        serializer = ReviewCommentCreateSerializer(
            data=request.data,
            context={'request': request, 'review': review}
        )
        
        if serializer.is_valid():
            comment = serializer.save()
            return Response(
                ReviewCommentSerializer(comment, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsModeratorOrReadOnly])
    def moderate(self, request, pk=None):
        """Moderate review"""
        review = self.get_object()
        status_value = request.data.get('status')
        reason = request.data.get('reason', '')
        
        if status_value not in dict(Review.STATUS_CHOICES):
            return Response(
                {'error': _("Invalid status value.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        review.moderate(status_value, request.user, reason)
        
        serializer = self.get_serializer(review)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Get current user's reviews"""
        reviews = Review.objects.filter(user=request.user).order_by('-created_at')
        
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def product_summary(self, request):
        """Get rating summary for a product"""
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response(
                {'error': _("Product ID is required.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        summary = ProductRatingSummarySerializer.get_summary(product_id)
        return Response(summary)


class QuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing questions"""
    queryset = Question.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = QuestionFilter
    search_fields = ['question']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return QuestionCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return QuestionUpdateSerializer
        return QuestionSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action == 'create':
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        elif self.action in ['moderate']:
            return [IsAuthenticated(), IsModeratorOrReadOnly()]
        return super().get_permissions()
    
    def get_queryset(self):
        """Filter questions based on user role and status"""
        queryset = Question.objects.all()
        
        # For regular users, only show approved or answered questions
        if not self.request.user.is_staff:
            # If viewing own questions, show all statuses
            if self.action == 'list' and self.request.query_params.get('user') == 'me':
                queryset = queryset.filter(user=self.request.user)
            else:
                queryset = queryset.filter(
                    Q(status=Question.STATUS_APPROVED) | 
                    Q(status=Question.STATUS_ANSWERED)
                )
        
        return queryset
    
    def perform_create(self, serializer):
        """Set user when creating question"""
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def add_answer(self, request, pk=None):
        """Add answer to question"""
        question = self.get_object()
        
        # Check if question can be answered
        if question.status not in [Question.STATUS_APPROVED, Question.STATUS_ANSWERED]:
            return Response(
                {'error': _("This question cannot be answered.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AnswerCreateSerializer(
            data=request.data,
            context={'request': request, 'question': question}
        )
        
        if serializer.is_valid():
            answer = serializer.save()
            return Response(
                AnswerSerializer(answer, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsModeratorOrReadOnly])
    def moderate(self, request, pk=None):
        """Moderate question"""
        question = self.get_object()
        status_value = request.data.get('status')
        reason = request.data.get('reason', '')
        
        if status_value not in dict(Question.STATUS_CHOICES):
            return Response(
                {'error': _("Invalid status value.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        question.moderate(status_value, request.user, reason)
        
        serializer = self.get_serializer(question)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_questions(self, request):
        """Get current user's questions"""
        questions = Question.objects.filter(user=request.user).order_by('-created_at')
        
        page = self.paginate_queryset(questions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(questions, many=True)
        return Response(serializer.data)


class AnswerViewSet(mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.DestroyModelMixin,
                    viewsets.GenericViewSet):
    """ViewSet for managing answers"""
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['update', 'partial_update']:
            return AnswerUpdateSerializer
        return AnswerSerializer
    
    def get_queryset(self):
        """Filter answers based on user role"""
        queryset = Answer.objects.all()
        
        # For regular users, only show approved answers
        if not self.request.user.is_staff:
            # If viewing own answers, show all
            if self.action == 'list' and self.request.query_params.get('user') == 'me':
                queryset = queryset.filter(user=self.request.user)
            else:
                queryset = queryset.filter(is_approved=True)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        """Vote on answer helpfulness"""
        answer = self.get_object()
        
        # Don't allow voting on own answers
        if answer.user == request.user:
            return Response(
                {'error': _("You cannot vote on your own answer.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AnswerVoteSerializer(data=request.data)
        if serializer.is_valid():
            vote_value = serializer.validated_data['vote']
            
            # Check if user has already voted
            try:
                vote = AnswerVote.objects.get(answer=answer, user=request.user)
                # Update existing vote
                vote.vote = vote_value
                vote.save()
                message = _("Your vote has been updated.")
            except AnswerVote.DoesNotExist:
                # Create new vote
                AnswerVote.objects.create(
                    answer=answer,
                    user=request.user,
                    vote=vote_value
                )
                message = _("Your vote has been recorded.")
            
            # Return updated answer
            serializer = self.get_serializer(answer)
            return Response({
                'message': message,
                'answer': serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def my_answers(self, request):
        """Get current user's answers"""
        answers = Answer.objects.filter(user=request.user).order_by('-created_at')
        
        page = self.paginate_queryset(answers)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(answers, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsModeratorOrReadOnly])
    def approve(self, request, pk=None):
        """Approve or disapprove an answer"""
        answer = self.get_object()
        is_approved = request.data.get('is_approved', True)
        
        answer.is_approved = is_approved
        answer.save(update_fields=['is_approved', 'updated_at'])
        
        serializer = self.get_serializer(answer)
        return Response(serializer.data)