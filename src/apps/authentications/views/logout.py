from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentications.service.refresh_cookie import clear_refresh_cookie, refresh_from_request
from apps.authentications.service.token_denylist import revoke_access_token


@extend_schema(tags=["authentications"])
class LogoutAPIView(APIView):
    """
    Tizimdan chiqish: joriy access token darhol bekor qilinadi (cache
    denylist), yuborilgan refresh token blacklist'ga tushadi. Shundan keyin
    ikkala token bilan ham hech qanday so'rov o'tmaydi.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        revoke_access_token(request.auth)

        refresh = refresh_from_request(request)  # body yoki HttpOnly cookie (audit A5)
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass  # allaqachon yaroqsiz / blacklist'da — baribir chiqamiz

        return clear_refresh_cookie(Response(status=status.HTTP_204_NO_CONTENT))
