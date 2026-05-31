from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

API_TITLE = 'Pharma API'
API_DESCRIPTION = 'A comprehensive API for pharmaceutical e-commerce'
API_VERSION = 'v1'


urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # API schema (OpenAPI JSON)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Swagger UI documentation
    path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # ReDoc UI documentation
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API endpoints with versioning
    path(f'api/{API_VERSION}/accounts/', include('accounts.urls', namespace='accounts')),
    path(f'api/{API_VERSION}/products/', include('products.urls', namespace='products')),
    path(f'api/{API_VERSION}/orders/', include('orders.urls', namespace='orders')),
    path(f'api/{API_VERSION}/payments/', include('payments.urls', namespace='payments')),
    path(f'api/{API_VERSION}/promotions/', include('promotions.urls', namespace='promotions')),
    path(f'api/{API_VERSION}/reviews/', include('reviews.urls', namespace='reviews')),
    path('api/v1/blog/', include('blog.urls', namespace='blog')),
    path(f'api/{API_VERSION}/support/', include('support.urls', namespace='support')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Add debug toolbar in development
    try:
        import debug_toolbar
        urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
    except ImportError:
        pass