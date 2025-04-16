from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.base.serializers import CustomSerializer


class LoginSerializer(CustomSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    refresh_token = serializers.CharField(read_only=True)
    access_token = serializers.CharField(read_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(self.context.get("request"), email=email, password=password)

        if not user:
            raise CustomExceptionError(code=404, detail=_("email or password was wrong!!!"))

        if not user.is_active:
            raise CustomExceptionError(code=404, detail=_("User was not active."))

        refresh = RefreshToken.for_user(user)

        return {
            "refresh_token": str(refresh),
            "access_token": str(refresh.access_token)
        }
