from rest_framework import status
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from apps.authentications.serializers.login_serializer import LoginSerializer
from apps.base.views import CustomGenericAPIView


@extend_schema(tags=["authentications"])
class LoginAPIView(CustomGenericAPIView):
    permission_classes = []
    authentication_classes = []
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
