# pharma_api/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.documentation import include_docs_urls
from rest_framework.permissions import IsAuthenticated

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


API_TITLE = 'Pharma API'
API_DESCRIPTION = 'A comprehensive API for pharmaceutical e-commerce'
API_VERSION = 'v1'


schema_view = get_schema_view(
    openapi.Info(
        title=API_TITLE,
        default_version=API_VERSION,
        description=API_DESCRIPTION,
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)



urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),
    
    # API endpoints with versioning
    path(f'api/{API_VERSION}/accounts/', include('accounts.urls', namespace='accounts')),
    path(f'api/{API_VERSION}/products/', include('products.urls', namespace='products')),
    path(f'api/{API_VERSION}/orders/', include('orders.urls', namespace='orders')),
    path(f'api/{API_VERSION}/payments/', include('payments.urls', namespace='payments')),
    path(f'api/{API_VERSION}/promotions/', include('promotions.urls', namespace='promotions')),
    path(f'api/{API_VERSION}/reviews/', include('reviews.urls', namespace='reviews')),
    path(f'api/{API_VERSION}/support/', include('support.urls', namespace='support')),
    
    path('docs/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

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