"""
Ombor ledger servisi (TZ §9, §22.1, §22.3).

    default_warehouse(org)                       tashkilotning asosiy ombori (yo'q bo'lsa yaratiladi)
    balance(warehouse, item)                     hisob qoldig'i = posted harakatlar yig'indisi
    warehouse_summary(org)                       pozitsiya bo'yicha: boshlang'ich, kirim, ajratilgan, tiklangan, qoldiq, yetishmovchilik
    post_opening / post_receipt                  hujjatli kirim (kirim raqami takrori — ogohlantirish)
    request_reversal / approve_reversal / reject_reversal
    allocate_for_acceptance(order, cabinet, ...) ijroga qabulda bir martalik ajratish (o'rmon manfiy, DM qat'iy)
    release_for_cancel(order_line, qty, ...)     bekor qilishda yetkazilmagan qismni tiklash
    capacity_available(org, item, period)        DM xizmat quvvati qoldig'i

Barcha yozuvlar chaqiruvchi tranzaksiyasi ichida; ombor qatori `select_for_update` bilan qulflanadi.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.yashil.models import (
    Acceptance,
    CatalogItem,
    Order,
    ServiceAllocation,
    ServiceCapacity,
    StockMovement,
    SupplierProfile,
    Warehouse,
    YashilMembership,
)
from apps.yashil.services.transitions import TransitionError

T = YashilMembership.MemberType
K = StockMovement.Kind
S = StockMovement.Status
ZERO = Decimal("0")


class LedgerError(TransitionError):
    """Ombor qoidasi buzilishi; `extra` javobga qo'shiladi (masalan `lines`)."""

    def __init__(self, message, *, code="business_rule", field=None, status=422, extra=None):
        super().__init__(message, code=code, field=field, status=status)
        self.extra = extra or {}


def _dec(value) -> str:
    return format(Decimal(value).normalize(), "f") if value is not None else None


def default_warehouse(organization) -> Warehouse:
    wh = Warehouse.objects.filter(organization=organization, is_default=True).first()
    if wh is None:
        wh, _ = Warehouse.objects.get_or_create(organization=organization, name="Асосий омбор", defaults={"is_default": True})
    return wh


def supplier_type_of(organization) -> str | None:
    profile = SupplierProfile.objects.filter(organization=organization).first()
    return profile.supplier_type if profile else None


def _lock(warehouse: Warehouse) -> Warehouse:
    return Warehouse.objects.select_for_update().get(pk=warehouse.pk)


def _require_supplier(cabinet, organization_id, *, sign=False):
    if cabinet is None or cabinet.member_type != T.SUPPLIER or cabinet.organization_id != organization_id:
        raise LedgerError("Омбор амалини фақат етказиб берувчи кабинети бажаради", code="forbidden", status=403)
    if sign and not cabinet.can_sign:
        raise LedgerError("Тасдиқлаш учун имзолаш ҳуқуқи керак", code="cannot_sign", status=403)
    if not sign and not cabinet.can_prepare:
        raise LedgerError("Бу кабинетда омбор амали ҳуқуқи йўқ", code="cannot_prepare", status=403)


def _check_item(warehouse: Warehouse, item: CatalogItem):
    if item.item_type != CatalogItem.ItemType.GOODS:
        raise LedgerError("Хизмат омборда юритилмайди — хизмат қуввати орқали", code="item_not_goods", field="catalog_item")
    if item.supplier_type != supplier_type_of(warehouse.organization):
        raise LedgerError("Позиция бу етказиб берувчи йўналишига тегишли эмас", code="item_supplier_mismatch", field="catalog_item")


def _check_qty(qty):
    try:
        qty = Decimal(qty)
    except Exception:
        raise LedgerError("Миқдор нотўғри", code="invalid_qty", field="qty", status=400)
    if qty <= 0:
        raise LedgerError("Миқдор мусбат бўлиши керак", code="invalid_qty", field="qty")
    return qty


# ----------------------------------------------------------------------------- hisob
def balance(warehouse: Warehouse, item: CatalogItem) -> Decimal:
    total = StockMovement.objects.filter(warehouse=warehouse, catalog_item=item, status=S.POSTED).aggregate(s=Sum("qty"))["s"]
    return total if total is not None else ZERO


def _totals_by_item(warehouse: Warehouse) -> dict:
    rows = (StockMovement.objects.filter(warehouse=warehouse, status=S.POSTED)
            .values("catalog_item_id", "kind").annotate(s=Sum("qty")))
    out: dict = {}
    for r in rows:
        out.setdefault(r["catalog_item_id"], {})[r["kind"]] = r["s"] or ZERO
    return out


def warehouse_summary(organization, warehouse: Warehouse | None = None) -> list[dict]:
    """Yetkazib beruvchi katalogidagi har pozitsiya uchun ko'rsatkichlar (TZ §9.1, §9.4)."""
    warehouse = warehouse or default_warehouse(organization)
    stype = supplier_type_of(organization)
    totals = _totals_by_item(warehouse)
    items = CatalogItem.objects.filter(supplier_type=stype, item_type=CatalogItem.ItemType.GOODS, is_active=True).order_by("order", "code")
    rows = []
    for item in items:
        t = totals.get(item.id, {})
        opening, receipt = t.get(K.OPENING, ZERO), t.get(K.RECEIPT, ZERO)
        allocated = -t.get(K.ALLOCATE, ZERO)
        released, returned, reversal = t.get(K.RELEASE, ZERO), t.get(K.RETURN_IN, ZERO), t.get(K.REVERSAL, ZERO)
        bal = opening + receipt + released + returned + reversal - allocated
        rows.append({
            "warehouse_id": str(warehouse.id), "catalog_item_id": str(item.id), "code": item.code,
            "name_cyr": item.name_cyr, "name_lat": item.name_lat, "unit": item.unit, "precision": item.precision,
            "opening": _dec(opening), "received": _dec(receipt + reversal), "allocated": _dec(allocated),
            "released": _dec(released), "returned": _dec(returned), "balance": _dec(bal),
            "shortage": _dec(max(ZERO, -bal)),
            "pending_reversals": StockMovement.objects.filter(warehouse=warehouse, catalog_item=item, status=S.PENDING).count(),
        })
    return rows


def capacity_available(organization, item: CatalogItem, period: str) -> Decimal:
    cap = ServiceCapacity.objects.filter(organization=organization, catalog_item=item, period=period).first()
    if cap is None:
        return ZERO
    used = ServiceAllocation.objects.filter(organization=organization, catalog_item=item, period=period).aggregate(s=Sum("qty"))["s"] or ZERO
    return cap.capacity - used


# ----------------------------------------------------------------------------- kirim
def _post(warehouse, item, kind, qty, cabinet, **fields) -> StockMovement:
    return StockMovement.objects.create(
        warehouse=warehouse, catalog_item=item, kind=kind, qty=qty, status=S.POSTED,
        requested_by_membership=cabinet, created_by=cabinet.user if cabinet else None, **fields,
    )


@transaction.atomic
def post_opening(warehouse, item, qty, cabinet, *, doc_number="", doc_date=None, note="", file=None) -> StockMovement:
    """Boshlang'ich qoldiq — pozitsiya uchun bir marta, hujjat bilan (TZ §9.3)."""
    _require_supplier(cabinet, warehouse.organization_id)
    _check_item(warehouse, item)
    qty = _check_qty(qty)
    _lock(warehouse)
    if StockMovement.objects.filter(warehouse=warehouse, catalog_item=item, kind=K.OPENING).exists():
        raise LedgerError("Бу позиция учун бошланғич қолдиқ аллақачон киритилган — кирим ёки тескари операция ишлатинг",
                          code="opening_exists", field="catalog_item", status=409)
    return _post(warehouse, item, K.OPENING, qty, cabinet, doc_number=doc_number[:100], doc_date=doc_date, note=note[:1000], file=file)


@transaction.atomic
def post_receipt(warehouse, item, qty, cabinet, *, doc_number="", doc_date=None, note="", file=None):
    """Kirim. Qaytaradi (movement, warnings) — hujjat raqami takrori ogohlantirish, taqiq emas."""
    _require_supplier(cabinet, warehouse.organization_id)
    _check_item(warehouse, item)
    qty = _check_qty(qty)
    _lock(warehouse)
    warnings = []
    if doc_number and StockMovement.objects.filter(warehouse=warehouse, doc_number=doc_number, kind__in=(K.RECEIPT, K.OPENING)).exists():
        warnings.append({"code": "doc_number_duplicate", "message": f"«{doc_number}» рақамли кирим аввал киритилган — текшириб кўринг"})
    mv = _post(warehouse, item, K.RECEIPT, qty, cabinet, doc_number=doc_number[:100], doc_date=doc_date, note=note[:1000], file=file)
    return mv, warnings


@transaction.atomic
def post_return_in(warehouse, item, qty, cabinet, *, doc_number="", doc_date=None, note="", file=None) -> StockMovement:
    """Haqiqiy qaytarish hujjati bilan omborga qayta kirim (TZ §9.3)."""
    _require_supplier(cabinet, warehouse.organization_id)
    _check_item(warehouse, item)
    qty = _check_qty(qty)
    if not (doc_number or "").strip():
        raise LedgerError("Қайтариш ҳужжати рақами мажбурий", code="doc_required", field="doc_number")
    _lock(warehouse)
    return _post(warehouse, item, K.RETURN_IN, qty, cabinet, doc_number=doc_number[:100], doc_date=doc_date, note=note[:1000], file=file)


# ----------------------------------------------------------------------------- teskari operatsiya
@transaction.atomic
def request_reversal(movement: StockMovement, cabinet, *, note: str) -> StockMovement:
    _require_supplier(cabinet, movement.warehouse.organization_id)
    if movement.kind not in StockMovement.REVERSIBLE_KINDS or movement.status != S.POSTED:
        raise LedgerError("Бу ҳаракат тескари операция билан тузатилмайди", code="not_reversible", status=409)
    if not (note or "").strip():
        raise LedgerError("Тескари операция асоси мажбурий", code="note_required", field="note")
    _lock(movement.warehouse)
    if movement.reversals.filter(status=S.POSTED).exists():
        raise LedgerError("Ҳаракат аллақачон тескари операция билан тузатилган", code="already_reversed", status=409)
    if movement.reversals.filter(status=S.PENDING).exists():
        raise LedgerError("Бу ҳаракат учун тасдиқ кутаётган тескари операция бор", code="reversal_pending", status=409)
    return StockMovement.objects.create(
        warehouse=movement.warehouse, catalog_item=movement.catalog_item, kind=K.REVERSAL, qty=-movement.qty,
        status=S.PENDING, reversal_of=movement, doc_number=movement.doc_number, doc_date=movement.doc_date,
        note=note.strip()[:1000], requested_by_membership=cabinet, created_by=cabinet.user,
    )


def _decide_reversal(rev: StockMovement, cabinet, *, approve: bool, note: str):
    _require_supplier(cabinet, rev.warehouse.organization_id, sign=True)
    _lock(rev.warehouse)
    rev = StockMovement.objects.select_for_update().get(pk=rev.pk)
    if rev.kind != K.REVERSAL or rev.status != S.PENDING:
        raise LedgerError("Тескари операция тасдиқ кутмаяпти", code="state_conflict", status=409)
    rev.status = S.POSTED if approve else S.REJECTED
    rev.approved_by = cabinet.user
    rev.approved_at = timezone.now()
    rev.decision_note = (note or "")[:1000]
    rev.save(update_fields=["status", "approved_by", "approved_at", "decision_note", "updated_at"])
    return rev


@transaction.atomic
def approve_reversal(rev: StockMovement, cabinet, note: str = "") -> StockMovement:
    return _decide_reversal(rev, cabinet, approve=True, note=note)


@transaction.atomic
def reject_reversal(rev: StockMovement, cabinet, *, note: str) -> StockMovement:
    if not (note or "").strip():
        raise LedgerError("Рад этиш сабаби мажбурий", code="note_required", field="note")
    return _decide_reversal(rev, cabinet, approve=False, note=note)


# ----------------------------------------------------------------------------- ijroga qabulda ajratish
def _period(day) -> str:
    return f"{day.year:04d}-{day.month:02d}"


@transaction.atomic
def allocate_for_acceptance(order: Order, cabinet, *, accepted_on, delivery_due, executor_name: str) -> Acceptance:
    """
    Har qator uchun bir martalik ajratish (TZ §22.1 4–5-qadamlar). O'rmon: chegara yo'q
    (manfiy qoldiq = ta'minlanmagan ehtiyoj). DM: har qator uchun qoldiq (tovar) yoki
    oy quvvati (xizmat) yetarli bo'lishi shart, aks holda 422 `stock_insufficient` va
    hech narsa yozilmaydi (chaqiruvchi tranzaksiyasi bekor bo'ladi).
    """
    if Acceptance.objects.filter(order=order).exists():
        raise LedgerError("Буюртма аллақачон ижрога қабул қилинган", code="acceptance_exists", status=409)
    warehouse = _lock(default_warehouse(order.supplier_org))
    strict = supplier_type_of(order.supplier_org) == SupplierProfile.SupplierType.DM
    period = _period(accepted_on)
    lines = list(order.lines.select_related("catalog_item").order_by("position", "created_at"))
    insufficient, plan = [], []
    for line in lines:
        item = line.catalog_item
        if item.item_type == CatalogItem.ItemType.SERVICE:
            available = capacity_available(order.supplier_org, item, period)
            kind = "capacity"
        else:
            available = balance(warehouse, item)
            kind = "stock"
        after = available - line.qty
        plan.append((line, item, kind, available, after))
        if strict and after < 0:
            insufficient.append({"order_line_id": str(line.id), "code": item.code, "name_cyr": item.name_cyr, "kind": kind,
                                 "need": _dec(line.qty), "available": _dec(max(ZERO, available)), "unit": item.unit})
    if insufficient:
        raise LedgerError("Омборда ёки хизмат қувватида етарли ресурс йўқ — кирим киритиб қайта қабул қилинг",
                          code="stock_insufficient", extra={"lines": insufficient})
    acceptance = Acceptance.objects.create(
        order=order, warehouse=warehouse, accepted_by=cabinet.user, accepted_by_membership=cabinet,
        accepted_on=accepted_on, delivery_due=delivery_due, executor_name=executor_name, created_by=cabinet.user,
    )
    result_lines = []
    for line, item, kind, available, after in plan:
        if kind == "capacity":
            ServiceAllocation.objects.create(organization=order.supplier_org, catalog_item=item, period=period,
                                             acceptance=acceptance, order_line=line, qty=line.qty, created_by=cabinet.user)
        else:
            StockMovement.objects.create(
                warehouse=warehouse, catalog_item=item, kind=K.ALLOCATE, qty=-line.qty, status=S.POSTED,
                acceptance=acceptance, order_line=line, note=f"Буюртма {order.number}",
                requested_by_membership=cabinet, created_by=cabinet.user,
            )
        result_lines.append({
            "order_line_id": str(line.id), "code": item.code, "name_cyr": item.name_cyr, "unit": item.unit, "kind": kind,
            "qty": _dec(line.qty), "balance_before": _dec(available), "balance_after": _dec(after),
            "shortage": _dec(max(ZERO, -after)), "period": period if kind == "capacity" else None,
        })
    acceptance.result = {"warehouse": warehouse.name, "warehouse_id": str(warehouse.id), "strict": strict,
                         "lines": result_lines, "has_shortage": any(l["shortage"] != "0" for l in result_lines)}
    acceptance.save(update_fields=["result", "updated_at"])
    return acceptance


@transaction.atomic
def release_for_cancel(order_line, qty, *, cabinet, note: str = "") -> StockMovement | None:
    """Bekor qilingan, yetkazilmagan qismga ajratishni tiklash (TZ §9.3). Xizmat qatorida quvvat sarfi qisqaradi."""
    qty = _check_qty(qty)
    order = order_line.order
    acceptance = Acceptance.objects.filter(order=order).first()
    if acceptance is None:
        return None
    item = order_line.catalog_item
    if item.item_type == CatalogItem.ItemType.SERVICE:
        alloc = ServiceAllocation.objects.select_for_update().filter(order_line=order_line).first()
        if alloc is not None:
            alloc.qty = max(ZERO, alloc.qty - qty)
            alloc.save(update_fields=["qty", "updated_at"])
        return None
    warehouse = _lock(acceptance.warehouse)
    return StockMovement.objects.create(
        warehouse=warehouse, catalog_item=item, kind=K.RELEASE, qty=qty, status=S.POSTED, acceptance=acceptance,
        order_line=order_line, note=(note or f"Буюртма {order.number} бекор қилинди")[:1000],
        requested_by_membership=cabinet, created_by=cabinet.user if cabinet else None,
    )
