# reviews/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db.models import Avg
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import (
    Review, ReviewImage, ReviewVote, ReviewComment,
    Question, Answer, AnswerVote
)
from products.models import Product
from orders.models import OrderItem


class ReviewImageSerializer(serializers.ModelSerializer):
    """Serializer for review images"""
    
    class Meta:
        model = ReviewImage
        fields = ['id', 'image', 'caption', 'created_at']
        read_only_fields = ['id', 'created_at']


class ReviewCommentSerializer(serializers.ModelSerializer):
    """Serializer for review comments"""
    user_display_name = serializers.SerializerMethodField()
    is_author = serializers.SerializerMethodField()
    
    class Meta:
        model = ReviewComment
        fields = [
            'id', 'user', 'user_display_name', 'content',
            'is_staff_response', 'is_author', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'user_display_name', 'is_staff_response',
            'is_author', 'created_at', 'updated_at'
        ]
    
    def get_user_display_name(self, obj):
        """Get user display name"""
        if obj.is_staff_response:
            return f"{obj.user.get_full_name()} ({_('Staff')})"
        return obj.user.get_full_name() or obj.user.email.split('@')[0]
    
    def get_is_author(self, obj):
        """Check if current user is the author"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for reviews"""
    user_display_name = serializers.CharField(read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    comments = ReviewCommentSerializer(many=True, read_only=True)
    helpfulness_score = serializers.IntegerField(read_only=True)
    is_author = serializers.SerializerMethodField()
    current_user_vote = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = [
            'id', 'product', 'user', 'user_display_name', 'rating',
            'title', 'content', 'status', 'is_verified_purchase',
            'is_anonymous', 'helpful_votes', 'unhelpful_votes',
            'helpfulness_score', 'created_at', 'updated_at',
            'images', 'comments', 'is_author', 'current_user_vote'
        ]
        read_only_fields = [
            'id', 'user', 'user_display_name', 'status', 'is_verified_purchase',
            'helpful_votes', 'unhelpful_votes', 'helpfulness_score',
            'created_at', 'updated_at', 'is_author', 'current_user_vote'
        ]
    
    def get_is_author(self, obj):
        """Check if current user is the author"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False
    
    def get_current_user_vote(self, obj):
        """Get current user's vote on this review"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        try:
            vote = ReviewVote.objects.get(review=obj, user=request.user)
            return vote.vote
        except ReviewVote.DoesNotExist:
            return None


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reviews"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True
    )
    image_captions = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = Review
        fields = [
            'product', 'rating', 'title', 'content',
            'is_anonymous', 'images', 'image_captions'
        ]
    
    def validate(self, data):
        """Validate review data"""
        user = self.context['request'].user
        product = data['product']
        
        # Check if user has already reviewed this product
        if Review.objects.filter(product=product, user=user).exists():
            raise serializers.ValidationError({
                'product': _("You have already reviewed this product.")
            })
        
        # Check if user has purchased this product
        has_purchased = OrderItem.objects.filter(
            order__user=user,
            product=product,
            order__status__in=['paid', 'preparing', 'shipped', 'delivered']
        ).exists()
        
        data['is_verified_purchase'] = has_purchased
        
        # Validate image captions
        images = data.get('images', [])
        captions = data.get('image_captions', [])
        
        if len(captions) > len(images):
            raise serializers.ValidationError({
                'image_captions': _("You provided more captions than images.")
            })
        
        return data
    
    def create(self, validated_data):
        """Create a new review with images"""
        images = validated_data.pop('images', [])
        captions = validated_data.pop('image_captions', [])
        
        # Set user from request
        validated_data['user'] = self.context['request'].user
        
        # Create review
        review = Review.objects.create(**validated_data)
        
        # Create review images
        for i, image in enumerate(images):
            caption = captions[i] if i < len(captions) else ""
            ReviewImage.objects.create(
                review=review,
                image=image,
                caption=caption
            )
        
        return review


class ReviewUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating reviews"""
    
    class Meta:
        model = Review
        fields = ['rating', 'title', 'content', 'is_anonymous']
    
    def validate(self, data):
        """Validate review update"""
        # Only allow updates if review is not yet approved
        if self.instance.status != Review.STATUS_PENDING:
            raise serializers.ValidationError({
                'non_field_errors': _("You can only update pending reviews.")
            })
        
        return data


class ReviewVoteSerializer(serializers.ModelSerializer):
    """Serializer for review votes"""
    
    class Meta:
        model = ReviewVote
        fields = ['vote']


class ReviewCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating review comments"""
    
    class Meta:
        model = ReviewComment
        fields = ['content']
    
    def create(self, validated_data):
        """Create a new review comment"""
        review = self.context['review']
        user = self.context['request'].user
        
        # Set staff response flag if user is staff
        is_staff_response = user.is_staff
        
        return ReviewComment.objects.create(
            review=review,
            user=user,
            content=validated_data['content'],
            is_staff_response=is_staff_response
        )


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for questions"""
    user_display_name = serializers.CharField(read_only=True)
    answer_count = serializers.IntegerField(read_only=True)
    answers = serializers.SerializerMethodField()
    is_author = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = [
            'id', 'product', 'user', 'user_display_name',
            'question', 'status', 'is_anonymous',
            'created_at', 'updated_at', 'answer_count',
            'answers', 'is_author'
        ]
        read_only_fields = [
            'id', 'user', 'user_display_name', 'status',
            'created_at', 'updated_at', 'answer_count',
            'answers', 'is_author'
        ]
    
    def get_answers(self, obj):
        """Get approved answers"""
        # Only return approved answers
        answers = obj.answers.filter(is_approved=True)
        return AnswerSerializer(answers, many=True, context=self.context).data
    
    def get_is_author(self, obj):
        """Check if current user is the author"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating questions"""
    
    class Meta:
        model = Question
        fields = ['product', 'question', 'is_anonymous']
    
    def create(self, validated_data):
        """Create a new question"""
        # Set user from request
        validated_data['user'] = self.context['request'].user
        
        return Question.objects.create(**validated_data)


class QuestionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating questions"""
    
    class Meta:
        model = Question
        fields = ['question', 'is_anonymous']
    
    def validate(self, data):
        """Validate question update"""
        # Only allow updates if question is not yet approved or answered
        if self.instance.status not in [Question.STATUS_PENDING, Question.STATUS_APPROVED]:
            raise serializers.ValidationError({
                'non_field_errors': _("You can only update pending or approved questions.")
            })
        
        return data


class AnswerSerializer(serializers.ModelSerializer):
    """Serializer for answers"""
    user_display_name = serializers.CharField(read_only=True)
    helpfulness_score = serializers.IntegerField(read_only=True)
    is_author = serializers.SerializerMethodField()
    current_user_vote = serializers.SerializerMethodField()
    
    class Meta:
        model = Answer
        fields = [
            'id', 'question', 'user', 'user_display_name',
            'answer', 'is_staff_answer', 'is_anonymous',
            'helpful_votes', 'unhelpful_votes', 'helpfulness_score',
            'created_at', 'updated_at', 'is_approved',
            'is_author', 'current_user_vote'
        ]
        read_only_fields = [
            'id', 'user', 'user_display_name', 'is_staff_answer',
            'helpful_votes', 'unhelpful_votes', 'helpfulness_score',
            'created_at', 'updated_at', 'is_approved',
            'is_author', 'current_user_vote'
        ]
    
    def get_is_author(self, obj):
        """Check if current user is the author"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False
    
    def get_current_user_vote(self, obj):
        """Get current user's vote on this answer"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        try:
            vote = AnswerVote.objects.get(answer=obj, user=request.user)
            return vote.vote
        except AnswerVote.DoesNotExist:
            return None


class AnswerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating answers"""
    
    class Meta:
        model = Answer
        fields = ['answer', 'is_anonymous']
    
    def create(self, validated_data):
        """Create a new answer"""
        question = self.context['question']
        user = self.context['request'].user
        
        # Set staff answer flag if user is staff
        is_staff_answer = user.is_staff
        
        # Create answer
        answer = Answer.objects.create(
            question=question,
            user=user,
            answer=validated_data['answer'],
            is_anonymous=validated_data['is_anonymous'],
            is_staff_answer=is_staff_answer
        )
        
        return answer


class AnswerUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating answers"""
    
    class Meta:
        model = Answer
        fields = ['answer', 'is_anonymous']


class AnswerVoteSerializer(serializers.ModelSerializer):
    """Serializer for answer votes"""
    
    class Meta:
        model = AnswerVote
        fields = ['vote']


class ProductRatingSummarySerializer(serializers.Serializer):
    """Serializer for product rating summary"""
    product_id = serializers.UUIDField()
    average_rating = serializers.FloatField()
    review_count = serializers.IntegerField()
    rating_distribution = serializers.DictField()
    
    @classmethod
    def get_summary(cls, product_id):
        """Get rating summary for a product"""
        product = get_object_or_404(Product, id=product_id)
        
        # Get approved reviews only
        reviews = Review.objects.filter(
            product=product,
            status=Review.STATUS_APPROVED
        )
        
        # Calculate average rating
        review_count = reviews.count()
        if review_count > 0:
            average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        else:
            average_rating = 0
        
        # Calculate rating distribution
        distribution = {
            '5': reviews.filter(rating=5).count(),
            '4': reviews.filter(rating=4).count(),
            '3': reviews.filter(rating=3).count(),
            '2': reviews.filter(rating=2).count(),
            '1': reviews.filter(rating=1).count(),
        }
        
        return {
            'product_id': product.id,
            'average_rating': round(average_rating, 1) if average_rating else 0,
            'review_count': review_count,
            'rating_distribution': distribution
        }