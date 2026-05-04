# support/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SupportCategoryViewSet, SupportTicketViewSet,
    FAQViewSet, KnowledgeBaseCategoryViewSet,
    KnowledgeBaseArticleViewSet, ContactMessageViewSet
)

# Configure router for ViewSets
router = DefaultRouter()
router.register(r'categories', SupportCategoryViewSet, basename='support-category')
router.register(r'tickets', SupportTicketViewSet, basename='support-ticket')
router.register(r'faqs', FAQViewSet, basename='faq')
router.register(r'kb/categories', KnowledgeBaseCategoryViewSet, basename='kb-category')
router.register(r'kb/articles', KnowledgeBaseArticleViewSet, basename='kb-article')
router.register(r'contact', ContactMessageViewSet, basename='contact-message')

# URL patterns with versioning
app_name = 'support'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
]