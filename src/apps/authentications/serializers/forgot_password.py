import random

from django.core.cache import cache
from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentications.utils import send_reset_password_email
from apps.base.exceptions.exception_files import CustomExceptionError

User = get_user_model()


class SendResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise CustomExceptionError(code=404, detail="This email was not loginned before.")
        return value

    def save(self):
        email = self.validated_data["email"]
        code = str(random.randint(100000, 999999))
        cache.set(f"reset_code:{email}", code, timeout=600)
        send_reset_password_email(email, code)


class VerifyResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    MAX_ATTEMPTS = 3
    BLOCK_TIMEOUT = 60 * 30

    def validate(self, data):
        email = data["email"]
        code = data["code"]

        attempt_key = f"reset_code_attempts:{email}"
        block_key = f"reset_code_blocked:{email}"

        if cache.get(block_key):
            raise CustomExceptionError(
                code=429,
                detail="Siz 3 marta xato kiritdingiz. 30 daqiqadan keyin qayta urinib ko'ring."
            )

        cached_code = cache.get(f"reset_code:{email}")

        if cached_code is None or cached_code != code:
            attempts = cache.get(attempt_key, 0) + 1
            cache.set(attempt_key, attempts, timeout=self.BLOCK_TIMEOUT)

            remaining = self.MAX_ATTEMPTS - attempts

            if attempts >= self.MAX_ATTEMPTS:
                cache.set(block_key, True, timeout=self.BLOCK_TIMEOUT)
                cache.delete(attempt_key)
                cache.delete(f"reset_code:{email}")
                raise CustomExceptionError(
                    code=429,
                    detail="Siz 3 marta xato kiritdingiz. 30 daqiqadan keyin qayta urinib ko'ring."
                )

            raise CustomExceptionError(
                code=400,
                detail=f"Kod xato yoki muddati o'tgan. Sizda yana {remaining} ta urinish qoldi."
            )

        cache.delete(attempt_key)
        cache.delete(block_key)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CustomExceptionError(code=404, detail="Foydalanuvchi topilmadi.")

        self.user = user
        return data


class NewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=100, write_only=True)
    confirm_password = serializers.CharField(max_length=100, write_only=True)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise CustomExceptionError(code=404, detail="passwords was not equal.")
        return data

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["password"])
        user.save()