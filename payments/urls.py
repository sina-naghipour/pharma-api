# payments/urls.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views

router = SimpleRouter()
router.register(r'methods', views.PaymentMethodViewSet)
router.register(r'gateways', views.PaymentGatewayViewSet)
router.register(r'payments', views.PaymentViewSet, basename='payment')
router.register(r'refunds', views.PaymentRefundViewSet, basename='refund')
router.register(r'saved-methods', views.SavedPaymentMethodViewSet, basename='saved-method')
router.register(r'webhooks', views.PaymentWebhookViewSet)
router.register(r'disputes', views.PaymentDisputeViewSet)

app_name = 'payments'
urlpatterns = [
    path('', include(router.urls)),
]