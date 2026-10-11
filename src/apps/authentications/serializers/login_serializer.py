from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.base.serializers import CustomSerializer
from apps.logs.models import HistoryActionJournal

User = get_user_model()


class LoginSerializer(CustomSerializer):
    # Email yoki login (eski billing inspektorlari username bilan kiradi)
    email = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)

    MAX_ATTEMPTS = 5
    ATTEMPT_WINDOW = 60 * 10
    BLOCK_TIMEOUT = 60 * 15

    default_error_message = _("Email/login yoki parol noto‘g‘ri.")

    def validate(self, attrs):
        request = self.context.get("request")
        email = (attrs.get("email") or "").strip().lower()
        password = attrs.get("password") or ""

        if not email or not password:
            raise CustomExceptionError(code=400, detail=_("Email/login va parol majburiy."))

        block_key = self._block_key(email, request)
        if cache.get(block_key):
            raise CustomExceptionError(
                code=429,
                detail=_("Juda ko‘p xato urinish. 15 daqiqadan keyin qayta urinib ko‘ring.")
            )

        attempt_key = self._attempt_key(email, request)
        attempts = cache.get(attempt_key, 0)

        user = authenticate(request=request, username=email, password=password)

        if user is None:
            attempts += 1
            cache.set(attempt_key, attempts, timeout=self.ATTEMPT_WINDOW)
            self._check_attempts_limit(email, request, attempts)
            raise CustomExceptionError(code=401, detail=self.default_error_message)


        cache.delete(attempt_key)
        cache.delete(block_key)

        user.last_activity = timezone.now()
        user.save(update_fields=["last_activity"])

        refresh = RefreshToken.for_user(user)

        HistoryActionJournal.objects.create(
            user=user,
            action="login",
            model_name="User",
            change_message="Tizimga login qilindi.",
            object_repr=f"Foydalanuvchi: {user.first_name} {user.last_name} - Role: {user.role}",
            created_at=timezone.now(),
        )

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.id,
            "email": user.email,
            "role": getattr(user, "role", None),
        }

    def _client_ident(self, request):
        if request is None:
            return "unknown"

        x_real_ip = request.META.get("HTTP_X_REAL_IP")
        if x_real_ip:
            return x_real_ip.strip()

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR", "unknown")

    def _attempt_key(self, email, request):
        ident = self._client_ident(request)
        return f"login_attempts:{email}:{ident}"

    def _block_key(self, email, request):
        ident = self._client_ident(request)
        return f"login_block:{email}:{ident}"

    def _check_attempts_limit(self, email, request, attempts):
        if attempts >= self.MAX_ATTEMPTS:
            cache.set(self._block_key(email, request), True, timeout=self.BLOCK_TIMEOUT)
            raise CustomExceptionError(
                code=429,
                detail=_("5 marta xato urinish. 15 daqiqadan so‘ng qayta urinib ko‘ring.")
            )