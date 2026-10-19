from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from drf_spectacular.utils import extend_schema

from apps.base.views import CustomGenericAPIView
from apps.authentications.serializers.login_serializer import LoginSerializer
from apps.authentications.service.throttles import LoginIPThrottle, LoginEmailThrottle
from apps.authentications.service.refresh_cookie import set_refresh_cookie


@extend_schema(tags=["authentications"])
class LoginAPIView(CustomGenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginIPThrottle, LoginEmailThrottle]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)
        # Refresh token HttpOnly cookie'da ham (audit A5). Body'dagi `refresh`
        # eski frontend uchun vaqtincha qoladi — yangi frontend uni saqlamaydi.
        refresh = serializer.validated_data.get("refresh")
        if refresh:
            set_refresh_cookie(response, refresh)
        return response