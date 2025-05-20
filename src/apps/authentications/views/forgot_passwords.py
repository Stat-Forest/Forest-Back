from drf_spectacular.utils import extend_schema
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from apps.base.views import CustomGenericAPIView
from apps.authentications.serializers import (SendResetCodeSerializer,
                                              VerifyResetCodeSerializer,
                                              NewPasswordSerializer)


@extend_schema(tags=["authentications"])
class SendResetCodeAPIView(CustomGenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = SendResetCodeSerializer

    def post(self, request):
        serializer = SendResetCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "We sent verify code."})


@extend_schema(tags=["authentications"])
class VerifyCodeAPIView(CustomGenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyResetCodeSerializer

    def post(self, request):
        serializer = VerifyResetCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = serializer.create_tokens()
        return Response(tokens)


@extend_schema(tags=["authentications"])
class NewPasswordAPIView(CustomGenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NewPasswordSerializer

    def post(self, request):
        serializer = NewPasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password was changed successfully."})