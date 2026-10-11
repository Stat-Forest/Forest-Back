from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        ident = (username or kwargs.get("email") or "").strip().lower()
        if not ident or not password:
            return None

        # "@" bo'lsa email, aks holda login (CustomUser.username — eski billing inspektorlari)
        lookup = {"email__iexact": ident} if "@" in ident else {"username__iexact": ident}
        try:
            user = UserModel.objects.get(**lookup)
        except UserModel.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None