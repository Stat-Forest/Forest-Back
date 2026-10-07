"""
Ijara billing ma'lumotnomalari: viloyat, tuman, xo'jalik, bo'lim, ijarachi
va tur ro'yxatlari. Stat'ning CustomUser/Organization modellariga
bog'lanmaydi (faqat Xojalik.organization ixtiyoriy FK).
"""
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from apps.base.models import AbstractBaseModel

inn_validator = RegexValidator(regex=r"^\d{9}$", message="INN faqat 9 ta raqamdan iborat bo'lishi kerak.")
pinfl_validator = RegexValidator(regex=r"^\d{14}$", message="JSHSHIR faqat 14 ta raqamdan iborat bo'lishi kerak.")


class Region(AbstractBaseModel):
    name = models.CharField(max_length=100, unique=True, verbose_name="Viloyat nomi")
    code = models.CharField(max_length=10, unique=True, verbose_name="Viloyat kodi")
    billing_id = models.IntegerField(
        null=True, blank=True, verbose_name="Eski billing ID",
        help_text="billing-urmon.uz dagi Region.id — fixture'larni moslash uchun",
    )

    class Meta:
        verbose_name = "Viloyat (billing)"
        verbose_name_plural = "Viloyatlar (billing)"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class District(AbstractBaseModel):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="districts", verbose_name="Viloyat")
    code = models.CharField(max_length=10, verbose_name="Tuman kodi")
    name = models.CharField(max_length=100, verbose_name="Tuman nomi")

    class Meta:
        verbose_name = "Tuman (billing)"
        verbose_name_plural = "Tumanlar (billing)"
        ordering = ["region__code", "code"]
        constraints = [models.UniqueConstraint(fields=["region", "code"], name="billing_district_region_code_uniq")]

    def __str__(self) -> str:
        return f"{self.region.name} - {self.name}"


class Xojalik(AbstractBaseModel):
    """Davlat o'rmon xo'jaligi (billing'dagi Department)."""

    name = models.CharField(max_length=300, unique=True, verbose_name="Nomi")
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="xojaliklar", verbose_name="Viloyat")
    code = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Kodi",
        help_text="Shartnoma raqami prefiksi, masalan 23:02:06",
    )
    inn = models.CharField(max_length=9, null=True, blank=True, unique=True, validators=[inn_validator], verbose_name="INN")
    account_detail = models.TextField(null=True, blank=True, verbose_name="Hisob ma'lumotlari")
    organization = models.ForeignKey(
        "general.Organization", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="billing_xojaliklar", verbose_name="Stat tashkiloti",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    class Meta:
        verbose_name = "Xo'jalik"
        verbose_name_plural = "Xo'jaliklar"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Bolim(AbstractBaseModel):
    """Xo'jalik bo'limi (billing'dagi DepartmentBranch)."""

    name = models.CharField(max_length=150, verbose_name="Nomi")
    xojalik = models.ForeignKey(Xojalik, on_delete=models.CASCADE, related_name="bolimlar", verbose_name="Xo'jalik")

    class Meta:
        verbose_name = "Bo'lim"
        verbose_name_plural = "Bo'limlar"
        ordering = ["xojalik__name", "name"]
        constraints = [models.UniqueConstraint(fields=["xojalik", "name"], name="billing_bolim_xojalik_name_uniq")]

    def __str__(self) -> str:
        return f"{self.xojalik.name} / {self.name}"


class Renter(AbstractBaseModel):
    """Ijarachi — jismoniy (JSHSHIR) yoki yuridik (INN) shaxs."""

    pinfl = models.CharField(max_length=14, null=True, blank=True, unique=True, validators=[pinfl_validator], verbose_name="JSHSHIR")
    stir = models.CharField(max_length=9, null=True, blank=True, unique=True, validators=[inn_validator], verbose_name="INN")
    full_name = models.CharField(max_length=255, verbose_name="F.I.Sh. / Yuridik shaxs nomi")
    passport = models.CharField(max_length=24, null=True, blank=True, verbose_name="Pasport")
    phone = models.CharField(max_length=128, null=True, blank=True, verbose_name="Telefon")
    per_adr = models.CharField(max_length=255, null=True, blank=True, verbose_name="Manzil")
    citizenship = models.CharField(max_length=255, null=True, blank=True, verbose_name="Fuqaroligi")
    birth_place = models.CharField(max_length=255, null=True, blank=True, verbose_name="Tug'ilgan joyi")
    is_legal_entity = models.BooleanField(default=False, verbose_name="Yuridik shaxs")
    legal_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Yuridik shaxs nomi")

    class Meta:
        verbose_name = "Ijarachi"
        verbose_name_plural = "Ijarachilar"
        ordering = ["full_name"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.stir or self.pinfl})"

    def clean(self):
        super().clean()
        if not self.pinfl and not self.stir:
            raise ValidationError({"pinfl": "INN yoki JSHSHIR'dan kamida bittasi kiritilishi shart."})

    def save(self, *args, **kwargs):
        # Bo'sh satr unique maydonlarda NULL sifatida saqlanadi
        self.pinfl = self.pinfl or None
        self.stir = self.stir or None
        super().save(*args, **kwargs)


class AbstractType(AbstractBaseModel):
    name = models.CharField(max_length=255, verbose_name="Nomi")
    description = models.CharField(max_length=1024, null=True, blank=True, verbose_name="Tavsif")
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children", verbose_name="Asosiy tur",
    )

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class LandType(AbstractType):
    class Meta(AbstractType.Meta):
        verbose_name = "Yer turi"
        verbose_name_plural = "Yer turlari"


class ActivityType(AbstractType):
    class Meta(AbstractType.Meta):
        verbose_name = "Faoliyat turi"
        verbose_name_plural = "Faoliyat turlari"


class PrivilegeType(AbstractType):
    month = models.PositiveIntegerField(null=True, blank=True, verbose_name="Imtiyoz muddati (oy)")

    class Meta(AbstractType.Meta):
        verbose_name = "Imtiyoz turi"
        verbose_name_plural = "Imtiyoz turlari"
