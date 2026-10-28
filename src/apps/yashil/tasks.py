"""
Davriy vazifalar (TZ §8.2, §22.4; javob Д5).

deadline_reminders — har ish kuni ertalab: ko'rib chiqishga 1 ish kuni qolganda,
yetkazishga 3 va 1 ish kuni qolganda mas'ul kabinetga eslatma; muddat buzilganda
mas'ulga, mahallaga (yetkazish) va kuzatuvchilarga «muddat buzildi» — har kuni bir marta.
"""
from datetime import date

from celery import shared_task
from django.utils import timezone

from apps.yashil.models import Order, OrderState, YashilMembership, YashilNotification
from apps.yashil.services import notifications as notif
from apps.yashil.services.scope import memberships_active_for_target
from apps.yashil.services.workdays import (
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
    due = review_deadline(order.review_segments_as_tuples_dates(), cal)
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


@shared_task(name="yashil.deadline_reminders", ignore_result=True)
def deadline_reminders(today: date | None = None) -> int:
    """Qaytaradi: yuborilgan xabarnomalar soni."""
    today = today or local_date(timezone.now())
    cal = calendar_from_db()
    sent = 0
    for order in Order.objects.filter(state__in=REVIEW_STATES).select_related("mahalla", "supplier_org").prefetch_related("review_segments"):
        sent += _process_review(order, today, cal)
    for order in Order.objects.filter(state=OrderState.EXECUTION, delivery_due__isnull=False).select_related("mahalla", "supplier_org"):
        sent += _process_delivery(order, today, cal)
    return sent
