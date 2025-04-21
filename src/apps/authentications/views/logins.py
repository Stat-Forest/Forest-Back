from rest_framework import status
from rest_framework.response import Response

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.authentications.serializers.login_serializer import LoginSerializer
from apps.base.views import CustomGenericAPIView


class LoginAPIView(CustomGenericAPIView):
    permission_classes = []
    authentication_classes = []

    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={200: openapi.Response("Login successful", LoginSerializer)}
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
