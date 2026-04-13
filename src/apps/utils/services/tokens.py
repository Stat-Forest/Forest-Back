from django.conf import settings

from rest_framework_simplejwt.tokens import AccessToken


def create_password_reset_access_token(user) -> str:
    token = AccessToken()
    token["user_id"] = str(user.id)
    token["pwd_reset"] = True
    token.set_exp(lifetime=getattr(settings, "PASSWORD_RESET_TOKEN_LIFETIME"))
    return str(token)


def blacklist_user_refresh_tokens(user) -> None:
    """
    Blacklist all outstanding refresh tokens for this user.
    Requires rest_framework_simplejwt.token_blacklist in INSTALLED_APPS.
    """
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
    except Exception:
        return

    tokens = OutstandingToken.objects.filter(user=user)

    for token in tokens:
        BlacklistedToken.objects.get_or_create(token=token)