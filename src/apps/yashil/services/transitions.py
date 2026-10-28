"""
Holat mashinasi (TZ §6, §7, §8): har o'tish — kim (kabinet turi + huquq), qaysi
holatdan, nima yozadi (event, segment, xabarnoma) — bitta tranzaksiyada.

    submit(order, cabinet, document_version)  mahalla, draft/returned -> union_new
    start_review(order, cabinet)              uyushma (union_new) / yetkazib beruvchi (supplier_new)
    forward(order, cabinet)                   uyushma, union_review -> supplier_new
    return_order(order, cabinet, ...)         uyushma (union_review) yoki yetkazib beruvchi (supplier_review) -> returned
    accept(order, cabinet, executor_name)     yetkazib beruvchi, supplier_review -> execution (ombor — 3-bosqich)
    allowed_actions(order, cabinet)           frontend tugmalari uchun
"""
from django.db import transaction
from django.utils import timezone

from apps.yashil.models import (
    Order,
    OrderEvent,
    OrderState,
    OrderVersion,
    ReviewSegment,
    YashilMembership,
    YashilNotification,
)
from apps.yashil.services import notifications as notif
from apps.yashil.services.numbering import next_order_number
from apps.yashil.services.scope import union_route
from apps.yashil.services.snapshot import build_snapshot
from apps.yashil.services.workdays import (
    REVIEW_WORKDAYS,
    calendar_from_db,
    delivery_deadline,
    local_date,
    overdue_workdays,
    review_days_used,
    review_deadline,
)

T = YashilMembership.MemberType
K = YashilNotification.Kind


class TransitionError(Exception):
    def __init__(self, message: str, *, code: str = "state_conflict", field: str | None = None, status: int = 409):
        super().__init__(message)
        self.message, self.code, self.field, self.status = message, code, field, status
        self.extra: dict = {}


def _forbidden(message="Бу амал учун ваколат йўқ", code="forbidden"):
    return TransitionError(message, code=code, status=403)


def _is_union_for(order, cabinet) -> bool:
    return cabinet.member_type == T.UNION and order.union_unit_id == cabinet.union_unit_id


def _is_supplier_for(order, cabinet) -> bool:
    return cabinet.member_type == T.SUPPLIER and order.supplier_org_id == cabinet.organization_id


def _is_mahalla_for(order, cabinet) -> bool:
    return cabinet.member_type == T.MAHALLA and order.mahalla_id == cabinet.mahalla_id


def _label(cabinet) -> str:
    return cabinet.cabinet_name if cabinet else ""


def _event(order, action, from_state, to_state, cabinet, comment="", reason_code="", payload=None):
    return OrderEvent.objects.create(
        order=order, action=action, from_state=from_state, to_state=to_state,
        actor_user=cabinet.user if cabinet else None, actor_membership=cabinet,
        actor_label=_label(cabinet), comment=comment or "", reason_code=reason_code or "", payload=payload or {},
    )


def _lock(order: Order) -> Order:
    """Qator qulfi (parallel o'tishlar) — chaqiruvchi obyektini oxirida _sync yangilaydi."""
    return Order.objects.select_for_update().get(pk=order.pk)


def _sync(target: Order, source: Order) -> Order:
    """Qulflangan nusxadagi o'zgarishlarni chaqiruvchi obyektga ko'chiradi."""
    for field in Order._meta.concrete_fields:
        setattr(target, field.attname, getattr(source, field.attname))
    return target


def _close_open_segment(order, on, reason):
    ReviewSegment.objects.filter(order=order, ended_on__isnull=True).update(ended_on=on, ended_reason=reason)


# ----------------------------------------------------------------------------- submit
@transaction.atomic
def submit(order: Order, cabinet, document_version):
    """Imzolangan buyurtmanoma bilan uyushmaga yuborish (TZ §6.1-3)."""
    caller, order = order, _lock(order)
    if not _is_mahalla_for(order, cabinet):
        raise _forbidden()
    if not cabinet.can_sign:
        raise _forbidden("Бу кабинетда имзолаш ҳуқуқи йўқ", code="cannot_sign")
    if order.state not in (OrderState.DRAFT, OrderState.RETURNED):
        raise TransitionError("Буюртма бу ҳолатда юборилмайди")
    route = union_route(order.mahalla)
    if route is None:
        raise TransitionError("Уюшма бўлинмаси бириктирилмаган — администраторга мурожаат қилинг", code="union_not_routed", status=422)
    now = timezone.now()
    today = local_date(now)
    from_state = order.state
    if not order.number:
        order.number = next_order_number(today)
    if order.first_submitted_at is None:
        order.first_submitted_at = now
    else:
        # Qayta yuborish: raqam o'zgarmaydi, versiya oshadi, eski versiya «almashtirilgan» (TZ §6.3-9)
        OrderVersion.objects.filter(order=order, superseded_at__isnull=True).update(superseded_at=now)
        order.version_no += 1
    order.union_unit = route.union_unit
    order.last_submitted_at = now
    order.state = OrderState.UNION_NEW
    version = OrderVersion.objects.create(
        order=order, version_no=order.version_no, snapshot=build_snapshot(order, cabinet),
        document_version=document_version, submitted_at=now, submitted_by=cabinet.user,
    )
    order.current_version = version
    order.save()
    ReviewSegment.objects.create(order=order, started_on=today)
    _event(order, "submit", from_state, order.state, cabinet, payload={"version_no": order.version_no, "number": order.number})
    title = f"Янги буюртма {order.number}" if from_state == OrderState.DRAFT else f"Қайта юборилган буюртма {order.number} (v{order.version_no})"
    notif.notify_union(order, kind=K.ORDER_NEW_UNION, title=title, body=order.title)
    return _sync(caller, order)


# ----------------------------------------------------------------------------- review
@transaction.atomic
def start_review(order: Order, cabinet):
    caller, order = order, _lock(order)
    if order.state == OrderState.UNION_NEW and _is_union_for(order, cabinet):
        to_state = OrderState.UNION_REVIEW
    elif order.state == OrderState.SUPPLIER_NEW and _is_supplier_for(order, cabinet):
        to_state = OrderState.SUPPLIER_REVIEW
    elif order.state in (OrderState.UNION_REVIEW, OrderState.SUPPLIER_REVIEW):
        raise TransitionError("Кўриб чиқиш аллақачон бошланган")
    elif _is_union_for(order, cabinet) or _is_supplier_for(order, cabinet):
        raise TransitionError("Буюртма бу ҳолатда кўриб чиқилмайди")
    else:
        raise _forbidden()
    from_state = order.state
    order.state = to_state
    order.save(update_fields=["state", "updated_at"])
    _event(order, "review", from_state, to_state, cabinet)
    return _sync(caller, order)


@transaction.atomic
def forward(order: Order, cabinet):
    caller, order = order, _lock(order)
    if not _is_union_for(order, cabinet):
        raise _forbidden()
    if order.state != OrderState.UNION_REVIEW:
        raise TransitionError("Аввал «Кўриб чиқишни бошлаш» босилиши керак")
    from_state = order.state
    order.state = OrderState.SUPPLIER_NEW
    order.save(update_fields=["state", "updated_at"])
    _event(order, "forward", from_state, order.state, cabinet)
    notif.notify_supplier(order, kind=K.ORDER_FORWARDED, title=f"Янги буюртма {order.number}", body=order.title)
    return _sync(caller, order)


@transaction.atomic
def return_order(order: Order, cabinet, *, reason_code: str, comment: str, fields=None):
    caller, order = order, _lock(order)
    if order.state == OrderState.UNION_REVIEW and _is_union_for(order, cabinet):
        by = "union"
    elif order.state == OrderState.SUPPLIER_REVIEW and _is_supplier_for(order, cabinet):
        by = "supplier"
    elif _is_union_for(order, cabinet) or _is_supplier_for(order, cabinet):
        raise TransitionError("Буюртма бу ҳолатда қайтарилмайди")
    else:
        raise _forbidden()
    if not (comment or "").strip():
        raise TransitionError("Қайтариш изоҳи мажбурий", code="comment_required", field="comment", status=422)
    if not reason_code:
        raise TransitionError("Қайтариш сабаби мажбурий", code="reason_required", field="reason_code", status=422)
    today = local_date(timezone.now())
    from_state = order.state
    order.state = OrderState.RETURNED
    order.save(update_fields=["state", "updated_at"])
    _close_open_segment(order, today, f"returned_by_{by}")
    _event(order, "return", from_state, order.state, cabinet, comment=comment.strip(), reason_code=reason_code,
           payload={"fields": list(fields or []), "by": by, "version_no": order.version_no})
    title = f"Буюртма {order.number} тузатишга қайтарилди"
    notif.notify_mahalla(order, kind=K.ORDER_RETURNED, title=title, body=comment.strip())
    if by == "supplier":
        notif.notify_union(order, kind=K.ORDER_RETURNED, title=title + " (етказиб берувчи)", body=comment.strip())
    return _sync(caller, order)


@transaction.atomic
def accept(order: Order, cabinet, *, executor_name: str):
    """Ijroga qabul: holat + 10 ish kuni + ombor ajratish (bir tranzaksiya)."""
    caller, order = order, _lock(order)
    if not _is_supplier_for(order, cabinet):
        raise _forbidden()
    if not cabinet.can_prepare:
        raise _forbidden("Бу кабинетда ижрога қабул ҳуқуқи йўқ", code="cannot_prepare")
    if order.state != OrderState.SUPPLIER_REVIEW:
        raise TransitionError("Аввал «Кўриб чиқишни бошлаш» босилиши керак")
    if not (executor_name or "").strip():
        raise TransitionError("Масъул ижрочи кўрсатилиши керак", code="executor_required", field="executor_name", status=422)
    from apps.yashil.services import ledger

    now = timezone.now()
    today = local_date(now)
    from_state = order.state
    order.state = OrderState.EXECUTION
    order.accepted_at = now
    order.accepted_on = today
    order.delivery_due = delivery_deadline(today, calendar_from_db())
    order.executor_name = executor_name.strip()
    # Ombor ajratish shu tranzaksiyada (TZ §22.1): DM'da yetmasa LedgerError — hech narsa yozilmaydi.
    acceptance = ledger.allocate_for_acceptance(order, cabinet, accepted_on=today, delivery_due=order.delivery_due,
                                                executor_name=order.executor_name)
    order.save(update_fields=["state", "accepted_at", "accepted_on", "delivery_due", "executor_name", "updated_at"])
    _close_open_segment(order, today, "accepted")
    _event(order, "accept", from_state, order.state, cabinet,
           payload={"executor_name": order.executor_name, "delivery_due": order.delivery_due.isoformat(), "stock": acceptance.result})
    notif.notify_mahalla(order, kind=K.ORDER_ACCEPTED, title=f"Буюртма {order.number} ижрога қабул қилинди",
                         body=f"Етказиш муддати: {order.delivery_due:%d.%m.%Y}")
    notif.notify_union(order, kind=K.ORDER_ACCEPTED, title=f"Буюртма {order.number} ижрога қабул қилинди")
    return _sync(caller, order)


# ----------------------------------------------------------------------------- hisob-kitob
def review_due(order: Order):
    return review_deadline(order.review_segments_as_tuples_dates(), calendar_from_db())


def deadline_info(order: Order, today=None) -> dict:
    """Frontend uchun: muddat, sarflangan/qolgan kunlar, kechikish."""
    cal = calendar_from_db()
    today = today or local_date(timezone.now())
    segments = order.review_segments_as_tuples_dates()
    info = {"review_due": None, "review_used": None, "delivery_due": None, "late_workdays": 0, "stage": None}
    if order.state in (OrderState.UNION_NEW, OrderState.UNION_REVIEW, OrderState.SUPPLIER_NEW, OrderState.SUPPLIER_REVIEW):
        due = review_deadline(segments, cal)
        info.update(stage="review", review_due=due.isoformat() if due else None,
                    review_used=review_days_used(segments, today, cal, REVIEW_WORKDAYS),
                    late_workdays=overdue_workdays(due, today, cal) if due else 0)
    elif order.state == OrderState.EXECUTION and order.delivery_due:
        info.update(stage="delivery", delivery_due=order.delivery_due.isoformat(),
                    late_workdays=overdue_workdays(order.delivery_due, today, cal))
    return info


def allowed_actions(order: Order, cabinet) -> list[str]:
    if cabinet is None:
        return []
    s = order.state
    if _is_mahalla_for(order, cabinet):
        if s in (OrderState.DRAFT, OrderState.RETURNED):
            acts = ["edit"] if cabinet.can_prepare else []
            if cabinet.can_sign:
                acts.append("submit")
            return acts
        return []
    if _is_union_for(order, cabinet):
        if s == OrderState.UNION_NEW:
            return ["review"]
        if s == OrderState.UNION_REVIEW:
            return ["forward", "return"]
        return []
    if _is_supplier_for(order, cabinet):
        if s == OrderState.SUPPLIER_NEW:
            return ["review"]
        if s == OrderState.SUPPLIER_REVIEW:
            return (["accept"] if cabinet.can_prepare else []) + ["return"]
        return []
    return []
