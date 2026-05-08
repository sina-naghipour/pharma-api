from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db.models import Avg
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import IntegrityError

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
        if obj.is_staff_response:
            return f"{obj.user.get_full_name()} ({_('Staff')})"
        return obj.user.get_full_name() or obj.user.email.split('@')[0]
    
    def get_is_author(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for reviews"""
    user_display_name = serializers.CharField(read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
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
    
    def get_comments(self, obj):
        qs = obj.comments.filter(is_approved=True)
        return ReviewCommentSerializer(qs, many=True, context=self.context).data
    
    def get_is_author(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False
    
    def get_current_user_vote(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        try:
            vote = ReviewVote.objects.get(review=obj, user=request.user)
            return vote.vote
        except ReviewVote.DoesNotExist:
            return None
class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reviews with session-based uniqueness for anonymous users"""
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
        request = self.context['request']
        user = request.user
        product = data['product']
        session_key = request.session.session_key

        if user.is_authenticated:
            if Review.objects.filter(product=product, user=user).exists():
                raise serializers.ValidationError({
                    'non_field_errors': _("شما قبلاً برای این محصول نظر داده‌اید.")
                })
            has_purchased = OrderItem.objects.filter(
                order__user=user,
                product=product,
                order__status__in=['paid', 'preparing', 'shipped', 'delivered']
            ).exists()
            data['is_verified_purchase'] = has_purchased
            data['session_key'] = None
        else:
            if session_key and Review.objects.filter(product=product, session_key=session_key).exists():
                raise serializers.ValidationError({
                    'non_field_errors': _("شما قبلاً از این نشست مرورگر برای این محصول نظر داده‌اید.")
                })
            data['is_anonymous'] = True
            data['is_verified_purchase'] = False
            data['session_key'] = session_key

        images = data.get('images', [])
        captions = data.get('image_captions', [])
        if len(captions) > len(images):
            raise serializers.ValidationError({
                'image_captions': _("تعداد توضیحات تصاویر بیشتر از تعداد تصاویر است.")
            })

        return data

    def create(self, validated_data):
        images = validated_data.pop('images', [])
        captions = validated_data.pop('image_captions', [])
        request = self.context['request']

        if request.user.is_authenticated:
            validated_data['user'] = request.user
        else:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            anonymous_user, _ = User.objects.get_or_create(
                username='anonymous',
                defaults={
                    'email': 'anonymous@example.com',
                    'first_name': 'ناشناس',
                    'last_name': '',
                    'is_active': True
                }
            )
            validated_data['user'] = anonymous_user

        try:
            review = Review.objects.create(**validated_data)
        except IntegrityError:
            raise serializers.ValidationError({
                'non_field_errors': _("شما قبلاً برای این محصول نظر داده‌اید.")
            })

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
    """Serializer for creating review comments (supports anonymous users)"""
    
    class Meta:
        model = ReviewComment
        fields = ['content']
    
    def create(self, validated_data):
        review = self.context['review']
        request = self.context['request']
        user = request.user
        session_key = request.session.session_key

        if user.is_authenticated:
            comment_user = user
            is_staff_response = user.is_staff
            comment_session_key = None
        else:
            # Anonymous user – use the dedicated anonymous user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            comment_user, _ = User.objects.get_or_create(
                username='anonymous',
                defaults={
                    'email': 'anonymous@example.com',
                    'first_name': 'ناشناس',
                    'last_name': '',
                    'is_active': True
                }
            )
            is_staff_response = False
            comment_session_key = session_key
            if not comment_session_key:
                request.session.save()
                comment_session_key = request.session.session_key

        return ReviewComment.objects.create(
            review=review,
            user=comment_user,
            content=validated_data['content'],
            is_staff_response=is_staff_response,
            session_key=comment_session_key
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
        answers = obj.answers.filter(is_approved=True)
        return AnswerSerializer(answers, many=True, context=self.context).data
    
    def get_is_author(self, obj):
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
        validated_data['user'] = self.context['request'].user
        return Question.objects.create(**validated_data)


class QuestionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating questions"""
    
    class Meta:
        model = Question
        fields = ['question', 'is_anonymous']
    
    def validate(self, data):
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
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False
    
    def get_current_user_vote(self, obj):
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
        question = self.context['question']
        user = self.context['request'].user
        is_staff_answer = user.is_staff
        return Answer.objects.create(
            question=question,
            user=user,
            answer=validated_data['answer'],
            is_anonymous=validated_data['is_anonymous'],
            is_staff_answer=is_staff_answer
        )


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
        product = get_object_or_404(Product, id=product_id)
        reviews = Review.objects.filter(
            product=product,
            status=Review.STATUS_APPROVED
        )
        review_count = reviews.count()
        if review_count > 0:
            average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        else:
            average_rating = 0
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