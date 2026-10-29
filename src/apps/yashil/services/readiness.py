"""
Pilot va ishchi muhitga o'tishdan oldingi tekshiruv (TZ §19.2): tashkilotlar, mahallalar,
xo'jalik biriktirishlari, marshrutlar, imzolovchilar, kalendar, katalog, boshlang'ich qoldiq
va DM quvvati. `blocker` — buyurtma oqimi ishlamaydi; `warning` — pilotdan oldin ko'rib chiqing.
"""
from datetime import date

from django.db.models import Exists, OuterRef, Q

from apps.yashil.models import (
    CalendarDay, CatalogItem, Mahalla, MahallaUnionRoute, ServiceCapacity, StockMovement, SupplierAssignment,
    SupplierProfile, YashilMembership,
)
from apps.yashil.services.scope import _active_period_q

T = YashilMembership.MemberType
BLOCKER, WARNING = "blocker", "warning"


def _active_members(on, **filters):
    return YashilMembership.objects.filter(is_active=True, user__is_active=True, **filters).filter(_active_period_q(on))


def _section(key, title, level, names, limit):
    names = list(names)
    return {"key": key, "title": title, "level": level, "count": len(names), "sample": names[:limit]}


def collect(on: date | None = None, limit: int = 20) -> dict:
    from apps.yashil.services.rules import snapshot

    on = on or date.today()
    period = on.strftime("%Y-%m")
    mahallas = Mahalla.objects.filter(is_active=True).filter(_active_period_q(on))
    forest_q = SupplierAssignment.objects.filter(mahalla=OuterRef("pk")).filter(_active_period_q(on))
    route_q = MahallaUnionRoute.objects.filter(mahalla=OuterRef("pk")).filter(_active_period_q(on))
    signer_q = _active_members(on, member_type=T.MAHALLA, can_sign=True).filter(mahalla=OuterRef("pk"))
    mahallas = mahallas.annotate(has_forest=Exists(forest_q), has_route=Exists(route_q), has_signer=Exists(signer_q)).order_by("name")

    suppliers = SupplierProfile.objects.filter(is_active_supplier=True).select_related("organization").order_by("organization__name")
    supplier_signer = _active_members(on, member_type=T.SUPPLIER, can_sign=True).filter(organization=OuterRef("organization"))
    opening = StockMovement.objects.filter(warehouse__organization=OuterRef("organization"), kind=StockMovement.Kind.OPENING)
    capacity = ServiceCapacity.objects.filter(organization=OuterRef("organization"), period=period)
    suppliers = suppliers.annotate(has_signer=Exists(supplier_signer), has_opening=Exists(opening), has_capacity=Exists(capacity))
    dm_services = CatalogItem.objects.filter(is_active=True, supplier_type="dm", item_type=CatalogItem.ItemType.SERVICE).exists()

    year_days = CalendarDay.objects.filter(date__year=on.year).count()
    catalog_missing = [label for value, label in SupplierProfile.SupplierType.choices
                       if not CatalogItem.objects.filter(is_active=True, supplier_type=value).exists()]
    observers = _active_members(on, member_type=T.OBSERVER).count()

    sections = [
        _section("mahalla_without_forest", "Ўрмон хўжалиги бириктирилмаган маҳаллалар", BLOCKER,
                 (m.name for m in mahallas if not m.has_forest), limit),
        _section("mahalla_without_route", "Уюшма бўлинмасига йўналтирилмаган маҳаллалар", BLOCKER,
                 (m.name for m in mahallas if not m.has_route), limit),
        _section("mahalla_without_signer", "Имзоловчиси йўқ маҳаллалар", WARNING,
                 (m.name for m in mahallas if not m.has_signer), limit),
        _section("supplier_without_signer", "Имзоловчиси йўқ етказиб берувчилар", WARNING,
                 (s.organization.name for s in suppliers if not s.has_signer), limit),
        _section("forest_without_opening", "Бошланғич қолдиқ киритилмаган ўрмон хўжаликлари", WARNING,
                 (s.organization.name for s in suppliers if s.supplier_type == SupplierProfile.SupplierType.FOREST and not s.has_opening), limit),
        _section("dm_without_capacity", f"{period} учун хизмат қуввати киритилмаган ДМлар", WARNING,
                 (s.organization.name for s in suppliers if dm_services and s.supplier_type == SupplierProfile.SupplierType.DM and not s.has_capacity), limit),
        _section("calendar_year", f"{on.year} йил иш кунлари календари киритилмаган", BLOCKER,
                 [] if year_days else [str(on.year)], limit),
        _section("catalog", "Фаол каталог позициялари йўқ йўналишлар", BLOCKER, catalog_missing, limit),
        _section("observers", "Агентлик кузатувчиси бириктирилмаган", WARNING, [] if observers else ["—"], limit),
    ]
    return {
        "date": on.isoformat(),
        "ready": not any(s["count"] for s in sections),
        "blockers": sum(1 for s in sections if s["level"] == BLOCKER and s["count"]),
        "totals": {"mahallas": mahallas.count(), "suppliers": suppliers.count(),
                   "memberships": _active_members(on).count()},
        "rules": {r["key"]: r["value"] for r in snapshot(on)},
        "sections": sections,
    }
