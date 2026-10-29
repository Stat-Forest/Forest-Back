"""
DM xizmat quvvati (javob В5; TZ §19.2): tashkilot × xizmat × oy.

    capacity_payload(org, period) -> {"period", "rows": [...]}   (quvvat, sarf, bo'sh)
    set_capacity(org, period, rows, user) -> payload
Kim kiritadi: modul admini yoki DM'ning `can_sign` a'zosi (o'z tashkiloti).
Sarflangandan kam quvvat o'rnatilmaydi.
"""
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.yashil.models import CatalogItem, ServiceCapacity
from apps.yashil.services import ledger


class CapacityError(Exception):
    def __init__(self, message, *, code="validation", field=None, status=422):
        super().__init__(message)
        self.message, self.code, self.field, self.status = message, code, field, status


def check_period(period: str) -> str:
    period = (period or "").strip()
    if len(period) != 7 or period[4] != "-" or not period.replace("-", "").isdigit() or not 1 <= int(period[5:]) <= 12:
        raise CapacityError("`period` YYYY-MM кўринишида бўлиши керак", code="invalid_format", field="period", status=400)
    return period


def capacity_payload(org, period: str) -> dict:
    period = check_period(period)
    items = CatalogItem.objects.filter(supplier_type=ledger.supplier_type_of(org), item_type=CatalogItem.ItemType.SERVICE,
                                       is_active=True).order_by("order", "code")
    caps = {c.catalog_item_id: c.capacity for c in ServiceCapacity.objects.filter(organization=org, period=period)}
    rows = []
    for item in items:
        cap = caps.get(item.id)
        available = ledger.capacity_available(org, item, period)
        used = (cap - available) if cap is not None else ledger.ZERO
        rows.append({"catalog_item_id": str(item.id), "code": item.code, "name_cyr": item.name_cyr, "name_lat": item.name_lat,
                     "unit": item.unit, "capacity": ledger._dec(cap or 0), "used": ledger._dec(used), "available": ledger._dec(available)})
    return {"period": period, "organization": str(org.id), "rows": rows}


@transaction.atomic
def set_capacity(org, period: str, rows: list, user) -> dict:
    period = check_period(period)
    if not isinstance(rows, list):
        raise CapacityError("rows рўйхат бўлиши керак", field="rows", status=400)
    for i, row in enumerate(rows):
        item = CatalogItem.objects.filter(pk=(row or {}).get("catalog_item")).first()
        if item is None:
            raise CapacityError(f"{i + 1}-қатор: позиция топилмади", field="catalog_item")
        try:
            value = Decimal(str(row.get("capacity")))
        except (InvalidOperation, TypeError):
            raise CapacityError(f"{i + 1}-қатор: қувват нотўғри", field="capacity")
        if value < 0:
            raise CapacityError(f"{i + 1}-қатор: қувват манфий бўлмайди", field="capacity")
        cap = ServiceCapacity.objects.select_for_update().filter(organization=org, catalog_item=item, period=period).first()
        if cap is not None:
            used = cap.capacity - ledger.capacity_available(org, item, period)
            if value < used:
                raise CapacityError(f"{item.name_cyr}: сарфланган ({ledger._dec(used)}) дан кам қувват ўрнатилмайди", field="capacity")
        else:
            cap = ServiceCapacity(organization=org, catalog_item=item, period=period)
        if item.supplier_type != ledger.supplier_type_of(org):
            raise CapacityError(f"{item.name_cyr}: бу ташкилот йўналишига тегишли эмас", field="catalog_item")
        cap.capacity = value
        cap._history_user = user
        try:
            cap.save()
        except ValidationError as exc:
            msg = "; ".join(sum(exc.message_dict.values(), [])) if hasattr(exc, "message_dict") else "; ".join(exc.messages)
            raise CapacityError(f"{item.name_cyr}: {msg}", field="catalog_item")
    return capacity_payload(org, period)
