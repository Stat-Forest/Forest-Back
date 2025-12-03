from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.base.serializers import CustomSerializer
from apps.logs.models import HistoryActionJournal
from django.utils import timezone

User = get_user_model()


class LoginSerializer(CustomSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").lower()
        password = attrs.get("password")

        if not email or not password:
            raise CustomExceptionError(code=400, detail=_("Email yokida parol majburiy"))

        block_key = f"login_block_{email}"
        if cache.get(block_key):
            raise CustomExceptionError(code=429, detail=_(
                "Juda koʻp urinishlar, 40 soniyadan keyin qayta urinib ko'ring.")
        )

        attempt_key = f"login_attempts_{email}"
        attempts = cache.get(attempt_key, 0)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            cache.set(attempt_key, attempts + 1, timeout=60)
            self._check_attempts_limit(email, attempts + 1)
            raise CustomExceptionError(code=404, detail=_("Foydalanuvchi topilmadi."))

        if not user.check_password(password):
            cache.set(attempt_key, attempts + 1, timeout=60)
            self._check_attempts_limit(email, attempts + 1)
            raise CustomExceptionError(code=404, detail=_("Email yokida parol xato kiritilgan."))

        if not user.is_active:
            raise CustomExceptionError(code=403, detail=_("This user is not active."))

        cache.delete(attempt_key)
        cache.delete(block_key)

        refresh = RefreshToken.for_user(user)
        HistoryActionJournal.objects.create(
            user=user,
            action="login",
            model_name="User",
            change_message="API orqali tizimga kirildi.",
            object_repr=f'Foydalanuvchi: {user.first_name} {user.last_name} Tashkiloti:{user.organization.name} role: {user.role} ',
            created_at=timezone.now()
        )

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.id,
            "email": user.email,
            "role": getattr(user, "role", "admin")
        }

    def _check_attempts_limit(self, email, attempts):
        if attempts >= 3:
            block_key = f"login_block_{email}"
            cache.set(block_key, True, timeout=40)  # ⛔ 40 soniyaga blok
            raise CustomExceptionError(code=429, detail="3 marta xato. Iltimos, 40 soniyadan so‘ng urinib ko‘ring.")