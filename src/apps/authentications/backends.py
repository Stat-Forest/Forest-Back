import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger(__name__)
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
            # Foydalanuvchi yo'q bo'lganda ham hash hisoblanadi — javob vaqti
            # bo'yicha email/login mavjudligini aniqlab bo'lmasin (audit C1)
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # Katta-kichik harf bilan farqlanadigan dublikat login/email — 500 o'rniga
            # rad etiladi (audit L2/F8); admin dublikatni tuzatishi kerak
            logger.warning("Login: '%s' uchun bir nechta foydalanuvchi topildi (iexact dublikat)", ident)
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None