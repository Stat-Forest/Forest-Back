"""
Hisobot reestri (TZ §14.1–14.2; javoblar З2, З3).

Qator = buyurtma pozitsiyasi (`OrderLine`); buyurtmalar soni unikal `order_id`
bo'yicha, miqdorlar `catalog_item + unit` kesimida. Kabinet ko'lami —
`scope.orders_for_cabinet`. Qoralamalar reestrga kirmaydi.

    parse_filters(params)                   -> dict | RegistryFilterError
    registry_queryset(cabinet, is_admin, f) -> QuerySet[OrderLine] (annotatsiyali)
    row_dicts(lines, start_no)              -> list[dict]  (UI va eksport bitta manba)
    summary(qs)                             -> dict
"""
from datetime import date
from decimal import Decimal

from django.db.models import Count, DecimalField, Max, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce, TruncDate

from apps.yashil.models import STATE_LABELS_CYR, Act, ActLine, ActVersion, CatalogItem, Order, OrderLine, OrderState, SupplierProfile
from apps.yashil.services.scope import orders_for_cabinet
from apps.yashil.services.units import UNIT_LABELS
from apps.yashil.services.workdays import local_date

ZERO = Decimal("0")
QTY = DecimalField(max_digits=18, decimal_places=4)

PERIOD_BASES = (
    ("submitted", "Буюртма юборилган сана (биринчи юбориш)"),
    ("accepted", "Ижрога қабул қилинган сана"),
    ("delivered", "Ҳақиқий етказиш санаси (тасдиқланган акт)"),
)
ROUTE_CYR = {"forest": "Ўрмон хўжалиги", "dm": "Яшил боғларни ташкил этиш ДМ"}
STAGE_CYR = {"review": "Кўриб чиқиш", "delivery": "Етказиш"}
RESPONSIBLE_CYR = {
    OrderState.UNION_NEW: "Уюшма", OrderState.UNION_REVIEW: "Уюшма",
    OrderState.SUPPLIER_NEW: "Етказиб берувчи", OrderState.SUPPLIER_REVIEW: "Етказиб берувчи",
    OrderState.EXECUTION: "Етказиб берувчи", OrderState.PARTIAL: "Етказиб берувчи",
    OrderState.RETURNED: "Маҳалла",
}
ORDERINGS = {
    "first_submitted_on": "first_submitted_on",
    "number": "order__number",
    "mahalla": "order__mahalla__name",
    "supplier": "order__supplier_org__name",
    "state": "order__state",
    "late_workdays": "order__late_workdays",
    "item": "catalog_item__name_cyr",
    "position": "position",
    "qty": "qty",
}
DEFAULT_ORDERING = ("-first_submitted_on", "order__number", "position")


class RegistryFilterError(ValueError):
    def __init__(self, message, field):
        super().__init__(message)
        self.field = field


def _date(value, field) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise RegistryFilterError("Сана YYYY-MM-DD кўринишида бўлиши керак", field)


def _csv(value) -> list[str]:
    return [v for v in str(value or "").split(",") if v]


def parse_filters(params) -> dict:
    """Query parametrlarini tekshirib lug'atga aylantiradi (eksport `filters` JSON ham shu)."""
    g = params.get
    basis = g("period_basis") or "submitted"
    if basis not in dict(PERIOD_BASES):
        raise RegistryFilterError("Давр асоси: submitted / accepted / delivered", "period_basis")
    route = g("route") or ""
    if route and route not in ROUTE_CYR:
        raise RegistryFilterError("Йўналиш: forest / dm", "route")
    states = _csv(g("state"))
    bad = [s for s in states if s not in OrderState.values]
    if bad:
        raise RegistryFilterError(f"Номаълум ҳолат: {bad[0]}", "state")
    ordering = g("ordering") or ""
    if ordering and ordering.lstrip("-") not in ORDERINGS:
        raise RegistryFilterError("Номаълум саралаш майдони", "ordering")
    return {
        "period_basis": basis,
        "date_from": _date(g("date_from"), "date_from"),
        "date_to": _date(g("date_to"), "date_to"),
        "region": g("region") or None,
        "district": g("district") or None,
        "mahalla": g("mahalla") or None,
        "supplier_org": g("supplier_org") or None,
        "route": route or None,
        "catalog_item": g("catalog_item") or None,
        "category": g("category") or None,
        "state": states,
        "overdue": str(g("overdue") or "") in ("1", "true"),
        "q": (g("q") or "").strip(),
        "ordering": ordering,
    }


def filters_label(f: dict) -> str:
    """Eksport sarlavhasi uchun filtrlar matni (kirill)."""
    parts = [dict(PERIOD_BASES)[f["period_basis"]]]
    if f.get("date_from") or f.get("date_to"):
        a = f["date_from"].strftime("%d.%m.%Y") if f.get("date_from") else "…"
        b = f["date_to"].strftime("%d.%m.%Y") if f.get("date_to") else "…"
        parts.append(f"давр {a} — {b}")
    if f.get("route"):
        parts.append(ROUTE_CYR[f["route"]])
    if f.get("state"):
        parts.append("ҳолат: " + ", ".join(STATE_LABELS_CYR.get(s, s) for s in f["state"]))
    if f.get("overdue"):
        parts.append("муддати бузилган")
    if f.get("q"):
        parts.append(f"қидирув «{f['q']}»")
    return "; ".join(parts)


def _accepted_qty():
    approved = ActLine.objects.filter(
        order_line=OuterRef("pk"), act_version__act__status=Act.Status.APPROVED, act_version__superseded_at__isnull=True,
    ).order_by().values("order_line").annotate(s=Sum("qty")).values("s")[:1]
    return Coalesce(Subquery(approved, output_field=QTY), Value(ZERO, output_field=QTY))


def _last_delivery():
    latest = ActVersion.objects.filter(
        act__order=OuterRef("order_id"), act__status=Act.Status.APPROVED, superseded_at__isnull=True,
    ).order_by().values("act__order").annotate(m=Max("delivery_date")).values("m")[:1]
    return Subquery(latest)


def base_queryset(cabinet, is_admin: bool):
    orders = orders_for_cabinet(cabinet, is_admin).exclude(state=OrderState.DRAFT)
    return (
        OrderLine.objects.filter(order__in=orders.values("pk"))
        .select_related("order__mahalla__district__region", "order__supplier_org__supplier_profile", "catalog_item")
        .annotate(accepted_qty=_accepted_qty(), last_delivery_date=_last_delivery(),
                  first_submitted_on=TruncDate("order__first_submitted_at"))
    )


def apply_filters(qs, f: dict):
    basis_field = {"submitted": "first_submitted_on", "accepted": "order__accepted_on", "delivered": "last_delivery_date"}[f["period_basis"]]
    if f.get("date_from"):
        qs = qs.filter(**{f"{basis_field}__gte": f["date_from"]})
    if f.get("date_to"):
        qs = qs.filter(**{f"{basis_field}__lte": f["date_to"]})
    if f.get("region"):
        qs = qs.filter(order__mahalla__region_id=f["region"])
    if f.get("district"):
        qs = qs.filter(order__mahalla__district_id=f["district"])
    if f.get("mahalla"):
        qs = qs.filter(order__mahalla_id=f["mahalla"])
    if f.get("supplier_org"):
        qs = qs.filter(order__supplier_org_id=f["supplier_org"])
    if f.get("route"):
        qs = qs.filter(order__route=f["route"])
    if f.get("catalog_item"):
        qs = qs.filter(catalog_item_id=f["catalog_item"])
    if f.get("category"):
        qs = qs.filter(catalog_item__category=f["category"])
    if f.get("state"):
        qs = qs.filter(order__state__in=f["state"])
    if f.get("overdue"):
        qs = qs.filter(order__late_workdays__gt=0)
    if f.get("q"):
        q = f["q"]
        qs = qs.filter(Q(order__number__icontains=q) | Q(order__title__icontains=q) | Q(order__mahalla__name__icontains=q)
                       | Q(order__address__icontains=q) | Q(order__supplier_org__name__icontains=q))
    return qs


def apply_order_filters(qs, f: dict):
    """Xuddi `apply_filters`, lekin `Order` queryset'i uchun (statistika, xarita)."""
    qs = qs.annotate(first_submitted_on=TruncDate("first_submitted_at"))
    basis = f["period_basis"]
    if basis == "delivered" and (f.get("date_from") or f.get("date_to")):
        latest = ActVersion.objects.filter(
            act__order=OuterRef("pk"), act__status=Act.Status.APPROVED, superseded_at__isnull=True,
        ).order_by().values("act__order").annotate(m=Max("delivery_date")).values("m")[:1]
        qs = qs.annotate(last_delivery_date=Subquery(latest))
    basis_field = {"submitted": "first_submitted_on", "accepted": "accepted_on", "delivered": "last_delivery_date"}[basis]
    if f.get("date_from"):
        qs = qs.filter(**{f"{basis_field}__gte": f["date_from"]})
    if f.get("date_to"):
        qs = qs.filter(**{f"{basis_field}__lte": f["date_to"]})
    if f.get("region"):
        qs = qs.filter(mahalla__region_id=f["region"])
    if f.get("district"):
        qs = qs.filter(mahalla__district_id=f["district"])
    if f.get("mahalla"):
        qs = qs.filter(mahalla_id=f["mahalla"])
    if f.get("supplier_org"):
        qs = qs.filter(supplier_org_id=f["supplier_org"])
    if f.get("route"):
        qs = qs.filter(route=f["route"])
    if f.get("catalog_item"):
        qs = qs.filter(lines__catalog_item_id=f["catalog_item"]).distinct()
    if f.get("category"):
        qs = qs.filter(lines__catalog_item__category=f["category"]).distinct()
    if f.get("state"):
        qs = qs.filter(state__in=f["state"])
    if f.get("overdue"):
        qs = qs.filter(late_workdays__gt=0)
    if f.get("q"):
        q = f["q"]
        qs = qs.filter(Q(number__icontains=q) | Q(title__icontains=q) | Q(mahalla__name__icontains=q)
                       | Q(address__icontains=q) | Q(supplier_org__name__icontains=q))
    return qs


def ordered(qs, ordering: str):
    if not ordering:
        return qs.order_by(*DEFAULT_ORDERING)
    desc = ordering.startswith("-")
    field = ORDERINGS[ordering.lstrip("-")]
    return qs.order_by(("-" if desc else "") + field, "order__number", "position")


def registry_queryset(cabinet, is_admin: bool, f: dict):
    return ordered(apply_filters(base_queryset(cabinet, is_admin), f), f.get("ordering", ""))


def _dec(value) -> str:
    return format(Decimal(value or 0).normalize(), "f")


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def row_dicts(lines, start_no: int = 1) -> list[dict]:
    """Sahifa (yoki eksport bo'lagi) qatorlari; akt raqamlari bitta so'rovda."""
    lines = list(lines)
    order_ids = {l.order_id for l in lines}
    act_numbers: dict = {}
    for oid, number in Act.objects.filter(order_id__in=order_ids, status=Act.Status.APPROVED).order_by("index").values_list("order_id", "number"):
        act_numbers.setdefault(oid, []).append(number)
    rows = []
    for n, l in enumerate(lines, start=start_no):
        o, item = l.order, l.catalog_item
        accepted = l.accepted_qty or ZERO
        rows.append({
            "row_no": n,
            "order_id": str(o.id),
            "line_id": str(l.id),
            "number": o.number,
            "title": o.title,
            "route": o.route,
            "route_cyr": ROUTE_CYR.get(o.route, o.route),
            "state": o.state,
            "state_cyr": STATE_LABELS_CYR.get(o.state, o.state),
            "responsible_cyr": RESPONSIBLE_CYR.get(o.state, ""),
            "mahalla": o.mahalla.name,
            "mahalla_id": str(o.mahalla_id),
            "district": o.mahalla.district.name,
            "region": o.mahalla.region.name,
            "supplier": o.supplier_org.name,
            "supplier_id": str(o.supplier_org_id),
            "item": item.name_cyr,
            "item_code": item.code,
            "category": item.category,
            "unit": item.unit,
            "unit_cyr": UNIT_LABELS.get(item.unit, (item.unit,))[0],
            "qty": _dec(l.qty),
            "accepted_qty": _dec(accepted),
            "remaining_qty": _dec(l.qty - accepted),
            "first_submitted_on": _iso(l.first_submitted_on),
            "last_submitted_at": o.last_submitted_at.isoformat() if o.last_submitted_at else None,
            "last_submitted_on": _iso(local_date(o.last_submitted_at)) if o.last_submitted_at else None,
            "review_due": _iso(o.review_due),
            "accepted_on": _iso(o.accepted_on),
            "delivery_due": _iso(o.delivery_due),
            "late_workdays": o.late_workdays,
            "overdue_stage": o.overdue_stage,
            "overdue_stage_cyr": STAGE_CYR.get(o.overdue_stage, ""),
            "executor_name": o.executor_name,
            "act_numbers": ", ".join(act_numbers.get(o.id, [])),
            "last_delivery_date": _iso(l.last_delivery_date),
            "address": o.address,
            "lat": _dec(o.lat) if o.lat is not None else None,
            "lon": _dec(o.lon) if o.lon is not None else None,
            "area_ha": _dec(o.area_ha) if o.area_ha is not None else None,
        })
    return rows


def summary(qs) -> dict:
    """Unikal buyurtmalar soni, qatorlar, pozitsiya/birlik kesimida jami, holatlar bo'yicha unikal soni.

    Filtrlangan qatorlar ID'si orqali oddiy yig'ma so'rovlar: annotatsiyali querysetda har qator uchun
    qabul qilingan miqdor qism-so'rovi hisoblanardi (100 ming buyurtmada soniyalar).
    """
    lines = OrderLine.objects.filter(pk__in=qs.order_by().values("pk"))
    accepted = {
        r["order_line__catalog_item_id"]: r["s"] or ZERO
        for r in ActLine.objects.filter(order_line__in=lines.values("pk"), act_version__act__status=Act.Status.APPROVED,
                                        act_version__superseded_at__isnull=True)
        .order_by().values("order_line__catalog_item_id").annotate(s=Sum("qty"))
    }
    item_rows = (
        lines.order_by().values("catalog_item_id", "catalog_item__code", "catalog_item__name_cyr", "catalog_item__unit", "catalog_item__order")
        .annotate(ordered=Sum("qty"), orders=Count("order", distinct=True), lines=Count("id"))
        .order_by("catalog_item__order", "catalog_item__code")
    )
    by_item = []
    for r in item_rows:
        o, a = r["ordered"] or ZERO, accepted.get(r["catalog_item_id"], ZERO)
        by_item.append({
            "item_code": r["catalog_item__code"], "item": r["catalog_item__name_cyr"], "unit": r["catalog_item__unit"],
            "unit_cyr": UNIT_LABELS.get(r["catalog_item__unit"], (r["catalog_item__unit"],))[0],
            "ordered": _dec(o), "accepted": _dec(a), "remaining": _dec(o - a), "orders": r["orders"], "lines": r["lines"],
        })
    orders = Order.objects.filter(pk__in=lines.values("order_id"))
    by_state = {r["state"]: r["n"] for r in orders.order_by().values("state").annotate(n=Count("id"))}
    overdue = orders.filter(late_workdays__gt=0).count()
    return {"orders": sum(by_state.values()), "lines": sum(r["lines"] for r in by_item), "by_item": by_item,
            "by_state": by_state, "overdue_orders": overdue}


def filter_dictionaries(cabinet, is_admin: bool) -> dict:
    """Filtr lug'atlari kabinet ko'lamida: yetkazib beruvchilar, pozitsiyalar, holatlar, davr asoslari."""
    orders = orders_for_cabinet(cabinet, is_admin).exclude(state=OrderState.DRAFT)
    supplier_ids = set(orders.values_list("supplier_org_id", flat=True).distinct())
    if cabinet is not None and cabinet.member_type == cabinet.MemberType.MAHALLA:
        # Mahalla hali buyurtma bermagan yetkazib beruvchilarni ham ko'rsin (biriktirilgan + hududdagi DM)
        from apps.yashil.services.scope import dm_suppliers_for, primary_forest_assignment

        a = primary_forest_assignment(cabinet.mahalla)
        if a is not None:
            supplier_ids.add(a.organization_id)
        supplier_ids.update(p.organization_id for p in dm_suppliers_for(cabinet.mahalla))
    profiles = SupplierProfile.objects.filter(organization_id__in=supplier_ids).select_related("organization").order_by("organization__name")
    suppliers = [{"id": str(p.organization_id), "name": p.organization.name, "supplier_type": p.supplier_type} for p in profiles]
    items = [
        {"id": str(i.id), "code": i.code, "name_cyr": i.name_cyr, "name_lat": i.name_lat, "supplier_type": i.supplier_type,
         "category": i.category, "unit": i.unit}
        for i in CatalogItem.objects.filter(is_active=True).order_by("supplier_type", "order", "code")
    ]
    states = [{"value": s, "label": STATE_LABELS_CYR[s]} for s in OrderState if s != OrderState.DRAFT]
    return {
        "suppliers": suppliers,
        "items": items,
        "states": states,
        "period_bases": [{"value": v, "label": l} for v, l in PERIOD_BASES],
        "routes": [{"value": v, "label": l} for v, l in ROUTE_CYR.items()],
    }
