from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from apps.logs.models import HistoryActionJournal
from apps.authentications.service.token_denylist import revoke_user_tokens_issued_before
from apps.utils.services.tokens import blacklist_user_refresh_tokens
from apps.base.exceptions.exception_files import CustomExceptionError


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    PASSWORD_RULES_MESSAGE = (
        "Parol kamida 8 ta belgidan iborat bo‘lishi, katta-kichik harf, "
        "raqam va maxsus belgi qatnashishi kerak."
    )

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise CustomExceptionError(code=400, detail="Eski parol noto‘g‘ri.")
        return value

    def validate(self, data):
        user = self.context["request"].user

        if data["new_password"] != data["confirm_password"]:
            raise CustomExceptionError(code=400, detail="Yangi parollar mos emas.")

        if data["old_password"] == data["new_password"]:
            raise CustomExceptionError(
                code=400,
                detail="Yangi parol eski parol bilan bir xil bo‘lmasligi kerak."
            )

        try:
            validate_password(data["new_password"], user=user)
        except Exception:
            raise CustomExceptionError(
                code=400,
                detail=self.PASSWORD_RULES_MESSAGE
            )

        return data

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.last_activity = timezone.now()
        user.save(update_fields=["password", "last_activity"])

        blacklist_user_refresh_tokens(user)
        # Oldin berilgan access tokenlar ham (boshqa qurilmalar) yaroqsiz (audit C3)
        revoke_user_tokens_issued_before(user.id)

        HistoryActionJournal.objects.create(
            user=user,
            action="change",
            model_name="User",
            change_message="Parol change-password orqali yangilandi.",
            object_repr=f"Foydalanuvchi: {user.first_name} {user.last_name} - Role: {user.role}",
            created_at=timezone.now(),
        )

        return user