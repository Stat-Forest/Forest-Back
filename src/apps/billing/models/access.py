"""
Billing foydalanuvchilari: kim qaysi xo'jaliklar doirasida ishlaydi.

- `billing_user` — faqat `BillingUserAccess.xojaliklar` doirasida (o'qish va yozish).
- `billing_super` / super_admin / superuser — cheklovsiz (yozuv shart emas).
"""
from django.conf import settings
from django.db import models

from apps.base.models import AbstractBaseModel
from apps.users.models import CustomUser

from .reference import Xojalik

BILLING_ROLES = (CustomUser.Role.BILLING_USER, CustomUser.Role.BILLING_SUPER)


class BillingUserAccess(AbstractBaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="billing_access",
        verbose_name="Foydalanuvchi",
    )
    xojaliklar = models.ManyToManyField(
        Xojalik, blank=True, related_name="billing_users", verbose_name="Biriktirilgan xo'jaliklar",
    )

    class Meta:
        verbose_name = "Billing foydalanuvchi doirasi"
        verbose_name_plural = "Billing foydalanuvchilar doirasi"

    def __str__(self) -> str:
        return str(self.user)


class BillingUser(CustomUser):
    """Billing adminkasi uchun proxy: faqat `billing_user`/`billing_super` rolidagilar."""

    class Meta:
        proxy = True
        verbose_name = "Billing foydalanuvchisi"
        verbose_name_plural = "Billing foydalanuvchilari"
