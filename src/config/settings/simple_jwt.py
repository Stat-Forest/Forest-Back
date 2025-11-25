from datetime import timedelta


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(seconds=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(seconds=30),
    'AUTH_HEADER_TYPES': ('Bearer',),
}