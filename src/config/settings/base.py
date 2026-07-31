import os
import socket
from pathlib import Path
from dotenv import load_dotenv

from datetime import timedelta

load_dotenv()

# ===============================
# BASE CONFIG
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ["SECRET_KEY"]

PASSWORD_RESET_TOKEN_LIFETIME = timedelta(minutes=10)

DEBUG = os.environ.get("DEBUG", "False") == "True"

CORS_ALLOW_CREDENTIALS = True

DEFAULT_FROM_EMAIL="urmoninfo@gmail.com"

CORS_ALLOWED_ORIGINS = [
    "https://forest.yutori.uz",
    "https://www.forest.yutori.uz",
    "https://stat-urmon.uz",
    "https://www.stat-urmon.uz",
    "http://localhost:5173",
    "http://localhost:5174",
]

# files will be installed here
EXPORT_ROOT = os.path.join(BASE_DIR, "exports")

ALLOWED_HOSTS = [
    "forest.yutori.uz", "www.forest.yutori.uz",
    "93.188.84.164", "localhost", "127.0.0.1",
    "stat-urmon.uz", "www.stat-urmon.uz",
]

CSRF_TRUSTED_ORIGINS = [
    "https://forest.yutori.uz",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "https://stat-urmon.uz",
]

# ===============================
# 📦 INSTALLED_APPS
# ===============================
INSTALLED_APPS = [
    # 3rd party
    "daphne",
    "modeltranslation",
    "jazzmin",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_yasg",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "debug_toolbar",
    "channels",

    # Django defaults
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Custom apps
    "apps.authentications.apps.AuthenticationsConfig",
    "apps.base.apps.BaseConfig",
    "apps.users.apps.UsersConfig",
    "apps.reports.apps.ReportsConfig",
    "apps.general.apps.GeneralConfig",
    "apps.sum.apps.SumConfig",
    "apps.report_statistics.apps.ReportStatisticsConfig",
    "apps.e_imzo.apps.EImzoConfig",
    "apps.logs.apps.LogsConfig",
    "apps.information_analytical.apps.InformationAnalyticalConfig",
    "apps.report_admin_stat.apps.ReportAdminStatConfig",
    "apps.ai.apps.AiConfig",
    "apps.chat.apps.ChatsConfig"
]

# ===============================
# ⚙ MIDDLEWARE
# ===============================
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    # CustomMiddleWare for Enter Admin
    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.logs.middleware.CurrentUserMiddleware",
]

ROOT_URLCONF = "config.urls"

# ===============================
# 🧩 TEMPLATES
# ===============================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"

# ===============================
# 🧱 DATABASES & AUTH
# ===============================
AUTH_USER_MODEL = "users.CustomUser"

AUTHENTICATION_BACKENDS = [
    "apps.authentications.backends.EmailBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "apps.authentications.service.password_validators.StrongPasswordValidator",
    },
]

# ===============================
# 🗂️ STATIC & MEDIA
# ===============================
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ===============================
# 🌐 LANGUAGE & TIMEZONE
# ===============================
LANGUAGE_CODE = "uz"  # ✅ O'zbek tili asosiy qilib belgilandi
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Qo‘llab-quvvatlanadigan tillar
LANGUAGES = [
    ("uz", "O'zbekcha"),
    ("ru", "Русский"),
    ("en", "English"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",  # ✅ Tarjima fayllari shu papkada bo‘ladi
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ===============================
# 🔐 REST FRAMEWORK & SPECTACULAR
# ===============================
# base.py
SPECTACULAR_SETTINGS = {
    "TITLE": "Forest API",
    "DESCRIPTION": "API documentation for the Forest application",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
}

# ===============================
# 🧩 INTERNAL IPs
# ===============================
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips]

# ===============================
# 🔥 REDIS (if used)
# ===============================
REDIS_HOST = os.environ.get("REDIS_HOST", "forest_redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB_CHANNELS = 2

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_CHANNELS}"],
        },
    },
}

