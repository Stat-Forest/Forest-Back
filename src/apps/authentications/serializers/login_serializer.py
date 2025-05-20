from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.base.serializers import CustomSerializer

User = get_user_model()


class LoginSerializer(CustomSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").lower()
        password = attrs.get("password")

        if not email or not password:
            raise CustomExceptionError(code=400, detail="Email or password was required")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CustomExceptionError(code=404, detail="User not found.")

        if not user.check_password(password):
            raise CustomExceptionError(code=404, detail="Email or password was mistake.")

        if not user.is_active:
            raise CustomExceptionError(code=403, detail="This user is not active.")

        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.id,
            "email": user.email,
            "role": getattr(user, "role", "admin")
        }