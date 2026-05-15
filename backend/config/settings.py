"""
Django 项目配置 — 数据库、缓存、文件存储、搜索、AI 服务、日志。
所有敏感信息通过 .env 环境变量注入，默认值适用于本地开发。
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---------- 核心 ----------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "travel-sharing-dev-secret-key-2026-demo-project")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver").split(",")
    if host.strip()
]
if "*" in ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["*"]

# ---------- 应用注册 ----------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "apps.users",
    "apps.travel",
    "apps.social",
    "apps.planner",
    "apps.ai",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.RequestLoggingMiddleware",
]

# ---------- 中间件 + 模板 ----------
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
    }
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------- 数据库（MySQL / SQLite） ----------
db_engine = os.getenv("DJANGO_DB_ENGINE", "sqlite").lower()
if db_engine == "mysql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DJANGO_DB_NAME", "travel_sharing_platform"),
            "HOST": os.getenv("DJANGO_DB_HOST", "8.137.70.186"),
            "PORT": int(os.getenv("DJANGO_DB_PORT", "3306")),
            "USER": os.getenv("DJANGO_DB_USER", "remote"),
            "PASSWORD": os.getenv("DJANGO_DB_PASSWORD", "123456"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / os.getenv("DJANGO_DB_NAME", "db.sqlite3"),
        }
    }

# ---------- Redis 缓存 ----------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("DJANGO_REDIS_URL", "redis://127.0.0.1:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT": 600,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------- 国际化 ----------
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"

USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- DRF + JWT ----------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": (
        "config.api.StandardJSONRenderer",
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOW_ALL_ORIGINS = os.getenv("DJANGO_CORS_ALLOW_ALL_ORIGINS", "True").lower() == "true"

if CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = []
    CSRF_TRUSTED_ORIGINS = []
else:
    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "DJANGO_CORS_ALLOWED_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]
    CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy()

# ---------- Minio 对象存储 ----------
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "8.137.70.186:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "travel-sharing")
MINIO_PUBLIC_BASE = os.getenv(
    "MINIO_PUBLIC_BASE",
    f"http{'s' if MINIO_SECURE else ''}://{MINIO_ENDPOINT}/{MINIO_BUCKET}",
)

# ---------- Elasticsearch ----------
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "travel_destinations")
ELASTICSEARCH_ENABLED = os.getenv("ELASTICSEARCH_ENABLED", "True").lower() == "true"

# ---------- AI 服务（Kimi + 千问） ----------
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
KIMI_MODEL = os.getenv("KIMI_MODEL", "kimi-k2.5")
KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1/chat/completions")

QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")
QWEN_BASE_URL = os.getenv(
    "QWEN_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
)

# ---------- 日志 ----------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s %(name)s:%(lineno)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "app.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "standard",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.request": {
            "handlers": ["console", "file"],
            "level": "WARNING",
        },
        "apps": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
        },
    },
}

import logging
import os as _os
log_dir = BASE_DIR / "logs"
if not _os.path.exists(log_dir):
    _os.makedirs(log_dir)
