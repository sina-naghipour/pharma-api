from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import BlogPostViewSet

router = SimpleRouter()
router.register(r'posts', BlogPostViewSet, basename='blog-post')

app_name = 'blog'
urlpatterns = [
    path('', include(router.urls)),
]