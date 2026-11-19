"""Django settings for the Sakay.ph backend.

Every secret and every environment-specific value is read from `.env` via
django-environ. Nothing in this file should need to change between a
developer machine and the submission build.
"""

from datetime import timedelta
from pathlib import Path

import environ

# ── Paths ──────────────────────────────────────────────────────
# settings.py is at backend/config/settings.py, so BASE_DIR is backend/.
BASE_DIR = Path(__file__).resolve().parent.parent
# The repository root, one level above backend/.
ROOT_DIR = BASE_DIR.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_TIME_ZONE=(str, "Asia/Manila"),
    # Host port published by docker-compose.yml (3307:3306) — a native MySQL 8.4
    # service already owns host port 3306 on the development machine.
    MYSQL_PORT=(int, 3307),
    SIMULATE_PAYMENTS=(bool, True),
    SIMULATE_OTP=(bool, True),
    OTP_TTL_SECONDS=(int, 300),
)

# Read the repository-root .env, not one inside backend/.
environ.Env.read_env(ROOT_DIR / ".env")

# ── Core ───────────────────────────────────────────────────────
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# ── Applications ───────────────────────────────────────────────
INSTALLED_APPS = [
    "daphne",  # must precede staticfiles so runserver uses ASGI

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "channels",

    "apps.core",
    "apps.accounts",
    "apps.rides",
    "apps.payments",
    "apps.safety",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must precede CommonMiddleware
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# ── Database ───────────────────────────────────────────────────
# PyMySQL is registered as MySQLdb in config/__init__.py — see Step 1.06.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("MYSQL_DATABASE"),
        "USER": env("MYSQL_USER"),
        "PASSWORD": env("MYSQL_PASSWORD"),
        "HOST": env("MYSQL_HOST"),
        "PORT": env("MYSQL_PORT"),
        "OPTIONS": {
            # utf8mb4 end to end. Tagalog diacritics and the emoji transport
            # icons both need 4-byte UTF-8; utf8mb3 silently truncates them.
            "charset": "utf8mb4",
            # Fail loudly on a strict-mode violation rather than silently
            # truncating a value that is too long for its column.
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "CONN_MAX_AGE": 60,
        "TEST": {
            "NAME": "test_sakayph",
            "CHARSET": "utf8mb4",
            "COLLATION": "utf8mb4_unicode_ci",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Passwords ──────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalisation ───────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE")
USE_I18N = True
# Store UTC, display Asia/Manila. Turning this off is the classic source of
# an eight-hour error in every duration the app reports.
USE_TZ = True

# ── Static and media ───────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── Django REST Framework ──────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,  # token_blacklist app is not installed
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Sakay.ph API",
    "DESCRIPTION": (
        "Isang App, Lahat ng Sakyan. Multi-mode ride-hailing for the Philippines. "
        "CCS670 capstone."
    ),
    "VERSION": "0.2.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ── CORS ───────────────────────────────────────────────────────
# The Vite dev server is a different origin from Django, so without this
# every request from the frontend fails in the browser.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True

# ── Channels and Redis ─────────────────────────────────────────
# One Redis container, two logical databases: db 0 for the channel layer,
# db 1 for the cache. They are separated so a cache flush cannot drop a
# live WebSocket group.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("REDIS_URL")],
        },
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_CACHE_URL"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "sakayph",
    }
}

# ── Application flags ──────────────────────────────────────────
SIMULATE_PAYMENTS = env("SIMULATE_PAYMENTS")
SIMULATE_OTP = env("SIMULATE_OTP")
OTP_TTL_SECONDS = env("OTP_TTL_SECONDS")

# ── Logging ────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        # Set to DEBUG when a WebSocket will not connect.
        "django.channels": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# ── Authentication ─────────────────────────────────────────────
# The domain's own USER table is Django's auth user model (Option A, D-19 in
# steps/PROGRESS.md). Set before the first migration — changing it afterwards
# means rebuilding the database.
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]
