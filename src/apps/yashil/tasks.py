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
    """{(kind, key): {"order_id", "warehouse_id", "details"}} — hozirgi holatdagi nomuvofiqliklar."""
    from apps.yashil.services.acts import accepted_by_line
    from apps.yashil.services.ledger import _totals_by_item, supplier_type_of

    found = {}
    for acc in Acceptance.objects.select_related("order").prefetch_related("order__lines__catalog_item"):
        for line in acc.order.lines.all():
            base = {"order_id": acc.order_id, "warehouse_id": acc.warehouse_id,
                    "details": {"order": acc.order.number, "code": line.catalog_item.code, "qty": _dec(line.qty)}}
            if line.catalog_item.item_type == CatalogItem.ItemType.GOODS:
                n = StockMovement.objects.filter(acceptance=acc, order_line=line, kind=StockMovement.Kind.ALLOCATE, status=StockMovement.Status.POSTED).count()
                if n == 0:
                    found[("allocation_missing", str(line.id))] = base
                elif n > 1:
                    found[("allocation_duplicate", str(line.id))] = {**base, "details": {**base["details"], "count": n}}
            elif not ServiceAllocation.objects.filter(order_line=line).exists():
                found[("allocation_missing", str(line.id))] = base
    for order in Order.objects.filter(state__in=(OrderState.EXECUTION, OrderState.PARTIAL, OrderState.CLOSED)).prefetch_related("lines__catalog_item"):
        accepted = accepted_by_line(order)
        incomplete = False
        for line in order.lines.all():
            if accepted[line.id] > line.qty:
                found[("accepted_exceeds", str(line.id))] = {"order_id": order.id, "warehouse_id": None, "details": {
                    "order": order.number, "code": line.catalog_item.code, "ordered": _dec(line.qty), "accepted": _dec(accepted[line.id])}}
            if accepted[line.id] < line.qty:
                incomplete = True
        if order.state == OrderState.CLOSED and incomplete:
            found[("closed_incomplete", str(order.id))] = {"order_id": order.id, "warehouse_id": None, "details": {"order": order.number}}
    items = {i.id: i for i in CatalogItem.objects.all()}
    for wh in Warehouse.objects.select_related("organization"):
        forest = supplier_type_of(wh.organization) == SupplierProfile.SupplierType.FOREST
        for item_id, totals in _totals_by_item(wh).items():
            bal = sum(totals.values())
            if bal < 0:
                item = items.get(item_id)
                kind = "stock_negative" if forest else "stock_negative_dm"
                found[(kind, f"{wh.id}:{item_id}")] = {"order_id": None, "warehouse_id": wh.id, "details": {
                    "organization": wh.organization.name, "code": item.code if item else str(item_id),
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
