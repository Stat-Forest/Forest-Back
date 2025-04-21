from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from apps.base.views import CustomGenericAPIView
from apps.authentications.serializers import (SendResetCodeSerializer,
                                              VerifyResetCodeSerializer,
                                              NewPasswordSerializer)


class SendResetCodeAPIView(CustomGenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = SendResetCodeSerializer

    @swagger_auto_schema(
        request_body=SendResetCodeSerializer,
        responses={200: openapi.Response("Code sent successfully")}
    )
    def post(self, request):
        serializer = SendResetCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "We sent verify code."})


class VerifyCodeAPIView(CustomGenericAPIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=VerifyResetCodeSerializer,
        responses={200: openapi.Response("Token created")}
    )
    def post(self, request):
        serializer = VerifyResetCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = serializer.create_tokens()
        return Response(tokens)


class NewPasswordAPIView(CustomGenericAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=NewPasswordSerializer,
        responses={200: openapi.Response("Password changed successfully")}
    )
    def post(self, request):
        serializer = NewPasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password was changed successfully."})