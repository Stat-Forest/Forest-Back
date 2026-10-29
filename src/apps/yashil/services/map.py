"""
Qabul qilingan buyurtmalar xaritasi (TZ §15.4; javob З4 — faqat kabinet ichida).

    points(cabinet, is_admin, f, bbox) -> {"count", "points": [...]}
Nuqtalar: `execution / partial / closed`, koordinatasi bor; filtrlar reestr bilan
bir xil; `bbox = lat_min,lon_min,lat_max,lon_max`. Klaster brauzerda.
"""
from decimal import Decimal, InvalidOperation

from apps.yashil import conf
from apps.yashil.models import OrderState
from apps.yashil.services import registry
from apps.yashil.services.scope import orders_for_cabinet
from apps.yashil.services.units import UNIT_LABELS

MAP_STATES = (OrderState.EXECUTION, OrderState.PARTIAL, OrderState.CLOSED)
ZERO = Decimal("0")


class MapError(Exception):
    def __init__(self, message, *, code="invalid_format", status=400, field=None, extra=None):
        super().__init__(message)
        self.message, self.code, self.status, self.field, self.extra = message, code, status, field, extra or {}


def parse_bbox(raw):
    if not raw:
        return None
    try:
        parts = [Decimal(p) for p in str(raw).split(",")]
        if len(parts) != 4:
            raise ValueError
    except (InvalidOperation, ValueError):
        raise MapError("bbox: lat_min,lon_min,lat_max,lon_max", field="bbox")
    return parts


def _dec(value):
    return format(Decimal(value).normalize(), "f") if value is not None else None


def points(cabinet, is_admin: bool, f: dict, bbox=None) -> dict:
    qs = orders_for_cabinet(cabinet, is_admin).filter(state__in=MAP_STATES, lat__isnull=False, lon__isnull=False)
    qs = registry.apply_order_filters(qs, f)
    if bbox:
        lat0, lon0, lat1, lon1 = bbox
        qs = qs.filter(lat__gte=lat0, lat__lte=lat1, lon__gte=lon0, lon__lte=lon1)
    total = qs.count()
    limit = conf.get("YASHIL_MAP_MAX_POINTS")
    if total > limit:
        raise MapError(f"Нуқталар жуда кўп ({total}). Фильтрни қисқартиринг ёки харитани яқинлаштиринг.",
                       code="too_many_points", status=422, extra={"count": total, "limit": limit})
    orders = list(qs.select_related("mahalla", "supplier_org").prefetch_related("lines__catalog_item").order_by("-accepted_on"))
    accepted = _accepted_for(orders)
    out = []
    for o in orders:
        out.append({
            "id": str(o.id), "number": o.number, "title": o.title, "state": o.state,
            "state_cyr": registry.STATE_LABELS_CYR.get(o.state, o.state), "route": o.route,
            "lat": _dec(o.lat), "lon": _dec(o.lon), "mahalla": o.mahalla.name, "supplier": o.supplier_org.name,
            "address": o.address, "area_ha": _dec(o.area_ha),
            "lines": [{
                "item": l.catalog_item.name_cyr, "unit_cyr": UNIT_LABELS.get(l.catalog_item.unit, (l.catalog_item.unit,))[0],
                "qty": _dec(l.qty), "accepted": _dec(accepted.get(l.id, ZERO)),
            } for l in o.lines.all()],
            "accepted_on": o.accepted_on.isoformat() if o.accepted_on else None,
            "delivery_due": o.delivery_due.isoformat() if o.delivery_due else None,
            "late_workdays": o.late_workdays,
        })
    return {"count": total, "points": out}


def _accepted_for(orders) -> dict:
    """Barcha buyurtma qatorlari uchun qabul miqdori bitta so'rovda."""
    from django.db.models import Sum

    from apps.yashil.models import Act, ActLine

    ids = [o.id for o in orders]
    totals = {}
    qs = ActLine.objects.filter(order_line__order_id__in=ids, act_version__act__status=Act.Status.APPROVED,
                                act_version__superseded_at__isnull=True)
    for row in qs.order_by().values("order_line_id").annotate(s=Sum("qty")):
        totals[row["order_line_id"]] = row["s"] or ZERO
    return totals
