from drf_spectacular.utils import extend_schema
from apps.authentications.service.token_denylist import revoke_access_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken

from apps.authentications.serializers import (
    SendResetCodeSerializer,
    VerifyResetCodeSerializer,
    NewPasswordSerializer,
)
from apps.base.views import CustomGenericAPIView
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.authentications.service.throttles import ResetCodeIPThrottle


@extend_schema(tags=["authentications"])
class SendResetCodeAPIView(CustomGenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ResetCodeIPThrottle]
    serializer_class = SendResetCodeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Agar email tizimda mavjud bo‘lsa, tasdiqlash kodi yuborildi."},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["authentications"])
class VerifyCodeAPIView(CustomGenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ResetCodeIPThrottle]
    serializer_class = VerifyResetCodeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = serializer.create_tokens()
        return Response(tokens, status=status.HTTP_200_OK)


@extend_schema(tags=["authentications"])
class NewPasswordAPIView(CustomGenericAPIView):
    permission_classes = [IsAuthenticated]
    allow_password_reset_token = True
    serializer_class = NewPasswordSerializer

    def post(self, request):
        validated_token = getattr(request, "auth", None)
        if not validated_token:
            raise CustomExceptionError(code=401, detail="Token topilmadi.")

        if not validated_token.get("pwd_reset"):
            raise InvalidToken("Ushbu token parolni tiklash uchun yaroqsiz.")

        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # pwd_reset tokeni bir martalik (audit C3)
        revoke_access_token(validated_token)

        return Response(
            {"detail": "Parol muvaffaqiyatli yangilandi."},
            status=status.HTTP_200_OK,
        )