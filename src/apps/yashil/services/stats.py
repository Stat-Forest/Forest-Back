"""
Statistika (TZ §15.1–15.3; javob З3).

    parse(params)                        -> filtrlar (registry.parse_filters)
    cards(cabinet, is_admin, f)          -> 6 karta + jami (unikal buyurtmalar)
    seedlings(cabinet, is_admin, f)      -> ko'chatlar farqi (tur kesimida)
    organizations(cabinet, is_admin, f)  -> orqada qolayotgan tashkilotlar jadvali

Natijalar 5 daqiqa keshlanadi; kalit = versiya + kabinet + filtrlar. Holat
o'tishida (`transitions._event`) va ertalabki qayta hisobda versiya oshadi.
"""
import hashlib
import json
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, Max, Q, Sum

from apps.yashil.models import Act, ActLine, CatalogItem, OrderState, UnionUnit
from apps.yashil.services import registry
from apps.yashil.services.scope import orders_for_cabinet
from apps.yashil.services.units import UNIT_LABELS

VERSION_KEY = "yashil:stats:ver"
TTL = 300
ZERO = Decimal("0")
UNION_STATES = (OrderState.UNION_NEW, OrderState.UNION_REVIEW)
SUPPLIER_REVIEW_STATES = (OrderState.SUPPLIER_NEW, OrderState.SUPPLIER_REVIEW)
IN_PROGRESS = (OrderState.EXECUTION, OrderState.PARTIAL)


def parse(params) -> dict:
    return registry.parse_filters(params)


# ----------------------------------------------------------------------------- kesh
def version() -> int:
    v = cache.get(VERSION_KEY)
    if v is None:
        cache.set(VERSION_KEY, 1, None)
        return 1
    return int(v)


def bump_version() -> None:
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        cache.set(VERSION_KEY, 2, None)


def _key(name, cabinet, is_admin, f) -> str:
    who = str(cabinet.pk) if cabinet is not None else ("admin" if is_admin else "none")
    raw = json.dumps({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in f.items()}, sort_keys=True, ensure_ascii=False)
    return f"yashil:stats:v{version()}:{name}:{who}:{hashlib.sha1(raw.encode()).hexdigest()[:16]}"


def _cached(name, cabinet, is_admin, f, compute):
    key = _key(name, cabinet, is_admin, f)
    hit = cache.get(key)
    if hit is not None:
        return hit
    value = compute(cabinet, is_admin, f)
    cache.set(key, value, TTL)
    return value


# ----------------------------------------------------------------------------- buyurtmalar bazasi
def order_queryset(cabinet, is_admin: bool, f: dict):
    """Ko'lam + filtrlar buyurtma darajasida (qoralamalar yo'q)."""
    qs = orders_for_cabinet(cabinet, is_admin).exclude(state=OrderState.DRAFT)
    return registry.apply_order_filters(qs, f)


def _dec(value) -> str:
    return format(Decimal(value or 0).normalize(), "f")


# ----------------------------------------------------------------------------- kartalar (15.1)
def _cards(cabinet, is_admin, f) -> dict:
    qs = order_queryset(cabinet, is_admin, f)
    by_state = {r["state"]: r["n"] for r in qs.order_by().values("state").annotate(n=Count("id", distinct=True))}
    g = lambda *states: sum(by_state.get(s, 0) for s in states)  # noqa: E731
    late = qs.filter(late_workdays__gt=0).order_by().values("overdue_stage").annotate(n=Count("id", distinct=True))
    late_by = {r["overdue_stage"]: r["n"] for r in late}
    return {
        "total": sum(by_state.values()),
        "new": g(OrderState.UNION_NEW, OrderState.SUPPLIER_NEW),
        "new_union": g(OrderState.UNION_NEW),
        "new_supplier": g(OrderState.SUPPLIER_NEW),
        "reviewing": g(OrderState.UNION_REVIEW, OrderState.SUPPLIER_REVIEW),
        "reviewing_union": g(OrderState.UNION_REVIEW),
        "reviewing_supplier": g(OrderState.SUPPLIER_REVIEW),
        "reviewed": g(OrderState.EXECUTION, OrderState.PARTIAL),
        "execution": g(OrderState.EXECUTION),
        "partial": g(OrderState.PARTIAL),
        "done": g(OrderState.CLOSED),
        "returned": g(OrderState.RETURNED),
        "cancelled": g(OrderState.CANCELLED),
        "overdue": sum(late_by.values()),
        "overdue_review": late_by.get("review", 0),
        "overdue_delivery": late_by.get("delivery", 0),
        "filters_label": registry.filters_label(f),
    }


def cards(cabinet, is_admin: bool, f: dict) -> dict:
    return _cached("cards", cabinet, is_admin, f, _cards)


# ----------------------------------------------------------------------------- ko'chatlar farqi (15.2)
def _seedlings(cabinet, is_admin, f) -> dict:
    lines = registry.apply_filters(registry.base_queryset(cabinet, is_admin), f).filter(
        catalog_item__category=CatalogItem.Category.SEEDLING,
    ).exclude(order__state=OrderState.CANCELLED)
    rows = (
        lines.order_by().values("catalog_item__code", "catalog_item__name_cyr", "catalog_item__unit", "catalog_item__order")
        .annotate(ordered=Sum("qty"), accepted=Sum("accepted_qty"), orders=Count("order", distinct=True),
                  returned_open=Sum("qty", filter=Q(order__state=OrderState.RETURNED)))
        .order_by("catalog_item__order", "catalog_item__code")
    )
    line_ids = list(lines.values_list("id", flat=True))
    pending = {
        r["order_line__catalog_item__code"]: r["s"]
        for r in ActLine.objects.filter(order_line_id__in=line_ids, act_version__act__status=Act.Status.REVIEW,
                                        act_version__superseded_at__isnull=True)
        .order_by().values("order_line__catalog_item__code").annotate(s=Sum("qty"))
    }
    items, tot = [], {"ordered": ZERO, "accepted": ZERO, "pending": ZERO, "returned_open": ZERO, "diff": ZERO}
    for r in rows:
        o, a = r["ordered"] or ZERO, r["accepted"] or ZERO
        p, ro = pending.get(r["catalog_item__code"], ZERO) or ZERO, r["returned_open"] or ZERO
        items.append({
            "item_code": r["catalog_item__code"], "item": r["catalog_item__name_cyr"], "unit": r["catalog_item__unit"],
            "unit_cyr": UNIT_LABELS.get(r["catalog_item__unit"], (r["catalog_item__unit"],))[0], "orders": r["orders"],
            "ordered": _dec(o), "accepted": _dec(a), "pending": _dec(p), "returned_open": _dec(ro), "diff": _dec(o - a),
        })
        tot["ordered"] += o; tot["accepted"] += a; tot["pending"] += p; tot["returned_open"] += ro; tot["diff"] += o - a
    return {"items": items, "totals": {k: _dec(v) for k, v in tot.items()}, "filters_label": registry.filters_label(f)}


def seedlings(cabinet, is_admin: bool, f: dict) -> dict:
    return _cached("seedlings", cabinet, is_admin, f, _seedlings)


# ----------------------------------------------------------------------------- orqada qolayotgan tashkilotlar (15.3)
def _org_rows(qs, group_field, kind, late_states, delivery_states, name_of):
    agg = (
        qs.order_by().values(group_field).annotate(
            total=Count("id", distinct=True),
            in_progress=Count("id", filter=Q(state__in=IN_PROGRESS), distinct=True),
            done=Count("id", filter=Q(state=OrderState.CLOSED), distinct=True),
            waiting=Count("id", filter=Q(state__in=late_states), distinct=True),
            review_late=Count("id", filter=Q(state__in=late_states, late_workdays__gt=0), distinct=True),
            delivery_late=Count("id", filter=Q(state__in=delivery_states, late_workdays__gt=0), distinct=True),
            max_late=Max("late_workdays", filter=Q(late_workdays__gt=0) & (Q(state__in=late_states) | Q(state__in=delivery_states))),
        )
    )
    rows = []
    for r in agg:
        if r[group_field] is None:
            continue
        late = r["review_late"] + r["delivery_late"]
        rows.append({
            "kind": kind, "id": str(r[group_field]), "name": name_of(r[group_field]),
            "total": r["total"], "in_progress": r["in_progress"], "done": r["done"], "waiting": r["waiting"],
            "review_late": r["review_late"], "delivery_late": r["delivery_late"], "late": late,
            "max_late_days": r["max_late"] or 0, "has_late": late > 0,
            "done_pct": format(Decimal(r["done"] * 100) / Decimal(r["total"]), ".1f") if r["total"] else "0.0",
        })
    return rows


def _organizations(cabinet, is_admin, f) -> list:
    qs = order_queryset(cabinet, is_admin, f)
    supplier_names = dict(qs.order_by().values_list("supplier_org_id", "supplier_org__name").distinct())
    unit_names = dict(UnionUnit.objects.filter(id__in=qs.values("union_unit_id")).values_list("id", "name"))
    rows = _org_rows(qs, "supplier_org_id", "supplier", SUPPLIER_REVIEW_STATES, IN_PROGRESS, lambda i: supplier_names.get(i, ""))
    rows += _org_rows(qs.filter(union_unit__isnull=False), "union_unit_id", "union", UNION_STATES, (), lambda i: unit_names.get(i, ""))
    rows.sort(key=lambda r: (not r["has_late"], -r["late"], -r["max_late_days"], r["name"]))
    return rows


def organizations(cabinet, is_admin: bool, f: dict) -> list:
    return _cached("organizations", cabinet, is_admin, f, _organizations)
