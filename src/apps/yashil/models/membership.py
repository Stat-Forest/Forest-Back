"""
Modul a'zoligi (TZ §2, §20 `organization_members`; javoblar Б1–Б4).

Bir foydalanuvchi bir nechta kabinetga ega bo'lishi mumkin; har a'zolikda
tayyorlash/imzolash huquqi va vakolat asosi alohida. `CustomUser.organization`
o'zgarmaydi — modulga kirish faqat shu yozuvlar orqali.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.utils.validators import validate_document_file
from apps.yashil.models._base import PeriodMixin, ValidatedModel
from apps.yashil.models.reference import Mahalla, SupplierProfile, UnionUnit


class YashilMembership(ValidatedModel, PeriodMixin):
    class MemberType(models.TextChoices):
        MAHALLA = "mahalla", "Mahalla"
        UNION = "union", "Mahallalar uyushmasi"
        SUPPLIER = "supplier", "Yetkazib beruvchi (xo'jalik / DM)"
        OBSERVER = "observer", "Agentlik kuzatuvchisi"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="yashil_memberships")
    member_type = models.CharField(max_length=10, choices=MemberType.choices)
    mahalla = models.ForeignKey(Mahalla, on_delete=models.PROTECT, null=True, blank=True, related_name="memberships")
    union_unit = models.ForeignKey(UnionUnit, on_delete=models.PROTECT, null=True, blank=True, related_name="memberships")
    organization = models.ForeignKey("general.Organization", on_delete=models.PROTECT, null=True, blank=True, related_name="yashil_memberships")
    can_prepare = models.BooleanField(default=True, verbose_name="Tayyorlaydi")
    can_sign = models.BooleanField(default=False, verbose_name="Imzolaydi")
    position_title = models.CharField(max_length=200, blank=True, verbose_name="Lavozim")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Aloqa raqami")
    authority_doc_number = models.CharField(max_length=100, blank=True, verbose_name="Vakolat hujjati raqami")
    authority_doc_date = models.DateField(null=True, blank=True, verbose_name="Vakolat hujjati sanasi")
    authority_file = models.FileField(
        upload_to="documents/yashil/authority/", null=True, blank=True,
        validators=[validate_document_file], verbose_name="Vakolat hujjati fayli",
    )
    observer_scope = models.JSONField(
        default=dict, blank=True, verbose_name="Kuzatuvchi ko'lami",
        help_text='{} — respublika; {"regions": [..kodlar..]} yoki {"districts": [..kodlar..]}',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Modul a'zoligi"
        verbose_name_plural = "Modul a'zoliklari"
        ordering = ["user__last_name", "member_type"]

    def clean(self):
        super().clean()
        t = self.MemberType
        need = {t.MAHALLA: "mahalla", t.UNION: "union_unit", t.SUPPLIER: "organization"}.get(self.member_type)
        for fname in ("mahalla", "union_unit", "organization"):
            value = getattr(self, f"{fname}_id")
            if fname == need and not value:
                raise ValidationError({fname: "Bu a'zolik turi uchun majburiy."})
            if fname != need and value:
                raise ValidationError({fname: "Bu a'zolik turi uchun to'ldirilmaydi."})
        if self.member_type == t.SUPPLIER:
            if not SupplierProfile.objects.filter(organization_id=self.organization_id, is_active_supplier=True).exists():
                raise ValidationError({"organization": "Tashkilotda faol yetkazib beruvchi profili yo'q."})
        if self.member_type == t.OBSERVER and (self.can_prepare or self.can_sign):
            raise ValidationError({"can_sign": "Kuzatuvchi tayyorlamaydi va imzolamaydi."})
        if self.observer_scope and not isinstance(self.observer_scope, dict):
            raise ValidationError({"observer_scope": "Lug'at (dict) bo'lishi kerak."})

    @property
    def cabinet_name(self) -> str:
        if self.member_type == self.MemberType.MAHALLA:
            return str(self.mahalla)
        if self.member_type == self.MemberType.UNION:
            return str(self.union_unit)
        if self.member_type == self.MemberType.SUPPLIER:
            return str(self.organization)
        return "Kuzatuvchi"

    @property
    def supplier_type(self) -> str | None:
        if self.member_type != self.MemberType.SUPPLIER or not self.organization_id:
            return None
        profile = getattr(self.organization, "supplier_profile", None)
        return profile.supplier_type if profile else None

    def __str__(self):
        return f"{self.user} — {self.get_member_type_display()}: {self.cabinet_name}"
