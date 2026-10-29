"""
Bekor qilish (TZ §9.3; javob Е4):

    cancel_before_acceptance(order, cabinet, reason)   mahalla, qoralama/qaytarilgan — omborsiz
    request_cancel(order, cabinet, lines, reason)      mahalla yoki yetkazib beruvchi, ijroda/qisman; ochiq akt bo'lmasin
    agree_cancel(req, cabinet)                         ikkinchi tomon kelishadi
    reject_cancel(req, cabinet, note)                  ikkinchi tomon yoki uyushma rad etadi
    approve_cancel(req, cabinet)                       uyushma: yetkazilmagan qismga `release`, holat, bekor hujjati
    cancel_actions(order, cabinet)                     frontend tugmalari
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.yashil.models import (
    DELIVERY_STATES,
    Act,
    CancelRequest,
    Document,
    DocumentVersion,
    Order,
    OrderLine,
    OrderState,
    YashilMembership,
    YashilNotification,
)
from apps.yashil.services import ledger
from apps.yashil.services import notifications as notif
from apps.yashil.services import transitions as tr
from apps.yashil.services.acts import accepted_by_line, remaining_by_line
from apps.yashil.services.documents import _new_version
from apps.yashil.services.transitions import TransitionError
from apps.yashil.services.units import UNIT_LABELS
from apps.yashil.services.workdays import local_date

T = YashilMembership.MemberType
K = YashilNotification.Kind
P = CancelRequest.Party
S = CancelRequest.Status
ZERO = Decimal("0")
PARTY_CYR = {P.MAHALLA: "Маҳалла", P.SUPPLIER: "Етказиб берувчи"}
RESULT_CYR = {"cancelled": "Буюртма бекор қилинган", "closed": "Қолган қисм бекор қилинди — буюртма бажарилган",
              "partial": "Қисман бекор қилинган — ижро давом этади"}


def _dec(value) -> str:
    return format(Decimal(value).normalize(), "f")


def _forbidden(message="Бу амал учун ваколат йўқ", code="forbidden"):
    return TransitionError(message, code=code, status=403)


def _party_of(order, cabinet):
    if cabinet is None:
        return None
    if cabinet.member_type == T.MAHALLA and order.mahalla_id == cabinet.mahalla_id:
        return P.MAHALLA
    if cabinet.member_type == T.SUPPLIER and order.supplier_org_id == cabinet.organization_id:
        return P.SUPPLIER
    return None


def _is_union(order, cabinet) -> bool:
    return cabinet is not None and cabinet.member_type == T.UNION and order.union_unit_id == cabinet.union_unit_id


def _other(party):
    return P.SUPPLIER if party == P.MAHALLA else P.MAHALLA


def open_request(order):
    return order.cancel_requests.filter(status__in=CancelRequest.OPEN_STATUSES).first()


def _notify_party(order, party, **kw):
    return notif.notify_mahalla(order, **kw) if party == P.MAHALLA else notif.notify_supplier(order, **kw)


# ----------------------------------------------------------------------------- qabulgacha
@transaction.atomic
def cancel_before_acceptance(order: Order, cabinet, *, reason: str = "") -> Order:
    caller, order = order, tr._lock(order)
    if _party_of(order, cabinet) != P.MAHALLA:
        raise _forbidden("Буюртмани фақат маҳалла кабинети бекор қилади")
    if not cabinet.can_prepare:
        raise _forbidden("Бу кабинетда буюртма тайёрлаш ҳуқуқи йўқ", code="cannot_prepare")
    if order.state not in (OrderState.DRAFT, OrderState.RETURNED):
        raise TransitionError("Бу ҳолатда буюртма фақат бекор қилиш сўрови орқали тўхтатилади")
    now = timezone.now()
    from_state = order.state
    order.state = OrderState.CANCELLED
    order.closed_at = now
    order.save(update_fields=["state", "closed_at", "updated_at"])
    tr._close_open_segment(order, local_date(now), "cancelled")
    tr._event(order, "cancel", from_state, order.state, cabinet, comment=(reason or "").strip())
    if order.first_submitted_at and order.union_unit_id:
        notif.notify_union(order, kind=K.CANCEL_APPROVED, title=f"Буюртма {order.number} маҳалла томонидан бекор қилинди", body=(reason or "").strip())
    return tr._sync(caller, order)


# ----------------------------------------------------------------------------- so'rov
def _validate_lines(order: Order, lines):
    remaining = remaining_by_line(order)
    order_lines = {l.id: l for l in order.lines.select_related("catalog_item")}
    if not lines:
        rows = [(l, remaining[l.id]) for l in order_lines.values() if remaining[l.id] > 0]
        if not rows:
            raise TransitionError("Бекор қилинадиган қолдиқ йўқ — барча сатрлар қабул қилинган")
        return rows, True
    rows, seen = [], set()
    for idx, raw in enumerate(lines):
        line = raw["order_line"]
        if not isinstance(line, OrderLine):
            line = order_lines.get(line)
        if line is None or line.order_id != order.id:
            raise TransitionError("Сатр бу буюртмага тегишли эмас", code="line_invalid", field="lines", status=422, index=idx)
        if line.id in seen:
            raise TransitionError("Сатр такрорланган", code="line_duplicate", field="lines", status=422, index=idx)
        seen.add(line.id)
        try:
            qty = Decimal(str(raw["qty"]))
        except Exception:
            raise TransitionError("Миқдор нотўғри", code="invalid_qty", field="lines", status=422, index=idx)
        if qty <= 0:
            raise TransitionError("Миқдор мусбат бўлиши керак", code="invalid_qty", field="lines", status=422, index=idx)
        if qty > remaining[line.id]:
            raise TransitionError(f"{line.catalog_item.name_cyr}: бекор қилиш учун қолган ҳажм {_dec(remaining[line.id])}",
                                  code="qty_exceeds_remaining", field="lines", status=422, index=idx)
        rows.append((line, qty))
    return rows, False


def _lines_json(rows):
    return [{"order_line_id": str(l.id), "code": l.catalog_item.code, "name_cyr": l.catalog_item.name_cyr,
             "unit": l.catalog_item.unit, "qty": _dec(q)} for l, q in rows]


@transaction.atomic
def request_cancel(order: Order, cabinet, *, lines, reason: str) -> CancelRequest:
    order = tr._lock(order)
    party = _party_of(order, cabinet)
    if party is None:
        raise _forbidden()
    if not cabinet.can_prepare:
        raise _forbidden("Бу кабинетда сўров юбориш ҳуқуқи йўқ", code="cannot_prepare")
    if order.state not in DELIVERY_STATES:
        raise TransitionError("Бекор қилиш сўрови фақат ижродаги буюртма учун")
    if order.acts.filter(status__in=Act.OPEN_STATUSES).exists():
        raise TransitionError("Очиқ далолатнома бор — аввал уни якунланг ёки бекор қилинг", code="act_in_progress")
    if open_request(order) is not None:
        raise TransitionError("Бу буюртма бўйича кўриб чиқилаётган бекор қилиш сўрови бор", code="cancel_pending")
    if not (reason or "").strip():
        raise TransitionError("Бекор қилиш сабаби мажбурий", code="reason_required", field="reason", status=422)
    rows, is_full = _validate_lines(order, lines)
    req = CancelRequest.objects.create(
        order=order, requested_by_party=party, requested_by_membership=cabinet, is_full=is_full,
        lines=_lines_json(rows), reason=reason.strip()[:4000], created_by=cabinet.user,
    )
    tr._event(order, "cancel_request", order.state, order.state, cabinet, comment=req.reason,
              payload={"cancel_request_id": str(req.id), "is_full": is_full, "lines": req.lines, "party": party})
    title = f"Буюртма {order.number}: бекор қилиш сўрови ({PARTY_CYR[party]})"
    _notify_party(order, _other(party), kind=K.CANCEL_REQUESTED, title=title, body=req.reason)
    notif.notify_union(order, kind=K.CANCEL_REQUESTED, title=title, body=req.reason)
    return req


def _lock_req(req) -> CancelRequest:
    return CancelRequest.objects.select_for_update().select_related("order").get(pk=req.pk)


def _sync(target, source):
    for field in type(target)._meta.concrete_fields:
        setattr(target, field.attname, getattr(source, field.attname))
    return target


@transaction.atomic
def agree_cancel(req: CancelRequest, cabinet) -> CancelRequest:
    caller, req = req, _lock_req(req)
    order = req.order
    if _party_of(order, cabinet) != _other(req.requested_by_party):
        raise _forbidden("Сўровни фақат иккинчи тараф келишади")
    if not cabinet.can_prepare:
        raise _forbidden("Бу кабинетда келишиш ҳуқуқи йўқ", code="cannot_prepare")
    if req.status != S.REQUESTED:
        raise TransitionError("Сўров бу ҳолатда келишилмайди")
    req.status = S.AGREED
    req.agreed_by = cabinet
    req.agreed_at = timezone.now()
    req.save(update_fields=["status", "agreed_by", "agreed_at", "updated_at"])
    tr._event(order, "cancel_agree", order.state, order.state, cabinet, payload={"cancel_request_id": str(req.id)})
    title = f"Буюртма {order.number}: бекор қилишга иккинчи тараф рози — уюшма тасдиғи кутилмоқда"
    notif.notify_union(order, kind=K.CANCEL_AGREED, title=title, body=req.reason)
    _notify_party(order, req.requested_by_party, kind=K.CANCEL_AGREED, title=title)
    return _sync(caller, req)


@transaction.atomic
def reject_cancel(req: CancelRequest, cabinet, *, note: str) -> CancelRequest:
    caller, req = req, _lock_req(req)
    order = req.order
    is_union = _is_union(order, cabinet)
    is_other = _party_of(order, cabinet) == _other(req.requested_by_party)
    if not (is_union or is_other):
        raise _forbidden()
    if req.status not in CancelRequest.OPEN_STATUSES or (is_other and not is_union and req.status != S.REQUESTED):
        raise TransitionError("Сўров бу ҳолатда рад этилмайди")
    if not (note or "").strip():
        raise TransitionError("Рад этиш сабаби мажбурий", code="note_required", field="note", status=422)
    req.status = S.REJECTED
    req.decision_note = note.strip()[:4000]
    now = timezone.now()
    if is_union:
        req.approved_by, req.approved_at = cabinet, now
    else:
        req.agreed_by, req.agreed_at = cabinet, now
    req.save(update_fields=["status", "decision_note", "approved_by", "approved_at", "agreed_by", "agreed_at", "updated_at"])
    tr._event(order, "cancel_reject", order.state, order.state, cabinet, comment=req.decision_note, payload={"cancel_request_id": str(req.id)})
    title = f"Буюртма {order.number}: бекор қилиш сўрови рад этилди"
    _notify_party(order, req.requested_by_party, kind=K.CANCEL_REJECTED, title=title, body=req.decision_note)
    if not is_union:
        notif.notify_union(order, kind=K.CANCEL_REJECTED, title=title, body=req.decision_note)
    return _sync(caller, req)


def _cancellation_document(order: Order, req: CancelRequest, rows_info, result: str, cabinet) -> Document:
    n = order.documents.filter(kind=Document.Kind.CANCELLATION).count() + 1
    document = Document.objects.create(order=order, kind=Document.Kind.CANCELLATION, number=f"{order.number}/B{n}")
    content = {
        "doc_type": "cancellation", "template_version": 1, "number": document.number, "order_number": order.number,
        "order_id": str(order.id), "version_no": 1, "date": local_date(timezone.now()).strftime("%d.%m.%Y"),
        "mahalla_name": order.mahalla.name, "supplier_name": order.supplier_org.name,
        "requested_by": f"{PARTY_CYR[req.requested_by_party]} — {req.requested_by_membership.cabinet_name}",
        "agreed_by": req.agreed_by.cabinet_name if req.agreed_by else "—",
        "approved_by": cabinet.cabinet_name, "reason": req.reason, "is_full": req.is_full,
        "lines": rows_info, "result": result, "result_cyr": RESULT_CYR[result],
    }
    version = _new_version(document, content, 1)
    # Tizim hujjati: elektron imzo talab qilinmaydi, hash bilan muhrlangan
    version.status = DocumentVersion.Status.SIGNED
    version.save(update_fields=["status", "updated_at"])
    return document


@transaction.atomic
def approve_cancel(req: CancelRequest, cabinet) -> CancelRequest:
    """Uyushma tasdig'i: yetkazilmagan qismga ajratish tiklanadi, holat o'zgaradi, bekor hujjati yaratiladi."""
    caller, req = req, _lock_req(req)
    order = tr._lock(req.order)
    if not _is_union(order, cabinet):
        raise _forbidden("Бекор қилишни фақат уюшма тасдиқлайди")
    if req.status != S.AGREED:
        raise TransitionError("Аввал иккинчи тараф келишиши керак")
    if order.acts.filter(status__in=Act.OPEN_STATUSES).exists():
        raise TransitionError("Очиқ далолатнома бор — бекор қилиш тасдиқланмайди", code="act_in_progress")
    accepted = accepted_by_line(order)
    remaining = remaining_by_line(order)
    lines = {l.id: l for l in order.lines.select_related("catalog_item")}
    wanted = {} if req.is_full else {row["order_line_id"]: Decimal(row["qty"]) for row in req.lines}
    rows_info, released = [], []
    for n, line in enumerate(lines.values(), start=1):
        rem = remaining[line.id]
        want = rem if req.is_full else min(wanted.get(str(line.id), ZERO), rem)
        cancel_qty = max(ZERO, want)
        if cancel_qty > 0:
            mv = ledger.release_for_cancel(line, cancel_qty, cabinet=cabinet, note=f"Буюртма {order.number} бекор қилинди ({req.reason[:60]})")
            released.append({"order_line_id": str(line.id), "qty": _dec(cancel_qty), "movement_id": str(mv.id) if mv else None})
            if not req.is_full:
                line.qty = line.qty - cancel_qty
                line.save(update_fields=["qty", "updated_at"])
        rows_info.append({"n": n, "order_line_id": str(line.id), "code": line.catalog_item.code, "name": line.catalog_item.name_cyr,
                          "unit": UNIT_LABELS.get(line.catalog_item.unit, (line.catalog_item.unit,))[0],
                          "ordered_qty": _dec(line.qty + (cancel_qty if not req.is_full else ZERO)), "accepted_qty": _dec(accepted[line.id]),
                          "cancelled_qty": _dec(cancel_qty)})
    now = timezone.now()
    from_state = order.state
    if req.is_full:
        order.state = OrderState.CANCELLED
        order.closed_at = now
        result = "cancelled"
    elif all(accepted[l.id] >= l.qty for l in lines.values()):
        order.state = OrderState.CLOSED
        order.closed_at = now
        result = "closed"
    else:
        result = "partial"
    order.save(update_fields=["state", "closed_at", "updated_at"])
    document = _cancellation_document(order, req, rows_info, result, cabinet)
    req.status = S.APPROVED
    req.approved_by = cabinet
    req.approved_at = now
    req.document = document
    req.result = {"result": result, "released": released, "lines": rows_info}
    req.save(update_fields=["status", "approved_by", "approved_at", "document", "result", "updated_at"])
    tr._event(order, "cancel_approve", from_state, order.state, cabinet,
              payload={"cancel_request_id": str(req.id), "document_number": document.number, "result": result, "released": released})
    title = f"Буюртма {order.number}: бекор қилиш уюшма томонидан тасдиқланди ({RESULT_CYR[result]})"
    notif.notify_mahalla(order, kind=K.CANCEL_APPROVED, title=title, body=req.reason)
    notif.notify_supplier(order, kind=K.CANCEL_APPROVED, title=title, body=req.reason)
    req.order = order
    return _sync(caller, req)


# ----------------------------------------------------------------------------- frontend
def cancel_actions(order: Order, cabinet) -> list[str]:
    if cabinet is None:
        return []
    party = _party_of(order, cabinet)
    req = open_request(order)
    if party is not None:
        if order.state in (OrderState.DRAFT, OrderState.RETURNED) and party == P.MAHALLA and cabinet.can_prepare:
            return ["cancel"]
        if order.state not in DELIVERY_STATES or not cabinet.can_prepare:
            return []
        if req is not None:
            if req.status == S.REQUESTED and req.requested_by_party != party:
                return ["cancel_agree", "cancel_reject"]
            return []
        if order.acts.filter(status__in=Act.OPEN_STATUSES).exists():
            return []
        return ["cancel_request"]
    if _is_union(order, cabinet) and req is not None and req.status == S.AGREED:
        return ["cancel_approve", "cancel_reject"]
    return []
