"""
Django settings for Kh Resin Art Backend.

Django + Django REST Framework
Local development + Render deployment ready.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def env_list(name, default=""):
    """
    Read comma-separated env variables safely.
    Example:
    ALLOWED_HOSTS=localhost,127.0.0.1,.onrender.com
    """
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


# =========================
# Core settings
# =========================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-local-dev-key-change-this-in-production",
)

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,.onrender.com",
)


# =========================
# Cloudinary media storage
# =========================
# Local: if Cloudinary env vars are missing, uploaded images stay in /media/
# Render: add Cloudinary env vars so product images do not disappear after redeploy.

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

USE_CLOUDINARY = all([
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
])

if USE_CLOUDINARY:
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
        "API_KEY": CLOUDINARY_API_KEY,
        "API_SECRET": CLOUDINARY_API_SECRET,
    }


# =========================
# Applications
# =========================

INSTALLED_APPS = []

if USE_CLOUDINARY:
    INSTALLED_APPS += [
        "cloudinary",
    ]

INSTALLED_APPS += [
    # Optional later for nicer admin:
    # "jazzmin",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party apps
    "rest_framework",
    "corsheaders",

    # Local apps
    "catalog",
]


# =========================
# Middleware
# =========================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# =========================
# Database
# =========================
# Local: SQLite
# Render: PostgreSQL using DATABASE_URL

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}


# =========================
# Password validation
# =========================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# =========================
# Language / Timezone
# =========================

LANGUAGE_CODE = "ar"
TIME_ZONE = "Asia/Damascus"

USE_I18N = True
USE_TZ = True


# =========================
# Static files
# =========================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


# =========================
# Media files
# =========================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# =========================
# Storage backends
# =========================
# Cloudinary handles uploaded media files.
# WhiteNoise serves collected static files such as Django admin CSS on Render.

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

if USE_CLOUDINARY:
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
else:
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }

WHITENOISE_ROOT = STATIC_ROOT

# =========================
# Django REST Framework
# =========================

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}


# =========================
# CORS / CSRF
# =========================

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ",".join([
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://kh-resin-art.pages.dev",
    ]),
)

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    ",".join([
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://*.onrender.com",
    ]),
)


# =========================
# Production security
# =========================

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # خليها False بالبداية حتى ما نعمل redirect loop على Render.
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False") == "True"


# =========================
# Default primary key
# =========================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"