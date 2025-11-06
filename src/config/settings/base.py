import os
from pathlib import Path
from dotenv import load_dotenv
import socket

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = True

CORS_ALLOW_ALL_ORIGINS = True

ALLOWED_HOSTS = [
    'forest.yutori.uz', 'www.forest.yutori.uz',
    '93.188.84.164', 'localhost', '127.0.0.1',
    'stat-urmon.uz', 'www.stat-urmon.uz'
]

CSRF_TRUSTED_ORIGINS = [
    "https://forest.yutori.uz",
    "http://localhost:5173",
    "http://localhost:5174",
    "https://localhost:5173",
    "https://localhost:5174",
    "http://stat-urmon.uz",
    "https://stat-urmon.uz",
]

# ===============================
# 📦 INSTALLED_APPS
# ===============================
INSTALLED_APPS = [
    "modeltranslation",
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_yasg",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "debug_toolbar",
    # --- Custom apps ---
    "apps.authentications.apps.AuthenticationsConfig",
    "apps.base.apps.BaseConfig",
    "apps.users.apps.UsersConfig",
    "apps.reports.apps.ReportsConfig",
    "apps.general.apps.GeneralConfig",
    "apps.sum.apps.SumConfig",
    "apps.report_statistics.apps.ReportStatisticsConfig",
    "apps.e_imzo.apps.EImzoConfig",
    "apps.logs.apps.LogsConfig",  # ✅ Eng oxirida
]

# ===============================
# ⚙️ MIDDLEWARE
# ===============================
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
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
        "DIRS": [BASE_DIR / "templates"],  # agar `templates/` papkangiz bo‘lsa
        "APP_DIRS": True,  # ✅ Juda muhim — admin, jazzmin, debug_toolbar uchun
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",  # ✅ jazzmin uchun zarur
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ===============================
# 🎨 JAZZMIN SETTINGS
# ===============================
JAZZMIN_SETTINGS = {
    "site_title": "Forest Admin",
    "site_header": "Stat-Urmon",
    "site_brand": "Forest",
    "welcome_sign": "Stat-Urmon boshqaruv tizimi",
    "copyright": "© 2025 Stat-Urmon",
    "site_logo": None,
    "order_with_respect_to": [
        "auth",
        "users",
        "reports",
        "general",
        "sum",
        "report_statistics",
        "e_imzo",
        "logs",  # ✅ “Foydalanuvchi amallari tarixi” eng oxirida chiqadi
    ],
    "icons": {
        "auth": "fas fa-user-shield",
        "users": "fas fa-users",
        "reports": "fas fa-file-alt",
        "general": "fas fa-database",
        "sum": "fas fa-layer-group",
        "report_statistics": "fas fa-chart-bar",
        "e_imzo": "fas fa-signature",
        "logs": "fas fa-history",  # 🕓 Loglar uchun ikonka
    },
    "hide_models": [
        "auth.Group",  # 👈 "Groups" admin paneldan yashiriladi
    ],
}

# ===============================
# 🧱 DATABASES & AUTH
# ===============================
AUTH_USER_MODEL = "users.CustomUser"

# ===============================
# 🗂️ STATIC & MEDIA
# ===============================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ===============================
# ⏰ TIMEZONE & DEFAULTS
# ===============================
TIME_ZONE = "Asia/Tashkent"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ===============================
# 🔐 REST FRAMEWORK & SPECTACULAR
# ===============================
SPECTACULAR_SETTINGS = {
    'TITLE': 'Forest API',
    'DESCRIPTION': 'API documentation for the Forest application',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# ===============================
# 🧩 INTERNAL IPs
# ===============================
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips]

# ===============================
# 🔥 REDIS (if used)
# ===============================
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
