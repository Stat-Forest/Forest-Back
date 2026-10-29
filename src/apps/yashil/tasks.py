"""
Davriy vazifalar (TZ §8.2, §22.4; javob Д5).

deadline_reminders — har ish kuni ertalab: ko'rib chiqishga 1 ish kuni qolganda,
yetkazishga 3 va 1 ish kuni qolganda mas'ul kabinetga eslatma; muddat buzilganda
mas'ulga, mahallaga (yetkazish) va kuzatuvchilarga «muddat buzildi» — har kuni bir marta.
"""
from datetime import date

from celery import shared_task
from django.utils import timezone

from apps.yashil.models import (
    DELIVERY_STATES,
    Acceptance,
    Act,
    CatalogItem,
    Order,
    OrderState,
    ReconcileIssue,
    ServiceAllocation,
    StockMovement,
    SupplierProfile,
    Warehouse,
    YashilMembership,
    YashilNotification,
)
from apps.yashil.services import notifications as notif
from apps.yashil.services.scope import memberships_active_for_target
from apps.yashil.services.workdays import (
    add_workdays,
    calendar_from_db,
    count_workdays,
    local_date,
    overdue_workdays,
    review_deadline,
)

T = YashilMembership.MemberType
K = YashilNotification.Kind
REVIEW_STATES = (OrderState.UNION_NEW, OrderState.UNION_REVIEW, OrderState.SUPPLIER_NEW, OrderState.SUPPLIER_REVIEW)
DELIVERY_REMIND_AT = (3, 1)
REVIEW_REMIND_AT = (1,)


def _already_sent(order, kind, title, membership_ids) -> bool:
    """Bir xil matnli xabar (sarlavhada qolgan/o'tgan kunlar soni bor) bir marta yuboriladi."""
    return YashilNotification.objects.filter(
        order=order, kind=kind, title=title, membership_id__in=membership_ids,
    ).exists()


def _send(order, memberships, kind, title, body, today):
    memberships = list(memberships)
    if not memberships or _already_sent(order, kind, title, [m.id for m in memberships]):
        return 0
    notif.notify_memberships(memberships, kind=kind, title=title, body=body, order=order)
    return len(memberships)


def _responsible(order):
    if order.state in (OrderState.UNION_NEW, OrderState.UNION_REVIEW):
        return memberships_active_for_target(T.UNION, union_unit_id=order.union_unit_id)
    return memberships_active_for_target(T.SUPPLIER, organization_id=order.supplier_org_id)


def _process_review(order, today, cal) -> int:
    from apps.yashil.services.rules import review_workdays_for

    due = review_deadline(order.review_segments_as_tuples_dates(), cal, review_workdays_for(order))
    if due is None:
        return 0
    sent = 0
    left = count_workdays(today, due, cal) if today <= due else -overdue_workdays(due, today, cal)
    if left in REVIEW_REMIND_AT:
        sent += _send(order, _responsible(order), K.DEADLINE_REMINDER,
                      f"{order.number}: кўриб чиқишга {left} иш куни қолди", f"Охирги муддат {due:%d.%m.%Y}", today)
    elif left < 0:
        days = -left
        title = f"{order.number}: кўриб чиқиш муддати {days} иш кунига бузилган"
        sent += _send(order, _responsible(order), K.OVERDUE, title, f"Охирги муддат {due:%d.%m.%Y} эди", today)
        sent += _send(order, memberships_active_for_target(T.OBSERVER), K.OVERDUE, title, order.mahalla.name, today)
    return sent


def _process_delivery(order, today, cal) -> int:
    due = order.delivery_due
    if not due:
        return 0
    sent = 0
    left = count_workdays(today, due, cal) if today <= due else -overdue_workdays(due, today, cal)
    supplier = memberships_active_for_target(T.SUPPLIER, organization_id=order.supplier_org_id)
    if left in DELIVERY_REMIND_AT:
        sent += _send(order, supplier, K.DEADLINE_REMINDER,
                      f"{order.number}: етказишга {left} иш куни қолди", f"Охирги муддат {due:%d.%m.%Y}", today)
    elif left < 0:
        days = -left
        title = f"{order.number}: етказиш муддати {days} иш кунига бузилган"
        sent += _send(order, supplier, K.OVERDUE, title, f"Охирги муддат {due:%d.%m.%Y} эди", today)
        sent += _send(order, memberships_active_for_target(T.MAHALLA, mahalla_id=order.mahalla_id), K.OVERDUE, title, order.supplier_org.name, today)
        sent += _send(order, memberships_active_for_target(T.OBSERVER), K.OVERDUE, title, order.mahalla.name, today)
    return sent


def _process_act_review(act, today, cal) -> int:
    """Akt mahalla tasdig'ida 3 ish kunidan ortiq tursa — mahallaga eslatma (javob Д3), har kuni bir marta."""
    v = act.current_version
    if v is None or not v.submitted_at:
        return 0
    from apps.yashil.services.rules import get as rule

    due = add_workdays(local_date(v.submitted_at), rule("act_review_reminder_days", today), cal)
    if today <= due:
        return 0
    days = overdue_workdays(due, today, cal)
    title = f"{act.number}: далолатнома тасдиғи {days} иш кунига кечикмоқда"
    return _send(act.order, memberships_active_for_target(T.MAHALLA, mahalla_id=act.order.mahalla_id), K.DEADLINE_REMINDER, title,
                 f"Етказиб берувчи {local_date(v.submitted_at):%d.%m.%Y} да юборган", today)


@shared_task(name="yashil.deadline_reminders", ignore_result=True)
def deadline_reminders(today: date | None = None) -> int:
    """Qaytaradi: yuborilgan xabarnomalar soni."""
    today = today or local_date(timezone.now())
    cal = calendar_from_db()
    # Avval kechikish ustunlari (reestr filtri va statistika kartalari shunga qaraydi)
    from apps.yashil.services.deadlines import recalc_all

    recalc_all(today=today, cal=cal)
    sent = 0
    for order in Order.objects.filter(state__in=REVIEW_STATES).select_related("mahalla", "supplier_org").prefetch_related("review_segments"):
        sent += _process_review(order, today, cal)
    for order in Order.objects.filter(state__in=DELIVERY_STATES, delivery_due__isnull=False).select_related("mahalla", "supplier_org"):
        sent += _process_delivery(order, today, cal)
    for act in Act.objects.filter(status=Act.Status.REVIEW).select_related("order__mahalla", "current_version"):
        sent += _process_act_review(act, today, cal)
    return sent


# ----------------------------------------------------------------------------- tungi solishtirish (TZ §22.3)
ERROR_KINDS = ("allocation_missing", "allocation_duplicate", "accepted_exceeds", "closed_incomplete", "stock_negative_dm")


def _dec(value) -> str:
    from decimal import Decimal

    return format(Decimal(value).normalize(), "f")


def _collect_issues() -> dict:
    """{(kind, key): {"order_id", "warehouse_id", "details"}} — hozirgi holatdagi nomuvofiqliklar.

    Yig'ma so'rovlar bilan (100 ming buyurtmada ham bir necha so'rov): har qator uchun
    alohida so'rov tungi vazifani va bekapdagi yaxlitlik tekshiruvini daqiqalarga cho'zardi.
    """
    from django.db.models import Count, Sum

    from apps.yashil.models import ActLine, Act, OrderLine
    from apps.yashil.services.ledger import supplier_type_of

    found = {}
    alloc_counts = {
        (r["acceptance_id"], r["order_line_id"]): r["n"]
        for r in StockMovement.objects.filter(kind=StockMovement.Kind.ALLOCATE, status=StockMovement.Status.POSTED, acceptance__isnull=False)
        .values("acceptance_id", "order_line_id").annotate(n=Count("id"))
    }
    service_lines = set(ServiceAllocation.objects.values_list("order_line_id", flat=True))
    accepted_lines = (OrderLine.objects.filter(order__acceptance__isnull=False)
                      .values("id", "qty", "order_id", "order__number", "order__acceptance__id", "order__acceptance__warehouse_id",
                              "catalog_item__code", "catalog_item__item_type"))
    for line in accepted_lines.iterator(chunk_size=5000):
        base = {"order_id": line["order_id"], "warehouse_id": line["order__acceptance__warehouse_id"],
                "details": {"order": line["order__number"], "code": line["catalog_item__code"], "qty": _dec(line["qty"])}}
        if line["catalog_item__item_type"] == CatalogItem.ItemType.GOODS:
            n = alloc_counts.get((line["order__acceptance__id"], line["id"]), 0)
            if n == 0:
                found[("allocation_missing", str(line["id"]))] = base
            elif n > 1:
                found[("allocation_duplicate", str(line["id"]))] = {**base, "details": {**base["details"], "count": n}}
        elif line["id"] not in service_lines:
            found[("allocation_missing", str(line["id"]))] = base

    accepted_qty = {
        r["order_line_id"]: r["s"]
        for r in ActLine.objects.filter(act_version__act__status=Act.Status.APPROVED, act_version__superseded_at__isnull=True)
        .values("order_line_id").annotate(s=Sum("qty"))
    }
    incomplete_orders, closed_orders = set(), {}
    delivery_lines = (OrderLine.objects.filter(order__state__in=(OrderState.EXECUTION, OrderState.PARTIAL, OrderState.CLOSED))
                      .values("id", "qty", "order_id", "order__number", "order__state", "catalog_item__code"))
    for line in delivery_lines.iterator(chunk_size=5000):
        accepted = accepted_qty.get(line["id"]) or 0
        if accepted > line["qty"]:
            found[("accepted_exceeds", str(line["id"]))] = {"order_id": line["order_id"], "warehouse_id": None, "details": {
                "order": line["order__number"], "code": line["catalog_item__code"], "ordered": _dec(line["qty"]), "accepted": _dec(accepted)}}
        if accepted < line["qty"]:
            incomplete_orders.add(line["order_id"])
        if line["order__state"] == OrderState.CLOSED:
            closed_orders[line["order_id"]] = line["order__number"]
    for order_id, number in closed_orders.items():
        if order_id in incomplete_orders:
            found[("closed_incomplete", str(order_id))] = {"order_id": order_id, "warehouse_id": None, "details": {"order": number}}

    items = {i.id: i for i in CatalogItem.objects.all()}
    warehouses = {w.id: w for w in Warehouse.objects.select_related("organization")}
    balances = (StockMovement.objects.filter(status=StockMovement.Status.POSTED)
                .values("warehouse_id", "catalog_item_id").annotate(s=Sum("qty")))
    forest_cache = {}
    for r in balances:
        bal = r["s"] or 0
        if bal >= 0:
            continue
        wh = warehouses[r["warehouse_id"]]
        if wh.id not in forest_cache:
            forest_cache[wh.id] = supplier_type_of(wh.organization) == SupplierProfile.SupplierType.FOREST
        item = items.get(r["catalog_item_id"])
        kind = "stock_negative" if forest_cache[wh.id] else "stock_negative_dm"
        found[(kind, f"{wh.id}:{r['catalog_item_id']}")] = {"order_id": None, "warehouse_id": wh.id, "details": {
            "organization": wh.organization.name, "code": item.code if item else str(r["catalog_item_id"]),
            "name": item.name_cyr if item else "", "balance": _dec(bal), "shortage": _dec(-bal)}}
    return found


@shared_task(name="yashil.reconcile", ignore_result=True)
def reconcile() -> dict:
    """
    Har kecha: qoldiq = harakatlar yig'indisi; har qabul qatoriga bitta ajratish; qabul ≤ buyurtma;
    yopiq buyurtma to'liq. Xatolar `ReconcileIssue` + kuzatuvchilarga xabar; manfiy o'rmon qoldig'i
    xato emas — yetkazib beruvchiga bir marta (qoldiq musbat bo'lib yana manfiyga tushsa — qayta).
    """
    now = timezone.now()
    found = _collect_issues()
    open_issues = {(i.kind, i.key): i for i in ReconcileIssue.objects.filter(resolved_at__isnull=True)}
    new_errors = 0
    for (kind, key), data in found.items():
        if (kind, key) in open_issues:
            continue
        ReconcileIssue.objects.create(kind=kind, key=key, order_id=data["order_id"], warehouse_id=data["warehouse_id"], details=data["details"])
        d = data["details"]
        if kind == "stock_negative":
            wh = Warehouse.objects.select_related("organization").get(pk=data["warehouse_id"])
            notif.notify_memberships(
                memberships_active_for_target(T.SUPPLIER, organization_id=wh.organization_id), kind=K.STOCK_NEGATIVE,
                title=f"{d['code']}: манфий қолдиқ {d['balance']} — таъминлаш керак {d['shortage']}", body=d.get("name", ""),
            )
            continue
        new_errors += 1
        notif.notify_memberships(
            memberships_active_for_target(T.OBSERVER), kind=K.RECONCILE_ISSUE,
            title=f"Солиштириш: {kind} — {d.get('order') or d.get('organization') or key}", body=str(d)[:1000],
            order=Order.objects.filter(pk=data["order_id"]).first() if data["order_id"] else None,
        )
    resolved = 0
    for k, issue in open_issues.items():
        if k not in found:
            issue.resolved_at = now
            issue.save(update_fields=["resolved_at"])
            resolved += 1
    return {"checked_at": now.isoformat(timespec="seconds"), "issues_new": new_errors, "issues_resolved": resolved,
            "open_errors": sum(1 for k in found if k[0] in ERROR_KINDS), "negative_items": sum(1 for k in found if k[0] == "stock_negative")}


# ----------------------------------------------------------------------------- hisobot eksporti (TZ §14.2)
@shared_task(name="yashil.export_job", ignore_result=True)
def export_job(job_id: str):
    from apps.yashil.models import ExportJob
    from apps.yashil.services.exports import run_export

    job = ExportJob.objects.filter(pk=job_id, status__in=ExportJob.ACTIVE_STATUSES).first()
    if job is None:
        return None
    run_export(job)
    return job.status


@shared_task(name="yashil.export_cleanup", ignore_result=True)
def export_cleanup() -> int:
    from apps.yashil.services.exports import cleanup

    return cleanup()
