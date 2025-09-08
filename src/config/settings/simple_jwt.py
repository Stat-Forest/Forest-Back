from datetime import timedelta


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(seconds=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}