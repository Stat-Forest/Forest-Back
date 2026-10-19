from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenRefreshView

from apps.authentications.service.refresh_cookie import (
    REFRESH_COOKIE,
    clear_refresh_cookie,
    refresh_from_request,
    set_refresh_cookie,
)


@extend_schema(tags=["authentications"])
class CookieTokenRefreshView(TokenRefreshView):
    """
    Refresh token body'dan (eski mijozlar) yoki HttpOnly cookie'dan olinadi
    (audit A5). Cookie bilan kelgan so'rovda yangi refresh faqat cookie'ga
    yoziladi — javob body'sida qaytarilmaydi (JS uni ko'rmasin).
    """

    def post(self, request, *args, **kwargs):
        from_cookie = not request.data.get("refresh") and bool(request.COOKIES.get(REFRESH_COOKIE))
        refresh = refresh_from_request(request)
        if not refresh:
            return Response({"detail": "Refresh token yuborilmadi."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = self.get_serializer(data={"refresh": refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        data = dict(serializer.validated_data)
        new_refresh = data.get("refresh")
        response = Response(data, status=status.HTTP_200_OK)
        if new_refresh:
            set_refresh_cookie(response, new_refresh)
            if from_cookie:
                response.data.pop("refresh", None)
        return response
