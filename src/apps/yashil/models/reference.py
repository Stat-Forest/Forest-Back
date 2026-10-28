"""
Ma'lumotnomalar: mahalla, uyushma bo'linmasi, yetkazib beruvchi profili,
biriktirishlar, mavsum, obyekt turi (TZ §3, §16, §20; javoblar A1–A6, Г1).

Viloyat/tuman — `billing.Region/District` (MHOBT kodlari bilan).
O'rmon xo'jaligi va DM — `general.Organization` + `SupplierProfile`.
"""
from django.core.exceptions import ValidationError
from django.db import models

from apps.yashil.models._base import PeriodMixin, ValidatedModel, ensure_single_active


class Mahalla(ValidatedModel, PeriodMixin):
    source_code = models.CharField(
        max_length=50, unique=True, null=True, blank=True, verbose_name="Manba kodi",
        help_text="Rasmiy ro'yxatdagi kod (SOATO yagona kod emas)",
    )
    name = models.CharField(max_length=200, verbose_name="Nomi")
    region = models.ForeignKey("billing.Region", on_delete=models.PROTECT, related_name="yashil_mahallalar", verbose_name="Viloyat")
    district = models.ForeignKey("billing.District", on_delete=models.PROTECT, related_name="yashil_mahallalar", verbose_name="Tuman")
    address = models.CharField(max_length=500, blank=True, verbose_name="Manzil")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    extra = models.JSONField(default=dict, blank=True, verbose_name="Qo'shimcha")

    class Meta:
        verbose_name = "Mahalla"
        verbose_name_plural = "Mahallalar"
        ordering = ["district__code", "name"]
        indexes = [models.Index(fields=["district", "name"])]
        constraints = [models.UniqueConstraint(fields=["district", "name"], name="yashil_mahalla_district_name_uniq")]
        permissions = [("manage_module", "Yashil mahalla modulini boshqarish")]

    def clean(self):
        super().clean()
        if self.district_id and self.region_id and self.district.region_id != self.region_id:
            raise ValidationError({"district": "Tuman tanlangan viloyatga tegishli emas."})

    def __str__(self):
        return self.name


class UnionUnit(ValidatedModel):
    """Mahallalar uyushmasi bo'linmasi (tuman/viloyat/respublika)."""

    class Level(models.TextChoices):
        REPUBLIC = "republic", "Respublika"
        REGION = "region", "Viloyat"
        DISTRICT = "district", "Tuman"

    name = models.CharField(max_length=300, verbose_name="Nomi")
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.DISTRICT, verbose_name="Daraja")
    region = models.ForeignKey("billing.Region", on_delete=models.PROTECT, null=True, blank=True, related_name="yashil_union_units")
    district = models.ForeignKey("billing.District", on_delete=models.PROTECT, null=True, blank=True, related_name="yashil_union_units")
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="children")
    stir = models.CharField(max_length=9, blank=True, verbose_name="STIR")
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    class Meta:
        verbose_name = "Uyushma bo'linmasi"
        verbose_name_plural = "Uyushma bo'linmalari"
        ordering = ["level", "name"]

    def clean(self):
        super().clean()
        if self.level == self.Level.DISTRICT and not self.district_id:
            raise ValidationError({"district": "Tuman darajasidagi bo'linma uchun tuman majburiy."})
        if self.level == self.Level.REGION and not self.region_id:
            raise ValidationError({"region": "Viloyat darajasidagi bo'linma uchun viloyat majburiy."})
        if self.district_id and not self.region_id:
            self.region = self.district.region

    def __str__(self):
        return self.name


class MahallaUnionRoute(ValidatedModel, PeriodMixin):
    """Mahalla -> buyurtmani ko'rib chiqadigan uyushma bo'linmasi (bir vaqtda bittasi)."""

    mahalla = models.ForeignKey(Mahalla, on_delete=models.CASCADE, related_name="union_routes")
    union_unit = models.ForeignKey(UnionUnit, on_delete=models.PROTECT, related_name="mahalla_routes")
    source_doc = models.CharField(max_length=200, blank=True, verbose_name="Asos")

    class Meta:
        verbose_name = "Mahalla -> uyushma marshruti"
        verbose_name_plural = "Mahalla -> uyushma marshrutlari"
        ordering = ["mahalla__name", "-valid_from"]

    def clean(self):
        super().clean()
        if self.mahalla_id and self.union_unit_id:
            ensure_single_active(self, field="mahalla", label="Mahalla uyushma marshruti")

    def __str__(self):
        return f"{self.mahalla} -> {self.union_unit}"


class SupplierProfile(ValidatedModel):
    """`general.Organization` ning yetkazib beruvchi sifatidagi profili."""

    class SupplierType(models.TextChoices):
        FOREST = "forest", "O'rmon xo'jaligi"
        DM = "dm", "Yashil bog'larni tashkil etish DM"

    organization = models.OneToOneField("general.Organization", on_delete=models.CASCADE, related_name="supplier_profile", verbose_name="Tashkilot")
    supplier_type = models.CharField(max_length=10, choices=SupplierType.choices, verbose_name="Turi")
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="branches", verbose_name="Bosh tashkilot (DM bo'linmasi uchun)")
    official_name = models.CharField(max_length=300, blank=True, verbose_name="Rasmiy nomi")
    stir = models.CharField(max_length=9, blank=True, verbose_name="STIR")
    is_active_supplier = models.BooleanField(default=True, verbose_name="Yetkazib beruvchi sifatida faol")
    service_regions = models.ManyToManyField("billing.Region", blank=True, related_name="yashil_dm_profiles", verbose_name="Xizmat viloyatlari (DM)")
    service_districts = models.ManyToManyField("billing.District", blank=True, related_name="yashil_dm_profiles", verbose_name="Xizmat tumanlari (DM)")

    class Meta:
        verbose_name = "Yetkazib beruvchi profili"
        verbose_name_plural = "Yetkazib beruvchi profillari"
        ordering = ["supplier_type", "organization__name"]

    def clean(self):
        super().clean()
        if self.parent_id:
            if self.supplier_type != self.SupplierType.DM:
                raise ValidationError({"parent": "Bosh tashkilot faqat DM bo'linmasi uchun."})
            if self.parent.supplier_type != self.SupplierType.DM:
                raise ValidationError({"parent": "Bosh tashkilot DM bo'lishi kerak."})
            if self.parent_id == self.pk:
                raise ValidationError({"parent": "Tashkilot o'zining bo'linmasi bo'la olmaydi."})

    @property
    def display_name(self) -> str:
        return self.official_name or self.organization.name

    def __str__(self):
        return f"{self.display_name} ({self.get_supplier_type_display()})"


class SupplierAssignment(ValidatedModel, PeriodMixin):
    """Mahalla -> asosiy o'rmon xo'jaligi (bir vaqtda bittasi)."""

    mahalla = models.ForeignKey(Mahalla, on_delete=models.CASCADE, related_name="supplier_assignments")
    organization = models.ForeignKey("general.Organization", on_delete=models.PROTECT, related_name="yashil_assignments", verbose_name="O'rmon xo'jaligi")
    source_doc = models.CharField(max_length=200, blank=True, verbose_name="Asos")

    class Meta:
        verbose_name = "Mahalla -> xo'jalik biriktirishi"
        verbose_name_plural = "Mahalla -> xo'jalik biriktirishlari"
        ordering = ["mahalla__name", "-valid_from"]

    def clean(self):
        super().clean()
        if self.organization_id:
            profile = SupplierProfile.objects.filter(organization_id=self.organization_id).first()
            if not profile or profile.supplier_type != SupplierProfile.SupplierType.FOREST:
                raise ValidationError({"organization": "Faqat o'rmon xo'jaligi (yetkazib beruvchi profili bilan) biriktiriladi."})
        if self.mahalla_id and self.organization_id:
            ensure_single_active(self, field="mahalla", label="Mahalla xo'jalik biriktirishi")

    def __str__(self):
        return f"{self.mahalla} -> {self.organization}"


class Season(ValidatedModel):
    class Kind(models.TextChoices):
        SPRING = "spring", "Bahor"
        AUTUMN = "autumn", "Kuz"
        YEAR = "year", "Yil davomida"

    year = models.PositiveSmallIntegerField(verbose_name="Yil")
    kind = models.CharField(max_length=10, choices=Kind.choices, verbose_name="Turi")
    date_from = models.DateField(verbose_name="Boshlanishi")
    date_to = models.DateField(verbose_name="Tugashi")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Mavsum"
        verbose_name_plural = "Mavsumlar"
        ordering = ["-year", "date_from"]
        constraints = [models.UniqueConstraint(fields=["year", "kind"], name="yashil_season_year_kind_uniq")]

    def clean(self):
        super().clean()
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValidationError({"date_to": "Tugash sanasi boshlanishdan oldin."})

    @property
    def label_cyr(self) -> str:
        return f"{self.year} {dict(SEASON_LABELS_CYR)[self.kind]}"

    def __str__(self):
        return f"{self.year} {self.get_kind_display()}"


SEASON_LABELS_CYR = [("spring", "баҳор"), ("autumn", "куз"), ("year", "йил давомида")]


class ObjectType(ValidatedModel):
    """Yashil hudud turi (javob Г1)."""

    code = models.CharField(max_length=40, unique=True)
    name_cyr = models.CharField(max_length=200)
    name_lat = models.CharField(max_length=200)
    requires_note = models.BooleanField(default=False, verbose_name="Izoh majburiy")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Obyekt turi"
        verbose_name_plural = "Obyekt turlari"
        ordering = ["order", "code"]

    def __str__(self):
        return self.name_lat
