"""
Dalolatnoma oqimi (TZ §10, §12, §22.2; javoblar Ж3–Ж5, Г5):

    create_act(order, cabinet, ...)        yetkazib beruvchi, buyurtma ijroda/qisman, bitta ochiq akt
    update_act(act, cabinet, ...)          qoralama — joyida; qaytarilgan — yangi versiya (raqam o'zgarmaydi)
    cancel_act(act, cabinet, comment)      qoralama/qaytarilgan aktni bekor qilish
    sign_task(act, cabinet, request)       imzolash topshirig'i: yetkazib beruvchi (qoralama, dalil shart) / mahalla (tasdiqda)
    sign(act, cabinet, pkcs7, nonce, ...)  imzo tekshiruvi; yetkazib beruvchi -> mahalla tasdig'iga; mahalla -> qabul
    return_act(act, cabinet, ...)          mahalla izoh bilan qaytaradi
    accepted_by_line(order)                qabul miqdori — faqat ikki imzoli joriy akt versiyalaridan
    allowed_act_actions(act, cabinet)
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.yashil.models import (
    DELIVERY_STATES,
    Act,
    ActLine,
    ActReturnReason,
    ActVersion,
    CancelRequest,
    DocumentVersion,
    Order,
    OrderLine,
    OrderState,
    Signature,
    YashilMembership,
    YashilNotification,
)
from apps.yashil.services import notifications as notif
from apps.yashil.services import transitions as tr
from apps.yashil.services.documents import build_act_document
from apps.yashil.services.signing import prepare_signing, verify_and_store
from apps.yashil.services.transitions import TransitionError
from apps.yashil.services.units import quantity_error
from apps.yashil.services.workdays import local_date

T = YashilMembership.MemberType
K = YashilNotification.Kind
ZERO = Decimal("0")


def _dec(value) -> str:
    return format(Decimal(value).normalize(), "f")


def _forbidden(message="Бу амал учун ваколат йўқ", code="forbidden"):
    return TransitionError(message, code=code, status=403)


def _is_supplier(order, cabinet) -> bool:
    return cabinet is not None and cabinet.member_type == T.SUPPLIER and order.supplier_org_id == cabinet.organization_id


def _is_mahalla(order, cabinet) -> bool:
    return cabinet is not None and cabinet.member_type == T.MAHALLA and order.mahalla_id == cabinet.mahalla_id


def _lock_act(act: Act) -> Act:
    return Act.objects.select_for_update().select_related("order").get(pk=act.pk)


def _sync(target, source):
    for field in type(target)._meta.concrete_fields:
        setattr(target, field.attname, getattr(source, field.attname))
    return target


# ----------------------------------------------------------------------------- hisob
def accepted_by_line(order: Order, exclude_act=None) -> dict:
    """Har buyurtma qatori uchun qabul qilingan miqdor (approved aktlarning joriy versiyalari)."""
    totals = {l.id: ZERO for l in order.lines.all()}
    qs = ActLine.objects.filter(order_line__order=order, act_version__act__status=Act.Status.APPROVED, act_version__superseded_at__isnull=True)
    if exclude_act is not None:
        qs = qs.exclude(act_version__act=exclude_act)
    for row in qs.values("order_line_id").annotate(s=Sum("qty")):
        totals[row["order_line_id"]] = row["s"] or ZERO
    return totals


def remaining_by_line(order: Order, exclude_act=None) -> dict:
    accepted = accepted_by_line(order, exclude_act)
    return {l.id: l.qty - accepted.get(l.id, ZERO) for l in order.lines.all()}


def open_act(order: Order):
    return order.acts.filter(status__in=Act.OPEN_STATUSES).first()


def _validate_lines(order: Order, lines, exclude_act=None) -> list[tuple[OrderLine, Decimal]]:
    if not lines:
        raise TransitionError("Камида битта сатр етказилган бўлиши керак", code="lines_required", field="lines", status=422)
    remaining = remaining_by_line(order, exclude_act)
    order_lines = {l.id: l for l in order.lines.select_related("catalog_item")}
    out, seen = [], set()
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
        err = quantity_error(qty, line.catalog_item.unit)
        if err:
            raise TransitionError(err, code="invalid_qty", field="lines", status=422, index=idx)
        if qty > remaining[line.id]:
            raise TransitionError(
                f"{line.catalog_item.name_cyr}: қолган ҳажм {_dec(remaining[line.id])} — ундан ошиб кетмайди",
                code="qty_exceeds_remaining", field="lines", status=422, index=idx,
            )
        out.append((line, qty))
    return out


def _check_delivery_date(order: Order, delivery_date):
    today = local_date(timezone.now())
    if delivery_date is None or delivery_date > today or (order.accepted_on and delivery_date < order.accepted_on):
        raise TransitionError("Ҳақиқий етказиш санаси келажакда ва ижрога қабул санасидан олдин бўлмайди",
                              code="delivery_date_invalid", field="delivery_date", status=422)


def _is_partial_after(order: Order, act: Act, validated) -> bool:
    remaining = remaining_by_line(order, exclude_act=act)
    for line, qty in validated:
        remaining[line.id] -= qty
    return any(v > 0 for v in remaining.values())


def _snapshot(validated) -> dict:
    return {"lines": [{
        "order_line_id": str(l.id), "code": l.catalog_item.code, "name_cyr": l.catalog_item.name_cyr,
        "name_lat": l.catalog_item.name_lat, "unit": l.catalog_item.unit, "qty": _dec(q), "ordered_qty": _dec(l.qty),
    } for l, q in validated]}


def _fill_version(version: ActVersion, validated, **fields):
    for k, v in fields.items():
        setattr(version, k, v)
    version.snapshot = _snapshot(validated)
    version.save()
    version.lines.all().delete()
    ActLine.objects.bulk_create([ActLine(act_version=version, order_line=l, qty=q) for l, q in validated])


# ----------------------------------------------------------------------------- yaratish / tahrir
@transaction.atomic
def create_act(order: Order, cabinet, *, delivery_date, lines, responsible="", note="", planned_date=None, delivery_address="") -> Act:
    order = Order.objects.select_for_update().get(pk=order.pk)
    if not _is_supplier(order, cabinet):
        raise _forbidden()
    if not cabinet.can_prepare:
        raise _forbidden("Бу кабинетда далолатнома тайёрлаш ҳуқуқи йўқ", code="cannot_prepare")
    if order.state not in DELIVERY_STATES:
        raise TransitionError("Далолатнома фақат ижродаги буюртма учун тузилади")
    if open_act(order) is not None:
        raise TransitionError("Бу буюртма бўйича очиқ далолатнома бор — аввал уни якунланг ёки бекор қилинг", code="act_in_progress")
    if order.cancel_requests.filter(status__in=CancelRequest.OPEN_STATUSES).exists():
        raise TransitionError("Буюртмани бекор қилиш сўрови кўриб чиқилмоқда — далолатнома тузилмайди",
                              code="cancel_pending", status=409)
    _check_delivery_date(order, delivery_date)
    validated = _validate_lines(order, lines)
    index = (order.acts.count() or 0) + 1
    act = Act.objects.create(order=order, index=index, number=f"{order.number}/A{index}", created_by=cabinet.user)
    version = ActVersion(act=act, version_no=1, created_by_membership=cabinet, created_by=cabinet.user)
    _fill_version(version, validated, delivery_date=delivery_date, planned_date=planned_date,
                  responsible=(responsible or "")[:300], delivery_address=(delivery_address or "")[:500], note=(note or "")[:4000])
    act.current_version = version
    act.is_partial = _is_partial_after(order, act, validated)
    act.save(update_fields=["current_version", "is_partial", "updated_at"])
    tr._event(order, "act_create", order.state, order.state, cabinet,
              payload={"act_id": str(act.id), "act_number": act.number, "version_no": 1, "lines": version.snapshot["lines"]})
    return act


@transaction.atomic
def update_act(act: Act, cabinet, *, delivery_date, lines, responsible="", note="", planned_date=None, delivery_address="") -> Act:
    """Qoralama — joyida tahrir; qaytarilgan — yangi versiya (eski versiya va imzo tarixda, TZ §10.3)."""
    caller, act = act, _lock_act(act)
    order = act.order
    if not _is_supplier(order, cabinet):
        raise _forbidden()
    if not cabinet.can_prepare:
        raise _forbidden("Бу кабинетда далолатнома тайёрлаш ҳуқуқи йўқ", code="cannot_prepare")
    if act.status not in (Act.Status.DRAFT, Act.Status.RETURNED):
        raise TransitionError("Далолатнома бу ҳолатда таҳрирланмайди")
    _check_delivery_date(order, delivery_date)
    validated = _validate_lines(order, lines, exclude_act=act)
    now = timezone.now()
    fields = dict(delivery_date=delivery_date, planned_date=planned_date, responsible=(responsible or "")[:300],
                  delivery_address=(delivery_address or "")[:500], note=(note or "")[:4000])
    if act.status == Act.Status.DRAFT:
        version = act.current_version
        dv = version.document_version
        if dv is not None:
            if dv.status == DocumentVersion.Status.UNSIGNED:
                dv.status = DocumentVersion.Status.SUPERSEDED
                dv.save(update_fields=["status", "updated_at"])
            version.document_version = None
        _fill_version(version, validated, **fields)
        action = "act_edit"
    else:
        old = act.current_version
        old.superseded_at = now
        old.save(update_fields=["superseded_at", "updated_at"])
        if old.document_version_id:
            DocumentVersion.objects.filter(pk=old.document_version_id).update(status=DocumentVersion.Status.SUPERSEDED)
        act.version_no += 1
        version = ActVersion(act=act, version_no=act.version_no, created_by_membership=cabinet, created_by=cabinet.user)
        _fill_version(version, validated, **fields)
        act.current_version = version
        act.status = Act.Status.DRAFT
        action = "act_revise"
    act.is_partial = _is_partial_after(order, act, validated)
    act.save(update_fields=["current_version", "status", "version_no", "is_partial", "updated_at"])
    tr._event(order, action, order.state, order.state, cabinet,
              payload={"act_id": str(act.id), "act_number": act.number, "version_no": act.version_no, "lines": version.snapshot["lines"]})
    return _sync(caller, act)


@transaction.atomic
def cancel_act(act: Act, cabinet, *, comment="") -> Act:
    caller, act = act, _lock_act(act)
    if not _is_supplier(act.order, cabinet):
        raise _forbidden()
    if not cabinet.can_prepare:
        raise _forbidden("Бу кабинетда далолатнома тайёрлаш ҳуқуқи йўқ", code="cannot_prepare")
    if act.status not in (Act.Status.DRAFT, Act.Status.RETURNED):
        raise TransitionError("Фақат қоралама ёки қайтарилган далолатнома бекор қилинади")
    act.status = Act.Status.CANCELLED
    act.save(update_fields=["status", "updated_at"])
    if act.current_version and act.current_version.document_version_id:
        DocumentVersion.objects.filter(pk=act.current_version.document_version_id).update(status=DocumentVersion.Status.CANCELLED)
    tr._event(act.order, "act_cancel", act.order.state, act.order.state, cabinet, comment=comment or "",
              payload={"act_id": str(act.id), "act_number": act.number, "version_no": act.version_no})
    return _sync(caller, act)


# ----------------------------------------------------------------------------- imzo
def _role_for(act: Act, cabinet) -> str:
    order = act.order
    if _is_supplier(order, cabinet):
        if act.status != Act.Status.DRAFT:
            raise TransitionError("Далолатнома бу ҳолатда етказиб берувчи томонидан имзоланмайди")
        if not cabinet.can_sign:
            raise _forbidden("Бу кабинетда имзолаш ҳуқуқи йўқ", code="cannot_sign")
        return Signature.Role.SUPPLIER
    if _is_mahalla(order, cabinet):
        if act.status != Act.Status.REVIEW:
            raise _forbidden("Далолатнома ҳали маҳалла тасдиғига юборилмаган", code="state_conflict") if act.status == Act.Status.DRAFT \
                else TransitionError("Далолатнома бу ҳолатда қабул қилинмайди")
        if not cabinet.can_sign:
            raise _forbidden("Бу кабинетда имзолаш ҳуқуқи йўқ", code="cannot_sign")
        return Signature.Role.MAHALLA
    raise _forbidden()


def _current_version(act: Act) -> ActVersion:
    """Joriy akt versiyasi va hujjat versiyasi — bazadan yangi (chaqiruvchi obyekti eskirgan bo'lishi mumkin)."""
    return ActVersion.objects.select_related("document_version__document").get(pk=act.current_version_id)


def _document_version_for_signing(act: Act, cabinet, role: str) -> DocumentVersion:
    version = _current_version(act)
    if role == Signature.Role.SUPPLIER:
        if not act.attachments.filter(version_no=act.version_no).exists():
            raise TransitionError("Етказишни тасдиқловчи камида битта фото ёки PDF илова мажбурий",
                                  code="evidence_required", field="attachments", status=422)
        dv = version.document_version
        if dv is None or dv.status != DocumentVersion.Status.UNSIGNED:
            act.current_version = version
            dv = build_act_document(act, cabinet)
        return dv
    dv = version.document_version
    if dv is None or dv.status != DocumentVersion.Status.PARTLY:
        raise TransitionError("Етказиб берувчи имзолаган ҳужжат версияси топилмади", code="state_conflict")
    return dv


def sign_task(act: Act, cabinet, request) -> dict:
    act.refresh_from_db()
    role = _role_for(act, cabinet)
    with transaction.atomic():
        dv = _document_version_for_signing(act, cabinet, role)
    task = prepare_signing(dv, cabinet.user, cabinet, role, request)
    task.update(document_version_id=str(dv.id), role=role, content_hash=dv.content_hash)
    return task


@transaction.atomic
def sign(act: Act, cabinet, *, pkcs7: str, nonce: str, request, document_version_id=None) -> Act:
    caller, act = act, _lock_act(act)
    role = _role_for(act, cabinet)
    dv = _current_version(act).document_version
    if dv is None or (document_version_id and str(dv.id) != str(document_version_id)):
        raise TransitionError("Имзоланаётган ҳужжат версияси жорий эмас — саҳифани янгиланг", code="version_conflict")
    verify_and_store(dv, cabinet.user, cabinet, role, pkcs7, nonce, request)
    if role == Signature.Role.SUPPLIER:
        _after_supplier_sign(act, cabinet)
    else:
        _approve(act, cabinet)
    return _sync(caller, act)


def _after_supplier_sign(act: Act, cabinet):
    now = timezone.now()
    order = act.order
    act.status = Act.Status.REVIEW
    act.save(update_fields=["status", "updated_at"])
    ActVersion.objects.filter(pk=act.current_version_id).update(submitted_at=now)
    tr._event(order, "act_sign_supplier", order.state, order.state, cabinet,
              payload={"act_id": str(act.id), "act_number": act.number, "version_no": act.version_no})
    notif.notify_mahalla(order, kind=K.ACT_SENT, title=f"Далолатнома {act.number} тасдиқ учун юборилди",
                         body=f"Буюртма {order.number}: етказилган миқдорни текшириб имзоланг ёки изоҳ билан қайтаринг")


def _approve(act: Act, cabinet):
    """TZ §22.2: akt va buyurtma qulflanadi, qoldiq qayta tekshiriladi, qabul miqdori bir marta yoziladi, ombor o'zgarmaydi."""
    order = Order.objects.select_for_update().get(pk=act.order_id)
    now = timezone.now()
    remaining = remaining_by_line(order, exclude_act=act)
    for l in _current_version(act).lines.select_related("order_line__catalog_item"):
        if l.qty > remaining[l.order_line_id]:
            raise TransitionError(f"{l.order_line.catalog_item.name_cyr}: қабул миқдори буюртмадан ошади", code="qty_exceeds_remaining", status=422)
    act.status = Act.Status.APPROVED
    act.approved_at = now
    act.save(update_fields=["status", "approved_at", "updated_at"])
    accepted = accepted_by_line(order)
    complete = all(accepted[l.id] >= l.qty for l in order.lines.all())
    from_state = order.state
    order.state = OrderState.CLOSED if complete else OrderState.PARTIAL
    if complete:
        order.closed_at = now
    order.save(update_fields=["state", "closed_at", "updated_at"])
    tr._event(order, "act_approve", from_state, order.state, cabinet,
              payload={"act_id": str(act.id), "act_number": act.number, "version_no": act.version_no,
                       "accepted": {str(k): _dec(v) for k, v in accepted.items()}})
    title = f"Далолатнома {act.number} маҳалла томонидан қабул қилинди"
    body = "Буюртма тўлиқ бажарилди" if complete else "Буюртма қисман бажарилган — қолган ҳажм учун янги акт тузилади"
    notif.notify_supplier(order, kind=K.ACT_APPROVED, title=title, body=body)
    notif.notify_union(order, kind=K.ACT_APPROVED, title=title, body=body)
    act.order = order


@transaction.atomic
def return_act(act: Act, cabinet, *, reason_code: str, comment: str) -> Act:
    caller, act = act, _lock_act(act)
    order = act.order
    if not _is_mahalla(order, cabinet):
        raise _forbidden()
    if act.status != Act.Status.REVIEW:
        raise TransitionError("Фақат тасдиқдаги далолатнома қайтарилади")
    if not (comment or "").strip():
        raise TransitionError("Қайтариш изоҳи мажбурий", code="comment_required", field="comment", status=422)
    if reason_code not in ActReturnReason.values:
        raise TransitionError("Қайтариш сабаби мажбурий", code="reason_required", field="reason_code", status=422)
    act.status = Act.Status.RETURNED
    act.returned_at = timezone.now()
    act.save(update_fields=["status", "returned_at", "updated_at"])
    tr._event(order, "act_return", order.state, order.state, cabinet, comment=comment.strip(), reason_code=reason_code,
              payload={"act_id": str(act.id), "act_number": act.number, "version_no": act.version_no})
    notif.notify_supplier(order, kind=K.ACT_RETURNED, title=f"Далолатнома {act.number} тузатишга қайтарилди", body=comment.strip())
    return _sync(caller, act)


# ----------------------------------------------------------------------------- frontend
def allowed_act_actions(act: Act, cabinet) -> list[str]:
    if cabinet is None:
        return []
    order = act.order
    if _is_supplier(order, cabinet):
        if act.status == Act.Status.DRAFT:
            acts = ["edit", "attach"] if cabinet.can_prepare else []
            if cabinet.can_sign:
                acts.append("sign")
            if cabinet.can_prepare:
                acts.append("cancel")
            return acts
        if act.status == Act.Status.RETURNED:
            return ["edit", "attach", "cancel"] if cabinet.can_prepare else []
        return []
    if _is_mahalla(order, cabinet) and act.status == Act.Status.REVIEW:
        return (["approve"] if cabinet.can_sign else []) + ["return"]
    return []


def last_return_of(act: Act):
    ev = act.order.events.filter(action="act_return", payload__act_id=str(act.id)).order_by("-created_at").first()
    if ev is None:
        return None
    return {"comment": ev.comment, "reason_code": ev.reason_code, "at": ev.created_at.isoformat(timespec="seconds"),
            "actor": ev.actor_label, "version_no": ev.payload.get("version_no")}
