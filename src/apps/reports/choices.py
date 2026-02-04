from django.db import models
from django.utils.translation import gettext_lazy as _

class UserRoleChoices(models.TextChoices):
    SUPER_ADMIN = "super_admin", _("Super Admin")
    RAHBARIYAT = "rahbariyat", _("Rahbariyat")
    BOLIM_ADMIN = "bolim_admin", _("Bo`lim Admin")
    TASHKILOT_RAHBARI = "tashkilot_rahbari", _("Tashkilot rahbari")
    TASHKILOT_HODIMI = "tashkilot_hodimi", _("Tashkilot hodimi")
    HUDUDIY_BOSHQARMA = "hududiy_boshqarma", _("Hududiy boshqarma")
