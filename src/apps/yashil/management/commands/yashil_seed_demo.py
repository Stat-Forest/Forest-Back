"""
Sintetik namuna ma'lumotlari — FAQAT lokal/test muhit (DEBUG yoki --force).

Yaratadi: 2 viloyat / 4 tuman / 6 mahalla, 2 o'rmon xo'jaligi, DM + bo'linma, 2 uyushma
bo'linmasi, marshrut va biriktirishlar, katalog (PF-206 6-ilova namunasi, narxsiz),
meyorlar, 2027 mavsumlari, obyekt turlari, 2027 bayramlari, test foydalanuvchilar
(parol Test12345!): mahalla@ / uyushma@ / dm@ / kuzatuvchi@ / xojalik@test.uz.
Idempotent: qayta ishga tushirilsa takrorlamaydi.
"""
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.billing.models import District, Region
from apps.general.models import Organization
from apps.yashil.models import (
    CalendarDay,
    CatalogItem,
    Mahalla,
    MahallaUnionRoute,
    NormRule,
    ObjectType,
    Season,
    SupplierAssignment,
    SupplierProfile,
    UnionUnit,
    YashilMembership,
)

PASSWORD = "Test12345!"
VALID_FROM = date(2026, 1, 1)

REGIONS = {"1703": "Андижон вилояти", "1727": "Тошкент вилояти"}
# Kodlar — billing ma'lumotnomasidagi (MHOBT) haqiqiy tuman kodlari.
DISTRICTS = {
    "1703203": ("1703", "Андижон тумани"),
    "1703224": ("1703", "Асака тумани"),
    "1727224": ("1727", "Бўстонлиқ тумани"),
    "1727237": ("1727", "Зангиота тумани"),
}
MAHALLAS = [
    ("YM-DEMO-001", "1703203", "Боғистон маҳалласи"),
    ("YM-DEMO-002", "1703203", "Навбаҳор маҳалласи"),
    ("YM-DEMO-003", "1703224", "Гулистон маҳалласи"),
    ("YM-DEMO-004", "1727224", "Чимён маҳалласи"),
    ("YM-DEMO-005", "1727224", "Хумсон маҳалласи"),
    ("YM-DEMO-006", "1727237", "Эшонгузар маҳалласи"),
]
CATALOG = [
    # code, cyr, lat, supplier_type, item_type, category, unit, attributes
    ("ASH", "Шумтол кўчати", "Shumtol ko'chati", "forest", "goods", "seedling", "tup", {"age": "2–3 йил", "height": "1–1,5 м"}),
    ("ELM", "Қайрағоч кўчати", "Qayrag'och ko'chati", "forest", "goods", "seedling", "tup", {"age": "2–3 йил"}),
    ("WIL", "Тол кўчати", "Tol ko'chati", "forest", "goods", "seedling", "tup", {"age": "2–3 йил", "height": "1–1,5 м"}),
    ("MUL", "Мульча", "Mulcha", "forest", "goods", "mulch", "kg", {}),
    ("BIO", "Биогумус", "Biogumus", "dm", "goods", "fertilizer", "kg", {}),
    ("TANK", "Сув идиши 3–5 тонна", "Suv idishi 3–5 tonna", "dm", "goods", "irrigation", "dona", {"capacity": "3–5 т"}),
    ("IBC", "IBC контейнер", "IBC konteyner", "dm", "goods", "irrigation", "dona", {"capacity": "1 м³"}),
    ("PUMP", "Мотопомпа", "Motopompa", "dm", "goods", "irrigation", "dona", {}),
    ("HOSE", "Шланг 25–50 мм", "Shlang 25–50 mm", "dm", "goods", "irrigation", "metr", {"diameter": "25–50 мм"}),
    ("BUCK", "Челак", "Chelak", "dm", "goods", "equipment", "dona", {}),
    ("CAN", "Лейка", "Leyka", "dm", "goods", "equipment", "dona", {}),
    ("RAKE", "Хаскаш", "Xaskash", "dm", "goods", "equipment", "dona", {}),
    ("SPADE", "Белкурак", "Belkurak", "dm", "goods", "equipment", "dona", {}),
    ("HOE", "Кетмон", "Ketmon", "dm", "goods", "equipment", "dona", {}),
    ("CART", "Арава", "Arava", "dm", "goods", "equipment", "dona", {}),
    ("PROT", "Касаллик ва зараркунандаларга қарши кураш хизмати", "Kasallik va zararkunandalarga qarshi kurash xizmati", "dm", "service", "protection_service", "daraxt", {}),
]
NORMS = [
    ("fertilizer_per_tup_kg", "Биогумус: 1 тупга 5 кггача", "fertilizer", {"max_per_tup": 5}),
    ("mulch_per_tup_kg", "Мульча: 1 тупга 4 кггача", "mulch", {"max_per_tup": 4}),
]
OBJECT_TYPES = [
    ("micro_forest", "Маҳалла микроўрмони", "Mahalla mikro-o'rmoni", False),
    ("pocket_park", "Жамоатчилик кичик боғи", "Jamoatchilik kichik bog'i", False),
    ("mahalla_park", "Маҳалла боғи", "Mahalla bog'i", False),
    ("street", "Кўча / йўл бўйи", "Ko'cha / yo'l bo'yi", False),
    ("courtyard", "Кўп квартирали уйлар оралиғи", "Ko'p kvartirali uylar oralig'i", False),
    ("school", "Мактаб / боғча ҳовлиси", "Maktab / bog'cha hovlisi", False),
    ("waterside", "Сув объекти бўйи", "Suv obyekti bo'yi", False),
    ("other", "Бошқа", "Boshqa", True),
]
HOLIDAYS_2027 = {
    date(2027, 1, 1): "Янги йил", date(2027, 1, 14): "Ватан ҳимоячилари куни", date(2027, 3, 8): "Хотин-қизлар куни",
    date(2027, 3, 21): "Наврўз", date(2027, 5, 9): "Хотира ва қадрлаш куни", date(2027, 9, 1): "Мустақиллик куни",
    date(2027, 10, 1): "Ўқитувчилар куни", date(2027, 12, 8): "Конституция куни",
}


class Command(BaseCommand):
    help = "Yashil mahalla: sintetik namuna ma'lumotlari (faqat DEBUG / --force)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="DEBUG=False bo'lsa ham ishga tushirish (prod'da ISHLATMANG)")
        parser.add_argument("--with-orders", action="store_true", help="Turli holatdagi namuna buyurtmalar ham (imzosiz, faqat namoyish)")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Bu buyruq faqat DEBUG muhitda (yoki --force bilan) ishlaydi.")
        regions = {code: Region.objects.get_or_create(code=code, defaults={"name": name})[0] for code, name in REGIONS.items()}
        districts = {
            code: District.objects.get_or_create(region=regions[rc], code=code, defaults={"name": name})[0]
            for code, (rc, name) in DISTRICTS.items()
        }
        mahallas = {}
        for code, dcode, name in MAHALLAS:
            d = districts[dcode]
            mahallas[code], _ = Mahalla.objects.get_or_create(
                source_code=code, defaults={"name": name, "region": d.region, "district": d, "valid_from": VALID_FROM},
            )

        forest1 = self._supplier("Намуна ўрмон хўжалиги", "andijon", "forest")
        forest2 = self._supplier("Бўстонлиқ ўрмон хўжалиги", "tashkent", "forest")
        dm_main = self._supplier("Яшил боғларни ташкил этиш ДМ", "tashkent", "dm")
        dm_branch = self._supplier("Яшил боғлар ДМ Андижон бўлинмаси", "andijon", "dm", parent=dm_main.supplier_profile)
        dm_branch.supplier_profile.service_regions.add(regions["1703"])

        for code in ("YM-DEMO-001", "YM-DEMO-002", "YM-DEMO-003"):
            self._assign(mahallas[code], forest1)
        for code in ("YM-DEMO-004", "YM-DEMO-005", "YM-DEMO-006"):
            self._assign(mahallas[code], forest2)

        unit_and, _ = UnionUnit.objects.get_or_create(name="Андижон туман маҳаллалар уюшмаси", defaults={
            "level": UnionUnit.Level.DISTRICT, "region": regions["1703"], "district": districts["1703203"]})
        unit_bos, _ = UnionUnit.objects.get_or_create(name="Бўстонлиқ туман маҳаллалар уюшмаси", defaults={
            "level": UnionUnit.Level.DISTRICT, "region": regions["1727"], "district": districts["1727224"]})
        for code in ("YM-DEMO-001", "YM-DEMO-002", "YM-DEMO-003"):
            self._route(mahallas[code], unit_and)
        for code in ("YM-DEMO-004", "YM-DEMO-005", "YM-DEMO-006"):
            self._route(mahallas[code], unit_bos)

        for order, (code, cyr, lat, st, it, cat, unit, attrs) in enumerate(CATALOG, start=1):
            CatalogItem.objects.get_or_create(code=code, defaults={
                "name_cyr": cyr, "name_lat": lat, "supplier_type": st, "item_type": it, "category": cat,
                "unit": unit, "attributes": attrs, "order": order, "effective_from": VALID_FROM,
            })
        for code, desc, cat, params in NORMS:
            NormRule.objects.get_or_create(code=code, version=1, defaults={
                "description": desc, "applies_to_category": cat, "params": params,
                "effective_from": VALID_FROM, "approved_ref": "ПФ-206, 6-илова (намуна)",
            })
        Season.objects.get_or_create(year=2027, kind=Season.Kind.SPRING, defaults={"date_from": date(2027, 3, 1), "date_to": date(2027, 5, 31)})
        Season.objects.get_or_create(year=2027, kind=Season.Kind.AUTUMN, defaults={"date_from": date(2027, 10, 1), "date_to": date(2027, 12, 15)})
        for order, (code, cyr, lat, note) in enumerate(OBJECT_TYPES, start=1):
            ObjectType.objects.get_or_create(code=code, defaults={"name_cyr": cyr, "name_lat": lat, "requires_note": note, "order": order})
        for day, note in HOLIDAYS_2027.items():
            CalendarDay.objects.get_or_create(date=day, defaults={"kind": CalendarDay.Kind.HOLIDAY, "note": note, "source_ref": "Namuna"})

        T = YashilMembership.MemberType
        self._member("mahalla@test.uz", "ym_mahalla", "Маҳалла", "Раиси", T.MAHALLA, mahalla=mahallas["YM-DEMO-001"],
                     position_title="Маҳалла раиси", phone="+998901112233")
        self._member("uyushma@test.uz", "ym_union", "Уюшма", "Масъули", T.UNION, union_unit=unit_and, can_sign=False)
        self._member("dm@test.uz", "ym_dm", "ДМ", "Масъули", T.SUPPLIER, organization=dm_main)
        self._member("kuzatuvchi@test.uz", "ym_observer", "Агентлик", "Кузатувчиси", T.OBSERVER, can_prepare=False, can_sign=False)
        self._member("xojalik@test.uz", "tashkilot_rahbari", "Хўжалик", "Раҳбари", T.SUPPLIER, organization=forest1, user_org=forest1)
        if options["with_orders"]:
            self._demo_orders(mahallas, forest1, dm_main)
        self.stdout.write("Yashil mahalla namuna ma'lumotlari tayyor (parol: Test12345!).")

    def _demo_orders(self, mahallas, forest1, dm_main):
        """Namuna buyurtmalar: qoralama, uyushmada, yetkazib beruvchida, qaytarilgan, ijroda (imzosiz)."""
        from decimal import Decimal

        from apps.yashil.models import Order, OrderLine, ReturnReason, YashilMembership
        from apps.yashil.services import transitions as tr

        if Order.objects.filter(title__startswith="Намуна:").exists():
            return
        m = YashilMembership.objects.get(user__email="mahalla@test.uz")
        u = YashilMembership.objects.get(user__email="uyushma@test.uz")
        f = YashilMembership.objects.get(user__email="xojalik@test.uz")
        items = {c.code: c for c in CatalogItem.objects.all()}
        mahalla = mahallas["YM-DEMO-001"]

        def make(title, route, org, lines, **extra):
            o = Order.objects.create(mahalla=mahalla, route=route, supplier_org=org, created_by_membership=m,
                                     title=title, address="Боғистон, марказий кўча", lat=Decimal("40.783200"),
                                     lon=Decimal("72.350100"), area_ha=Decimal("0.5"), water_source="Ариқ", **extra)
            for i, (code, qty) in enumerate(lines):
                OrderLine.objects.create(order=o, catalog_item=items[code], qty=Decimal(qty), position=i)
            return o

        make("Намуна: қоралама — кўчат", "forest", forest1, [("ASH", "200"), ("ELM", "100")])
        o2 = make("Намуна: уюшмада — кўчат ва мульча", "forest", forest1, [("ASH", "300"), ("MUL", "1000")], base_seedlings=300)
        tr.submit(o2, m, document_version=None)
        o3 = make("Намуна: етказиб берувчида — биогумус", "dm", dm_main, [("BIO", "500")], base_seedlings=120)
        tr.submit(o3, m, document_version=None); tr.start_review(o3, u); tr.forward(o3, u)
        o4 = make("Намуна: қайтарилган — тол кўчати", "forest", forest1, [("WIL", "150")])
        tr.submit(o4, m, document_version=None); tr.start_review(o4, u)
        tr.return_order(o4, u, reason_code=ReturnReason.ADDRESS, comment="Манзилни аниқлаштиринг: кўча номи йўқ", fields=["address"])
        o5 = make("Намуна: ижрода — қайрағоч", "forest", forest1, [("ELM", "250")])
        tr.submit(o5, m, document_version=None); tr.start_review(o5, u); tr.forward(o5, u)
        tr.start_review(o5, f); tr.accept(o5, f, executor_name="Иброҳимов А.")
        self.stdout.write("Namuna buyurtmalar: 5 ta (qoralama, uyushmada, yetkazib beruvchida, qaytarilgan, ijroda).")

    def _supplier(self, name, region, supplier_type, parent=None):
        org, _ = Organization.objects.get_or_create(name=name, defaults={"region": region})
        SupplierProfile.objects.get_or_create(organization=org, defaults={"supplier_type": supplier_type, "parent": parent})
        return org

    def _assign(self, mahalla, org):
        if not SupplierAssignment.objects.filter(mahalla=mahalla, valid_to__isnull=True).exists():
            SupplierAssignment.objects.create(mahalla=mahalla, organization=org, valid_from=VALID_FROM, source_doc="Namuna")

    def _route(self, mahalla, unit):
        if not MahallaUnionRoute.objects.filter(mahalla=mahalla, valid_to__isnull=True).exists():
            MahallaUnionRoute.objects.create(mahalla=mahalla, union_unit=unit, valid_from=VALID_FROM)

    def _member(self, email, role, last_name, first_name, member_type, user_org=None, **fields):
        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(
                email=email, password=PASSWORD, first_name=first_name, last_name=last_name,
                father_name="Намуна", role=role, organization=user_org,
            )
        if not YashilMembership.objects.filter(user=user, member_type=member_type).exists():
            fields.setdefault("can_prepare", True)
            fields.setdefault("can_sign", True)
            YashilMembership.objects.create(user=user, member_type=member_type, valid_from=VALID_FROM, **fields)
        return user
