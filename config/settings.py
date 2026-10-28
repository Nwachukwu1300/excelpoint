"""Django settings for the Excelpoint project.

This module centralizes configuration for local development. It loads
environment variables, declares installed apps and middleware, defines the
database and static/media handling, and configures integrations such as the
Django REST Framework and Celery.

Each section is documented to explain why a setting exists and how to adjust
it as the project evolves.
"""

import os
import sys
from pathlib import Path
from celery.schedules import crontab
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# Off unless explicitly enabled, so a missing .env never ships debug pages
DEBUG = os.getenv('DEBUG', 'False').lower() in ('1', 'true', 'yes')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError('DJANGO_SECRET_KEY must be set when DEBUG is off')
    SECRET_KEY = 'django-insecure-local-dev-only'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,0.0.0.0,testserver').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'storages',  # Required for S3 storage
    # our apps
    'users',
    'subjects',
    'retrieval',  # Stage 1: Retrieval System Optimization
    'reasoning',  # Stage 2: Agentic Reasoning Pipeline
    'rest_framework',
    'rest_framework_simplejwt',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # serves /static/ (the built app) when DEBUG is off
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

AUTH_USER_MODEL = 'users.User' 

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'excelpoint_dev'),
        'USER': os.getenv('DB_USER', 'mmesoma'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5433'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static'
]
STATIC_ROOT = BASE_DIR / 'staticfiles'  # collectstatic output, served by whitenoise
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},  # gzip/brotli copies
}

# A shared Redis cache when one is configured (production), so rate limits hold across workers;
# otherwise Django's per-process memory cache (local runs and tests)
if os.getenv('CACHE_URL'):
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': os.getenv('CACHE_URL')}}

# Behind a reverse proxy (Caddy in docker-compose.yml): how many proxies add to X-Forwarded-For.
# 0 means none, so the header is ignored and nobody can fake their address
NUM_PROXIES = int(os.getenv('NUM_PROXIES', '0'))
if NUM_PROXIES:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # the proxy terminates HTTPS
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0'))  # set once HTTPS is confirmed working

# Email (password reset). Any SMTP service: Gmail with an app password now, Resend once there's a domain.
# Without EMAIL_HOST, emails are printed to the console instead (local development).
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_BACKEND = ('django.core.mail.backends.smtp.EmailBackend' if EMAIL_HOST
                 else 'django.core.mail.backends.console.EmailBackend')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = EMAIL_PORT == 587
EMAIL_USE_SSL = EMAIL_PORT == 465
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL') or (f'ExcelPoint <{EMAIL_HOST_USER}>' if EMAIL_HOST_USER else 'ExcelPoint <noreply@localhost>')
PASSWORD_RESET_TIMEOUT = 2 * 60 * 60  # reset links work for 2 hours

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # Only used for local storage

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# The only backend, so every password check (app sign-in, admin, DRF) shares the failed-attempt cap
AUTHENTICATION_BACKENDS = ['users.backends.RateLimitedModelBackend']

REST_FRAMEWORK = {
    'NUM_PROXIES': NUM_PROXIES,  # DRF's default (None) would trust a forged X-Forwarded-For
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',  # the app signs in with sessions only
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # Each chat question costs LLM calls; cap them per user (views opt in with throttle_scope = 'llm').
    # shortcut: counts live in the default per-process cache, so N server workers allow N x the rate;
    # point CACHES at Redis before running multiple workers in production.
    'DEFAULT_THROTTLE_RATES': {
        'llm': os.getenv('LLM_RATE_LIMIT', '60/hour'),
    },
}

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True

# Authentication URLs
LOGIN_URL = '/app/login'  # the React sign-in page
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Celery Configuration
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Scheduled jobs: run `celery -A config beat` alongside the worker
CELERY_BEAT_SCHEDULE = {
    'flashcard-review-reminders': {
        'task': 'subjects.tasks.send_review_reminders',
        'schedule': crontab(hour=8, minute=0),
    },
}

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').replace('\n', '').strip()
if sys.argv[1:2] == ['test']:
    OPENAI_API_KEY = ''  # tests must mock LLM calls; never spend real tokens from the test suite
# Newer models need max_completion_tokens (not max_tokens); every call uses that name
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-5.4-mini')

# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
GOOGLE_OAUTH_REDIRECT_URI = os.getenv('GOOGLE_OAUTH_REDIRECT_URI', 'http://localhost:8000/users/google/callback/')

# Google OAuth Scopes
GOOGLE_OAUTH_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

# AI Chatbot Response Caching Configuration
CACHE_ENABLED = os.getenv('CACHE_ENABLED', 'True').lower() == 'true'
CACHE_TTL_HOURS = int(os.getenv('CACHE_TTL_HOURS', '48'))  # Default 48 hours
CACHE_MAX_SIZE = int(os.getenv('CACHE_MAX_SIZE', '10000'))  # Maximum cached entries
CACHE_LOG_LEVEL = os.getenv('CACHE_LOG_LEVEL', 'INFO')  # Logging verbosity

# Cache performance settings
CACHE_MIN_HIT_COUNT = int(os.getenv('CACHE_MIN_HIT_COUNT', '1'))  # Minimum hits before considering popular
CACHE_CLEANUP_INTERVAL_HOURS = int(os.getenv('CACHE_CLEANUP_INTERVAL_HOURS', '24'))  # Cleanup frequency

# Storage Configuration
STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'local')  # 'local' or 's3'

# S3 Configuration
if STORAGE_BACKEND == 's3':
    # S3 Settings
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'eu-north-1')
    AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN')
    
    # S3 Storage Settings
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_DEFAULT_ACL = 'private'
    AWS_S3_FILE_OVERWRITE = False  # same-named uploads get their own object, so deleting one can't remove another
    AWS_QUERYSTRING_AUTH = True  # objects are private, so URLs must be signed
    
    # Use S3 for media files
    # DEFAULT_FILE_STORAGE was removed in Django 5.1
    STORAGES['default'] = {'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage'}
    MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/'
    
    # Ensure MEDIA_ROOT is not used when S3 is enabled
    MEDIA_ROOT = None


# ============================================================================
# Stage 2: Agentic Reasoning Pipeline Configuration
# ============================================================================

# Reasoning Pipeline Settings
REASONING_DEFAULT_PIPELINE = os.getenv('REASONING_DEFAULT_PIPELINE', 'default')
REASONING_FAITHFULNESS_THRESHOLD = float(os.getenv('REASONING_FAITHFULNESS_THRESHOLD', '0.7'))
REASONING_MAX_RETRIES = int(os.getenv('REASONING_MAX_RETRIES', '2'))

# Confidence Scoring Weights (must sum to 1.0 for base weights, excluding penalties)
REASONING_CONFIDENCE_FAITHFULNESS_WEIGHT = float(os.getenv('REASONING_CONFIDENCE_FAITHFULNESS_WEIGHT', '0.40'))
REASONING_CONFIDENCE_MEAN_SIMILARITY_WEIGHT = float(os.getenv('REASONING_CONFIDENCE_MEAN_SIMILARITY_WEIGHT', '0.25'))
REASONING_CONFIDENCE_TOP_SIMILARITY_WEIGHT = float(os.getenv('REASONING_CONFIDENCE_TOP_SIMILARITY_WEIGHT', '0.15'))
REASONING_CONFIDENCE_FIRST_ATTEMPT_BONUS = float(os.getenv('REASONING_CONFIDENCE_FIRST_ATTEMPT_BONUS', '0.10'))
REASONING_CONFIDENCE_UNSUPPORTED_PENALTY = float(os.getenv('REASONING_CONFIDENCE_UNSUPPORTED_PENALTY', '0.05'))
REASONING_CONFIDENCE_MAX_UNSUPPORTED_PENALTY = float(os.getenv('REASONING_CONFIDENCE_MAX_UNSUPPORTED_PENALTY', '0.20'))

# LLM Settings for Reasoning (can override global OPENAI_MODEL)
REASONING_LLM_MODEL = os.getenv('REASONING_LLM_MODEL', OPENAI_MODEL)
REASONING_REWRITER_TEMPERATURE = float(os.getenv('REASONING_REWRITER_TEMPERATURE', '0.3'))
REASONING_GENERATOR_TEMPERATURE = float(os.getenv('REASONING_GENERATOR_TEMPERATURE', '0.4'))
REASONING_VERIFIER_TEMPERATURE = float(os.getenv('REASONING_VERIFIER_TEMPERATURE', '0.1'))

# Stage 3 evaluation: the LLM judge adds one call per answer, so it's opt-in
EVAL_LLM_JUDGE = os.getenv('EVAL_LLM_JUDGE', 'False').lower() in ('1', 'true', 'yes')
EVAL_JUDGE_MODEL = os.getenv('EVAL_JUDGE_MODEL', REASONING_LLM_MODEL)


# Logging: app loggers to the console (Celery and runserver both capture stdout)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {'format': '%(asctime)s %(levelname)s %(name)s %(message)s'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'standard'},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        app: {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False}
        for app in ('subjects', 'retrieval', 'reasoning', 'users')
    },
}
