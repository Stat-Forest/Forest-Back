from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=60),
    'AUTH_HEADER_TYPES': ('Bearer',),
}