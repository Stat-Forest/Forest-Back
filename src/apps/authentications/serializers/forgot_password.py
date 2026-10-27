import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.utils import timezone

from rest_framework import serializers

from apps.authentications.tasks import send_reset_password_email_task
from apps.utils.services.security import hash_reset_code, constant_time_equal
from apps.authentications.service.token_denylist import revoke_user_tokens_issued_before
from apps.utils.services.tokens import (
    create_password_reset_access_token,
    blacklist_user_refresh_tokens,
)
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.logs.models import HistoryActionJournal

User = get_user_model()


NO_RESET_EMAIL_DOMAINS = ("@billing-urmon.uz",)


class SendResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    SEND_TIMEOUT = 60
    CODE_TTL = 600

    def validate_email(self, value):
        self.normalized_email = value.strip().lower()
        return self.normalized_email

    def save(self):
        email = self.normalized_email
        throttle_key = f"reset_code_send_timeout:{email}"

        if cache.get(throttle_key):
            raise CustomExceptionError(
                code=429,
                detail="Kod allaqachon yuborilgan. Birozdan keyin qayta urinib ko‘ring."
            )

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user and email.endswith(NO_RESET_EMAIL_DOMAINS):
            # Eski billing'dan email'siz ko'chirilgan inspektorlar: domen yopilgach boshqa
            # egaga o'tsa, tiklash kodi orqali akkauntni egallash mumkin edi (audit H1).
            # Javob bir xil — mavjudligi oshkor bo'lmaydi.
            user = None

        if user:
            code = f"{secrets.randbelow(900000) + 100000}"
            hashed_code = hash_reset_code(email, code)

            cache.set(f"reset_code_hash:{email}", hashed_code, timeout=self.CODE_TTL)
            send_reset_password_email_task.delay(email, code)

        cache.set(throttle_key, True, timeout=self.SEND_TIMEOUT)


class VerifyResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    MAX_ATTEMPTS = 5
    BLOCK_TIMEOUT = 60 * 15

    def validate(self, data):
        email = data["email"].strip().lower()
        code = data["code"].strip()

        attempt_key = f"reset_code_attempts:{email}"
        block_key = f"reset_code_blocked:{email}"
        code_hash_key = f"reset_code_hash:{email}"

        if cache.get(block_key):
            raise CustomExceptionError(
                code=429,
                detail="Juda ko‘p xato urinish. 15 daqiqadan keyin qayta urinib ko‘ring."
            )

        cached_hash = cache.get(code_hash_key)
        incoming_hash = hash_reset_code(email, code)

        if not cached_hash or not constant_time_equal(cached_hash, incoming_hash):
            attempts = cache.get(attempt_key, 0) + 1
            cache.set(attempt_key, attempts, timeout=self.BLOCK_TIMEOUT)

            if attempts >= self.MAX_ATTEMPTS:
                cache.set(block_key, True, timeout=self.BLOCK_TIMEOUT)
                cache.delete(attempt_key)
                cache.delete(code_hash_key)
                raise CustomExceptionError(
                    code=429,
                    detail="5 marta xato urinish. 15 daqiqadan keyin qayta urinib ko‘ring."
                )

            remaining = self.MAX_ATTEMPTS - attempts
            raise CustomExceptionError(
                code=400,
                detail=f"Kod xato yoki muddati tugagan. Yana {remaining} ta urinish qoldi."
            )

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            raise CustomExceptionError(code=400, detail="Kod xato yoki muddati tugagan.")

        cache.delete(attempt_key)
        cache.delete(block_key)
        cache.delete(code_hash_key)

        self.user = user
        self.email = email
        return data

    def create_tokens(self):
        access_token = create_password_reset_access_token(self.user)

        HistoryActionJournal.objects.create(
            user=self.user,
            action="change",
            model_name="User",
            change_message="Parolni tiklash kodi tasdiqlandi.",
            object_repr=f"Foydalanuvchi: {self.user.first_name} {self.user.last_name} - Role: {self.user.role}",
            created_at=timezone.now(),
        )

        return {
            "access": access_token,
        }


class NewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=100, write_only=True)
    confirm_password = serializers.CharField(max_length=100, write_only=True)

    def validate(self, data):
        user = self.context["request"].user

        if data["password"] != data["confirm_password"]:
            raise CustomExceptionError(code=400, detail="Parollar mos kelmadi.")

        try:
            validate_password(data["password"], user=user)
        except Exception as exc:
            messages = getattr(exc, "messages", None) or [str(exc)]
            raise CustomExceptionError(code=400, detail=messages)

        return data

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["password"])
        user.last_activity = timezone.now()
        user.save(update_fields=["password", "last_activity"])

        blacklist_user_refresh_tokens(user)
        # Oldin berilgan access tokenlar ham (boshqa qurilmalar) yaroqsiz (audit C3)
        revoke_user_tokens_issued_before(user.id)

        HistoryActionJournal.objects.create(
            user=user,
            action="change",
            model_name="User",
            change_message="Parol forgot-password orqali yangilandi.",
            object_repr=f"Foydalanuvchi: {user.first_name} {user.last_name} - Role: {user.role}",
            created_at=timezone.now(),
        )