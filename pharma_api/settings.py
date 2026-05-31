import os
from pathlib import Path
from decouple import config
from datetime import timedelta
from celery.schedules import crontab


# -------------------
# BASE SETTINGS
# -------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="your-secret-key")

DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="*").split(",")

# -------------------
# INSTALLED APPS
# -------------------
INSTALLED_APPS = [
    
    # Django apps
    'unfold',
    'colorfield',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',

    # Third Party
    'rest_framework',
    'django_filters',
    'django_extensions',
    'corsheaders',
    'rest_framework.authtoken',
    # 'admin_interface',
    # 'colorfield',
    
    # Local apps
    'accounts',
    'blog',
    'products',
    'orders',
    'payments',
    'promotions',
    'reviews',
    'support',
    'drf_spectacular',
]

# -------------------
# MIDDLEWARE
# -------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000"
).split(",")

# Allow credentials (cookies, authorization headers)
CORS_ALLOW_CREDENTIALS = True

# Allow all headers in preflight requests
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Allow these HTTP methods
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]


# -------------------
# URL & TEMPLATES
# -------------------
ROOT_URLCONF = 'pharma_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pharma_api.wsgi.application'

# -------------------
# DATABASE
# -------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # You can switch to PostgreSQL later
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# -------------------
# PASSWORD VALIDATION
# -------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# -------------------
# LANGUAGE & TIME
# -------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

# -------------------
# STATIC & MEDIA
# -------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# -------------------
# CUSTOM USER MODEL
# -------------------
AUTH_USER_MODEL = 'accounts.User'  # We will create this model

# -------------------
# DJANGO REST FRAMEWORK CONFIG
# -------------------
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter',
    ),
    'FORMAT_SUFFIX_KWARG': None, 
}

# -------------------
# SIMPLE JWT SETTINGS
# -------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# -------------------
# DEFAULT PRIMARY KEY TYPE
# -------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = config(
        "CORS_ALLOWED_ORIGINS",
        default="http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")


CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@gmail.com'
EMAIL_HOST_PASSWORD = 'your_app_password'
DEFAULT_FROM_EMAIL = 'noreply@pharma.com'

LANGUAGE_CODE = 'fa'
USE_I18N = True
USE_L10N = True 
USE_TZ = True

SMS_IR_API_KEY = config('SMS_IR_API_KEY', default='')
SMS_IR_VERIFY_TEMPLATE_ID = config('SMS_IR_VERIFY_TEMPLATE_ID', default='')
MOCK_SMS = config('MOCK_SMS', default=False, cast=bool)
SMS_IR_SANDBOX = config('SMS_IR_SANDBOX', default=False, cast=bool)
SMS_IR_LINE_NUMBER = config('SMS_IR_LINE_NUMBER', default=0, cast=int)

CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    'release-expired-orders': {
        'task': 'orders.tasks.release_expired_reservations',
        'schedule': crontab(minute='*/5'),  # every 5 minutes
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'orders': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]




from django.templatetags.static import static

UNFOLD = {
    "SITE_TITLE": "Pharma Admin",
    "SITE_HEADER": "Pharmacy Store",
    "SITE_SUBHEADER": "Manage orders, prescriptions & inventory",
    "SITE_URL": "/",
    "DARK_MODE": True,
    # Branding with your favicon/logo (no background)
    "SITE_ICON": {
        "light": lambda request: static("favicon.png"),
        "dark": lambda request: static("favicon.png"),
    },
    "SITE_LOGO": {
        "light": lambda request: static("favicon.png"),
        "dark": lambda request: static("favicon.png"),
    },
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/png",
            "href": lambda request: static("favicon.png"),
        },
    ],
    "BORDER_RADIUS": "12px",
    "SHOW_HISTORY": False,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_BACK_BUTTON": True,
    "SHOW_UI_WARNINGS": False,
    "ENVIRONMENT": "yourapp.environment_callback",  # optional, see note below
    "COLORS": {
        "base": {
            "50": "oklch(98.5% .002 247.839)",
            "100": "oklch(96.7% .003 264.542)",
            "200": "oklch(92.8% .006 264.531)",
            "300": "oklch(87.2% .01 258.338)",
            "400": "oklch(70.7% .022 261.325)",
            "500": "oklch(55.1% .027 264.364)",
            "600": "oklch(44.6% .03 256.802)",
            "700": "oklch(37.3% .034 259.733)",
            "800": "oklch(27.8% .033 256.848)",
            "900": "oklch(21% .034 264.665)",
            "950": "oklch(13% .028 261.692)",
        },
        "primary": {
            "50": "#e6f5f4",
            "100": "#ccebe8",
            "200": "#99d6d1",
            "300": "#66c2ba",
            "400": "#33ada3",
            "500": "#0d9488",  # teal brand
            "600": "#0a7670",
            "700": "#085958",
            "800": "#053b40",
            "900": "#031e28",
            "950": "#010f14",
        },
        "secondary": {
            "50": "#f1f5f9",
            "100": "#e2e8f0",
            "200": "#cbd5e1",
            "300": "#94a3b8",
            "400": "#64748b",
            "500": "#475569",
            "600": "#334155",
            "700": "#1e293b",
            "800": "#0f172a",
            "900": "#020617",
            "950": "#020617",
        },
        "success": {
            "50": "#ecfdf5",
            "100": "#d1fae5",
            "200": "#a7f3d0",
            "300": "#6ee7b7",
            "400": "#34d399",
            "500": "#10b981",
            "600": "#059669",
            "700": "#047857",
            "800": "#065f46",
            "900": "#064e3b",
            "950": "#022c22",
        },
        "danger": {
            "50": "#fef2f2",
            "100": "#fee2e2",
            "200": "#fecaca",
            "300": "#fca5a5",
            "400": "#f87171",
            "500": "#ef4444",
            "600": "#dc2626",
            "700": "#b91c1c",
            "800": "#991b1b",
            "900": "#7f1d1d",
            "950": "#450a0a",
        },
        "warning": {
            "50": "#fffbeb",
            "100": "#fef3c7",
            "200": "#fde68a",
            "300": "#fcd34d",
            "400": "#fbbf24",
            "500": "#f59e0b",
            "600": "#d97706",
            "700": "#b45309",
            "800": "#92400e",
            "900": "#78350f",
            "950": "#431407",
        },
        "font": {
            "subtle-light": "var(--color-base-500)",
            "subtle-dark": "var(--color-base-400)",
            "default-light": "var(--color-base-600)",
            "default-dark": "var(--color-base-300)",
            "important-light": "var(--color-base-900)",
            "important-dark": "var(--color-base-100)",
        },
    },
    "TABS": [
        {
            "models": ["accounts.User", "accounts.UserProfile", "accounts.PharmacyLicense"],
            "items": [
                {"title": "All Users", "link": "/admin/accounts/user/"},
                {"title": "Pending Licenses", "link": "/admin/accounts/pharmacylicense/?status__exact=pending"},
                {"title": "User Profiles", "link": "/admin/accounts/userprofile/"},
            ],
        },
        {
            "models": ["orders.Order", "orders.Refund", "orders.Shipment"],
            "items": [
                {"title": "Orders", "link": "/admin/orders/order/"},
                {"title": "Pending Prescriptions", "link": "/admin/orders/order/?prescription_file__isnull=False&prescription_verified__exact=0"},
                {"title": "Refunds", "link": "/admin/orders/refund/"},
            ],
        },
    ],
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Dashboard",
                "items": [
                    {"title": "Home", "icon": "dashboard", "link": "/admin/"},
                ],
            },
            {
                "title": "Shop Management",
                "collapsible": True,
                "items": [
                    {"title": "Orders", "icon": "shopping_cart", "link": "/admin/orders/order/"},
                    {"title": "Products", "icon": "inventory", "link": "/admin/products/product/"},
                    {"title": "Customers", "icon": "people", "link": "/admin/accounts/user/"},
                    {"title": "Promotions", "icon": "local_offer", "link": "/admin/promotions/promotion/"},
                ],
            },
            {
                "title": "Content",
                "items": [
                    {"title": "Blog Posts", "icon": "article", "link": "/admin/blog/blogpost/"},
                    {"title": "FAQ", "icon": "help", "link": "/admin/support/faq/"},
                ],
            },
            {
                "title": "Support",
                "items": [
                    {
                        "title": "Tickets",
                        "icon": "support_agent",
                        "link": "/admin/support/supportticket/",
                        # optional: add badge with open tickets count (requires a callback)
                        # "badge": "yourapp.badge_callback",
                        # "badge_variant": "danger",
                    },
                ],
            },
        ],
    },
    # FIX: sidebarWidth variable for Alpine.js
    "SCRIPTS": [
        lambda request: "data:text/javascript;charset=utf-8,window.sidebarWidth = 260;",
    ],
}

