import os
import socket
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ===============================
# BASE CONFIG
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = False

# CORS_ALLOW_ALL_ORIGINS = True

# CORS_ALLOW_CREDENTIALS = True

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
    "https://localhost:5173",
    "https://localhost:5174",
    "http://stat-urmon.uz",
    "https://stat-urmon.uz",
    "http://localhost:8000"
]

# ===============================
# 📦 INSTALLED_APPS
# ===============================
INSTALLED_APPS = [
    # 3rd party
    "modeltranslation",
    "jazzmin",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_yasg",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "debug_toolbar",

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

    #CustomMiddleWare for Enter Admin
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

# ===============================
# 🧱 DATABASES & AUTH
# ===============================
AUTH_USER_MODEL = "users.CustomUser"

# ===============================
# 🗂️ STATIC & MEDIA
# ===============================
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

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
SPECTACULAR_SETTINGS = {
    "TITLE": "Forest API",
    "DESCRIPTION": "API documentation for the Forest application",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# ===============================
# 🧩 INTERNAL IPs
# ===============================
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips]

# ===============================
# 🔥 REDIS (if used)
# ===============================
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

