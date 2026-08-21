import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-rihan-dev')
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    
    # Third-party apps
    'rest_framework',
    
    # ✅ ریهان Core (M14 - معماری پلاگین‌محور)
    'src.core',
    
    # ✅ ماژول احراز هویت (M10)
    'src.modules.auth',
    'src.modules.catalog',
    
    # ✅ ماژول RBAC (M5)
    'src.modules.rbac',
    'src.modules.supplier_panel',
    
    # ✅ ماژول Audit Log (اسپرینت ۱)
    'src.modules.audit',
    
    # ماژول‌های ریهان (بر اساس D-079 - ۱۴ ماژول)
    #    # M1 - غیرفعال تا تکمیل بازنویسی
    'src.modules.order',     # M2 - غیرفعال تا تکمیل بازنویسی
    
    # ✅ ماژول پنل خانواده (M3) - اسپرینت ۳
    'src.modules.family_panel',
    'src.modules.reviews',
    'src.modules.leads',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # ✅ Middlewareهای ریهان (M14)
    'src.core.middleware.FeatureFlagMiddleware',
    'src.core.middleware.AuditLogMiddleware',
    
    # ✅ Middlewareهای RBAC (M5)
    'src.modules.rbac.middleware.RbacMiddleware',
]

ROOT_URLCONF = 'src.config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'src' / 'templates'],
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

WSGI_APPLICATION = 'src.config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ✅ تنظیمات محلی ایران (مطابق ADR-001 و CENTRAL-STORY)
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True
USE_L10N = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ✅ تنظیمات REST Framework (مطابق ADR-003)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# ✅ تنظیمات لاگینگ
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'core': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
    },
}


# ═══════════════════════════════════════════════════════════════
# تنظیمات پرداخت کارت‌به‌کارت (ADR-005 + D-067)
# ═══════════════════════════════════════════════════════════════

# Gateway پیش‌فرض برای MVP: کارت‌به‌کارت
PAYMENT_GATEWAY = 'MANUAL'

# اطلاعات حساب مقصد برای کارت‌به‌کارت
CARD_TO_CARD_CONFIG = {
    'card_number': '6037-9975-XXXX-XXXX',  # TODO: شماره کارت واقعی را وارد کنید
    'card_holder': 'عبدالحسین فهیمی',      # نام دارنده حساب
    'bank_name': 'بانک ملی',              # نام بانک
    'iban': '',                           # شبا (اختیاری)
}

# آستانه اجباری رسید (بالای این مبلغ، آپلود رسید اجباری است)
# اگر 0 باشد، رسید همیشه اختیاری است (مطابق D-067 پیش‌فرض)
RECEIPT_REQUIRED_ABOVE = 0  # تومان

# URL فرانت‌اند برای callback
FRONTEND_URL = 'http://rihan360.ir'
