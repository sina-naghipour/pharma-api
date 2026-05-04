# reviews/permissions.py
from rest_framework import permissions
from django.utils.translation import gettext_lazy as _
from orders.models import OrderItem


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow read access to everyone, but only allow write access to the owner.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner
        return obj.user == request.user


class IsModeratorOrReadOnly(permissions.BasePermission):
    """
    Allow read access to everyone, but only allow moderation actions to staff.
    """
    
    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to staff users
        return request.user and request.user.is_staff


class CanReviewProduct(permissions.BasePermission):
    """
    Check if user can review a product.
    """
    
    def has_permission(self, request, view):
        if view.action != 'create':
            return True
        
        # Get product ID from request data
        product_id = request.data.get('product')
        if not product_id:
            return False
        
        # Check if user has already reviewed this product
        from reviews.models import Review
        if Review.objects.filter(product_id=product_id, user=request.user).exists():
            self.message = _("You have already reviewed this product.")
            return False
        
        # Optionally check if user has purchased the product
        # Uncomment this if you want to enforce purchase verification
        # has_purchased = OrderItem.objects.filter(
        #     order__user=request.user,
        #     product_id=product_id,
        #     order__status__in=['paid', 'preparing', 'shipped', 'delivered']
        # ).exists()
        # 
        # if not has_purchased:
        #     self.message = _("You can only review products you have purchased.")
        #     return False
        
        return True


class CanAnswerQuestion(permissions.BasePermission):
    """
    Check if user can answer a question.
    """
    
    def has_permission(self, request, view):
        if view.action != 'add_answer':
            return True
        
        # Staff can always answer questions
        if request.user.is_staff:
            return True
        
        # Get question ID from URL
        question_id = view.kwargs.get('pk')
        if not question_id:
            return False
        
        # Check if question is approved or answered
        from reviews.models import Question
        try:
            question = Question.objects.get(pk=question_id)
            return question.status in [Question.STATUS_APPROVED, Question.STATUS_ANSWERED]
        except Question.DoesNotExist:
            return False