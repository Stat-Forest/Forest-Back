"""
Pilot uchun boshlang'ich ma'lumotlar — ishchi serverda, haqiqiy ma'lumot kelgunicha (D-29).

    python manage.py yashil_pilot_setup --find "Андижон"        # tuman kodlari va tashkilot ID'lari
    python manage.py yashil_pilot_setup --reference-only         # faqat kalendar, katalog, mavsum, obyekt turlari
    python manage.py yashil_pilot_setup --district <kod> --mahalla-name "<nom>" --forest <tashkilot ID>
        [--mahalla-code PILOT-001] [--dm <tashkilot ID>]

Qo'shadi (idempotent, bitta tranzaksiyada):
- ish kalendari 2026–2027: qonuniy sanasi o'zgarmas bayramlar (hayit kunlari va ko'chirilgan
  kunlar har yili e'lon qilinadi — «Ma'muriyat → Kalendar» orqali qo'shiladi);
- katalog va me'yorlar — PF-206 6-ilova namunasi (`yashil_seed_demo` bilan bir xil), mavsumlar, obyekt turlari;
- bitta pilot mahalla (billing'dagi mavjud tumanda), shu tuman uchun uyushma bo'linmasi;
- platformadagi mavjud tashkilotga o'rmon xo'jaligi profili, mahallani unga va bo'linmaga biriktirish.
Soxta tashkilot va foydalanuvchi yaratilmaydi; sinov hisoblari — `yashil_test_accounts`.
"""
from datetime import date

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.billing.models import District
from apps.general.models import Organization
from apps.yashil.management.commands.yashil_seed_demo import CATALOG, NORMS, OBJECT_TYPES
from apps.yashil.models import (
    CalendarDay, CatalogItem, Mahalla, MahallaUnionRoute, NormRule, ObjectType, Season, SupplierAssignment,
    SupplierProfile, UnionUnit,
)

VALID_FROM = date(2026, 1, 1)
SOURCE = "Mehnat kodeksi (sanasi o'zgarmas bayramlar); pilot"
CATALOG_REF = "ПФ-206, 6-илова (намуна)"
# Dam olish kunlari (Mehnat kodeksi): sanasi o'zgarmaydiganlari
FIXED_HOLIDAYS = {
    (1, 1): "Янги йил", (3, 8): "Хотин-қизлар куни", (3, 21): "Наврўз", (5, 9): "Хотира ва қадрлаш куни",
    (9, 1): "Мустақиллик куни", (10, 1): "Ўқитувчи ва мураббийлар куни", (12, 8): "Конституция куни",
}
YEARS = (2026, 2027)
SEASONS = [
    (2026, Season.Kind.AUTUMN, date(2026, 10, 1), date(2026, 12, 15)),
    (2027, Season.Kind.SPRING, date(2027, 3, 1), date(2027, 5, 31)),
    (2027, Season.Kind.AUTUMN, date(2027, 10, 1), date(2027, 12, 15)),
]


class Command(BaseCommand):
    help = "Yashil mahalla: pilot uchun kalendar, katalog va bitta mahalla (mavjud tuman va xo'jalikka)"

    def add_arguments(self, parser):
        parser.add_argument("--find", default="", help="Tuman va tashkilotlarni nom bo'yicha qidirish")
        parser.add_argument("--reference-only", action="store_true", help="Faqat kalendar, katalog, mavsum, obyekt turlari")
        parser.add_argument("--district", default="", help="Tuman kodi (billing ma'lumotnomasi)")
        parser.add_argument("--mahalla-name", default="", help="Mahalla nomi")
        parser.add_argument("--mahalla-code", default="PILOT-001", help="Mahalla kodi (standart PILOT-001)")
        parser.add_argument("--forest", default="", help="O'rmon xo'jaligi — platformadagi tashkilot ID")
        parser.add_argument("--dm", default="", help="Ixtiyoriy: DM — platformadagi tashkilot ID")

    def handle(self, *args, **opts):
        if opts["find"]:
            return self._find(opts["find"])
        if opts["reference_only"]:
            with transaction.atomic():
                self._reference()
            return self._done(None)
        missing = [name for name in ("district", "mahalla_name", "forest") if not opts[name]]
        if missing:
            raise CommandError("Kerak: " + ", ".join("--" + m.replace("_", "-") for m in missing) + " (yoki --reference-only / --find)")
        district = self._district(opts["district"])
        forest = self._org(opts["forest"], SupplierProfile.SupplierType.FOREST)
        dm = self._org(opts["dm"], SupplierProfile.SupplierType.DM) if opts["dm"] else None
        with transaction.atomic():
            self._reference()
            mahalla = self._mahalla(opts["mahalla_code"], opts["mahalla_name"], district)
            self._profile(forest, SupplierProfile.SupplierType.FOREST)
            if dm is not None:
                self._profile(dm, SupplierProfile.SupplierType.DM)
            unit = self._union_unit(district)
            if not SupplierAssignment.objects.filter(mahalla=mahalla, valid_to__isnull=True).exists():
                SupplierAssignment.objects.create(mahalla=mahalla, organization=forest, valid_from=VALID_FROM, source_doc="Pilot")
            if not MahallaUnionRoute.objects.filter(mahalla=mahalla, valid_to__isnull=True).exists():
                MahallaUnionRoute.objects.create(mahalla=mahalla, union_unit=unit, valid_from=VALID_FROM, source_doc="Pilot")
        self._done(mahalla)

    # ------------------------------------------------------------------ qidirish
    def _find(self, text):
        self.stdout.write("Tumanlar (kod | nom | viloyat):")
        for d in District.objects.select_related("region").filter(Q(name__icontains=text) | Q(region__name__icontains=text)).order_by("region__name", "name")[:40]:
            self.stdout.write(f"  {d.code} | {d.name} | {d.region.name}")
        self.stdout.write("Tashkilotlar (ID | nom | hudud | STIR | yetkazib beruvchi):")
        orgs = Organization.objects.filter(name__icontains=text).select_related("supplier_profile").order_by("name")[:40]
        for o in orgs:
            profile = getattr(o, "supplier_profile", None)
            self.stdout.write(f"  {o.id} | {o.name} | {o.region or '—'} | {o.stir or '—'} | {profile.supplier_type if profile else '—'}")

    # ------------------------------------------------------------------ tekshiruvlar
    def _district(self, code):
        found = list(District.objects.select_related("region").filter(code=code)[:2])
        if len(found) != 1:
            raise CommandError(f"Tuman kodi topilmadi yoki bir nechta: {code} (qidirish: --find)")
        return found[0]

    def _org(self, org_id, supplier_type):
        try:
            org = Organization.objects.filter(pk=org_id).first()
        except (ValueError, ValidationError):
            org = None
        if org is None:
            raise CommandError(f"Tashkilot topilmadi: {org_id} (qidirish: --find)")
        profile = getattr(org, "supplier_profile", None)
        if profile is not None and profile.supplier_type != supplier_type:
            raise CommandError(f"{org.name}: allaqachon «{profile.get_supplier_type_display()}» sifatida ro'yxatda")
        return org

    # ------------------------------------------------------------------ yozish
    def _reference(self):
        for year in YEARS:
            for (month, day), note in FIXED_HOLIDAYS.items():
                CalendarDay.objects.get_or_create(date=date(year, month, day),
                                                  defaults={"kind": CalendarDay.Kind.HOLIDAY, "note": note, "source_ref": SOURCE})
        for order, (code, cyr, lat, st, it, cat, unit, attrs) in enumerate(CATALOG, start=1):
            CatalogItem.objects.get_or_create(code=code, defaults={
                "name_cyr": cyr, "name_lat": lat, "supplier_type": st, "item_type": it, "category": cat,
                "unit": unit, "attributes": attrs, "order": order, "effective_from": VALID_FROM,
            })
        for code, desc, cat, params in NORMS:
            NormRule.objects.get_or_create(code=code, version=1, defaults={
                "description": desc, "applies_to_category": cat, "params": params,
                "effective_from": VALID_FROM, "approved_ref": CATALOG_REF,
            })
        for year, kind, start, end in SEASONS:
            Season.objects.get_or_create(year=year, kind=kind, defaults={"date_from": start, "date_to": end})
        for order, (code, cyr, lat, note) in enumerate(OBJECT_TYPES, start=1):
            ObjectType.objects.get_or_create(code=code, defaults={"name_cyr": cyr, "name_lat": lat, "requires_note": note, "order": order})

    def _mahalla(self, code, name, district):
        mahalla = Mahalla.objects.filter(source_code=code).first()
        if mahalla is None:
            return Mahalla.objects.create(source_code=code, name=name, region=district.region, district=district, valid_from=VALID_FROM)
        if mahalla.district_id != district.id:
            raise CommandError(f"{code} boshqa tumanda bor: {mahalla.district} — boshqa --mahalla-code bering")
        return mahalla

    def _profile(self, org, supplier_type):
        profile = getattr(org, "supplier_profile", None)
        if profile is None:
            SupplierProfile.objects.create(organization=org, supplier_type=supplier_type, stir=str(org.stir or "")[:9])
        elif not profile.is_active_supplier:
            profile.is_active_supplier = True
            profile.save()

    def _union_unit(self, district):
        unit = UnionUnit.objects.filter(district=district, level=UnionUnit.Level.DISTRICT, is_active=True).first()
        if unit is None:
            unit = UnionUnit.objects.create(name=f"{district.name} маҳаллалар уюшмаси", level=UnionUnit.Level.DISTRICT,
                                            region=district.region, district=district)
        return unit

    def _done(self, mahalla):
        self.stdout.write(self.style.SUCCESS(
            f"Kalendar {YEARS[0]}–{YEARS[-1]}, katalog {CatalogItem.objects.count()} pozitsiya, mavsumlar tayyor."))
        self.stdout.write("Eslatma: hayit kunlari va ko'chirilgan ish kunlarini «Ma'muriyat → Kalendar» orqali qo'shing.")
        if mahalla is not None:
            self.stdout.write(self.style.SUCCESS(f"Mahalla: {mahalla.source_code} — {mahalla.name} ({mahalla.district})"))
            self.stdout.write(f"Keyingi qadam: python manage.py yashil_test_accounts --mahalla {mahalla.source_code}")
