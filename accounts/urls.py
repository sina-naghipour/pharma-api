# accounts/urls.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from . import views

router = SimpleRouter()
router.register(r'users', views.UserViewSet)
router.register(r'profiles', views.UserProfileViewSet, basename='profile')
router.register(r'addresses', views.UserAddressViewSet, basename='address')
router.register(r'licenses', views.PharmacyLicenseViewSet, basename='license')

app_name = 'accounts'
urlpatterns = [
    path('', include(router.urls)),
    # JWT endpoints
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # Legacy Logout
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/request-otp/', views.UserViewSet.as_view({'post': 'request_otp'}), name='request_otp'),
    path('auth/verify-otp/', views.UserViewSet.as_view({'post': 'verify_otp'}), name='verify_otp'),
    path('auth/set_password_with_otp/', views.UserViewSet.as_view({'post': 'set_password_with_otp'}), name='set_password_with_otp'),
]