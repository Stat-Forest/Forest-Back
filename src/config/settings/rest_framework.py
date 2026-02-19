REST_FRAMEWORK = {
    # -------------------------------------------------------------------------
    # Authentication
    # JWT-only authentication. Session auth is disabled to prevent CSRF risks.
    # -------------------------------------------------------------------------
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],

    # -------------------------------------------------------------------------
    # Permissions
    # All endpoints require authentication by default.
    # Override per-view with @permission_classes([AllowAny]) where public access is needed.
    # -------------------------------------------------------------------------
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    # -------------------------------------------------------------------------
    # Throttling
    # Protects against brute-force, scraping, and DoS attacks.
    #
    # Rates:
    #   anon  — unauthenticated users (stricter)
    #   user  — authenticated users
    #   burst — short-window spike protection (optional, add ScopedRateThrottle per view)
    #
    # To apply scoped throttle on a specific view:
    #   throttle_classes = [ScopedRateThrottle]
    #   throttle_scope = 'burst'
    # -------------------------------------------------------------------------
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/min',    # Unauthenticated: 30 requests per minute
        'user': '120/min',   # Authenticated: 120 requests per minute
        'burst': '10/min',   # Scope-based burst limit for sensitive endpoints (login, OTP, etc.)
    },

    # -------------------------------------------------------------------------
    # Renderers
    # BrowsableAPIRenderer is disabled in production to prevent UI-based info leakage.
    # Enable it only in DEBUG mode (see bottom of this block).
    # -------------------------------------------------------------------------
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        # BrowsableAPIRenderer intentionally excluded — enabled below only in DEBUG
    ],

    # -------------------------------------------------------------------------
    # Parsers
    # Only accept necessary content types. Limits attack surface.
    # -------------------------------------------------------------------------
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],

    # -------------------------------------------------------------------------
    # Pagination
    # Forces all list responses to be paginated.
    # Prevents large data dumps from a single request.
    # -------------------------------------------------------------------------
    'DEFAULT_PAGINATION_CLASS': 'apps.base.pagination.CustomPageNumberPagination',
    'PAGE_SIZE': 10,

    # -------------------------------------------------------------------------
    # Filtering & Search
    # -------------------------------------------------------------------------
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
    ],
    'SEARCH_PARAM': 'search',
    'ORDERING_PARAM': 'ordering',

    # -------------------------------------------------------------------------
    # Exception Handling
    # Custom handler normalizes error responses and avoids stack trace leakage.
    # -------------------------------------------------------------------------
    'EXCEPTION_HANDLER': 'apps.base.handlers.custom_exception_handler',
    'NON_FIELD_ERRORS_KEY': 'non_field_errors',

    # -------------------------------------------------------------------------
    # Schema / OpenAPI
    # -------------------------------------------------------------------------
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'SCHEMA_COERCE_PATH_PK': True,
    'SCHEMA_COERCE_METHOD_NAMES': {
        'retrieve': 'read',
        'destroy': 'delete',
    },

    # -------------------------------------------------------------------------
    # Content Negotiation & Metadata
    # -------------------------------------------------------------------------
    'DEFAULT_CONTENT_NEGOTIATION_CLASS': 'rest_framework.negotiation.DefaultContentNegotiation',
    'DEFAULT_METADATA_CLASS': 'rest_framework.metadata.SimpleMetadata',
    'DEFAULT_VERSIONING_CLASS': None,
    'DEFAULT_VERSION': None,
    'ALLOWED_VERSIONS': None,
    'VERSION_PARAM': 'version',

    # -------------------------------------------------------------------------
    # Proxy configuration
    # Set NUM_PROXIES to the actual number of reverse proxies (nginx, etc.)
    # in front of your app so throttling uses the real client IP, not proxy IP.
    # Example: 1 if you have one nginx in front.
    # -------------------------------------------------------------------------
    'NUM_PROXIES': 1,

    # -------------------------------------------------------------------------
    # Anonymous / Unauthenticated user representation
    # -------------------------------------------------------------------------
    'UNAUTHENTICATED_USER': 'django.contrib.auth.models.AnonymousUser',
    'UNAUTHENTICATED_TOKEN': None,

    # -------------------------------------------------------------------------
    # View introspection helpers
    # -------------------------------------------------------------------------
    'VIEW_NAME_FUNCTION': 'rest_framework.views.get_view_name',
    'VIEW_DESCRIPTION_FUNCTION': 'rest_framework.views.get_view_description',

    # -------------------------------------------------------------------------
    # Testing
    # -------------------------------------------------------------------------
    'TEST_REQUEST_RENDERER_CLASSES': [
        'rest_framework.renderers.MultiPartRenderer',
        'rest_framework.renderers.JSONRenderer',
    ],
    'TEST_REQUEST_DEFAULT_FORMAT': 'multipart',

    # -------------------------------------------------------------------------
    # URL & Format settings
    # -------------------------------------------------------------------------
    'URL_FORMAT_OVERRIDE': 'format',
    'FORMAT_SUFFIX_KWARG': 'format',
    'URL_FIELD_NAME': 'url',

    # -------------------------------------------------------------------------
    # Date / Time formats
    # -------------------------------------------------------------------------
    'DATE_FORMAT': '%d.%m.%Y',
    'DATE_INPUT_FORMATS': ['%d.%m.%Y'],
    'DATETIME_FORMAT': '%d.%m.%Y %H:%M',
    'DATETIME_INPUT_FORMATS': ['%d.%m.%Y %H:%M'],
    'TIME_FORMAT': '%H:%M',
    'TIME_INPUT_FORMATS': ['%H:%M'],

    # -------------------------------------------------------------------------
    # Encoding & JSON behavior
    # STRICT_JSON=True rejects NaN/Infinity values which can cause parser errors.
    # COERCE_DECIMAL_TO_STRING=True prevents float precision bugs in JSON output.
    # -------------------------------------------------------------------------
    'UNICODE_JSON': True,
    'COMPACT_JSON': True,
    'STRICT_JSON': True,
    'COERCE_DECIMAL_TO_STRING': True,   # CHANGED: True prevents Decimal precision bugs
    'UPLOADED_FILES_USE_URL': True,

    # -------------------------------------------------------------------------
    # Browsable API cutoff
    # -------------------------------------------------------------------------
    'HTML_SELECT_CUTOFF': 1000,
    'HTML_SELECT_CUTOFF_TEXT': "More than {count} items...",
}


# -------------------------------------------------------------------------
# Enable BrowsableAPIRenderer only in DEBUG mode.
# This prevents exposing the interactive API UI in production,
# which could leak endpoint structure and facilitate manual probing.
# -------------------------------------------------------------------------
from django.conf import settings as django_settings  # noqa: E402
if django_settings.DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'].append(
        'rest_framework.renderers.BrowsableAPIRenderer'
    )