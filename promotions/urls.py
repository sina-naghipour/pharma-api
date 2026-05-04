# promotions/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CouponViewSet,
    PromotionViewSet,
    RewardPointViewSet,
    ReferralProgramViewSet,
    ReferralViewSet
)

# Configure router for ViewSets
router = DefaultRouter()
router.register(r'coupons', CouponViewSet, basename='coupon')
router.register(r'promotions', PromotionViewSet, basename='promotion')
router.register(r'reward-points', RewardPointViewSet, basename='reward-point')
router.register(r'referral-programs', ReferralProgramViewSet, basename='referral-program')
router.register(r'referrals', ReferralViewSet, basename='referral')

# URL patterns with versioning
app_name = 'promotions'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
]