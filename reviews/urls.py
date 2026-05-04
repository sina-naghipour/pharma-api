# reviews/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ReviewViewSet,
    QuestionViewSet,
    AnswerViewSet
)

# Configure router for ViewSets
router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'answers', AnswerViewSet, basename='answer')

# URL patterns with versioning
app_name = 'reviews'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
]