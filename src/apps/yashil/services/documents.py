"""
Hujjatlar (TZ §11, §12, §13.2): buyurtmanoma va dalolatnoma — serverda tasdiqlangan
shablondan to'ldiriladi, o'zgarmas `content` + `html`, hash va QR identifikatori.

Imzo talablari: buyurtmanoma — mahalla; dalolatnoma — yetkazib beruvchi, so'ng mahalla
(ikkala imzo bitta versiyaga). Hamma talab qilingan imzo bo'lsa `signed`, aks holda
`partly_signed`. PDF `services/pdf.py` da; imzodan keyin qayta yaratiladi.
"""
from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.yashil.models import Document, DocumentVersion, Order, Signature, YashilMembership
from apps.yashil.services.snapshot import build_snapshot
from apps.yashil.services.units import UNIT_LABELS
from apps.yashil.services.workdays import local_date

ORDER_FORM_TEMPLATE_VERSION = 1
ACT_TEMPLATE_VERSION = 1
PUBLIC_VERIFY_PATH = "/yashil/verify/"
REQUIRED_ROLES = {
    Document.Kind.ORDER_FORM: {Signature.Role.MAHALLA},
    Document.Kind.ACT: {Signature.Role.SUPPLIER, Signature.Role.MAHALLA},
    Document.Kind.CANCELLATION: set(),
}
ROLE_LABELS_CYR = {Signature.Role.MAHALLA: "Маҳалла", Signature.Role.SUPPLIER: "Етказиб берувчи"}


def verify_url(token: str) -> str:
    base = getattr(settings, "YASHIL_PUBLIC_BASE_URL", "https://stat-urmon.uz").rstrip("/")
    return f"{base}{PUBLIC_VERIFY_PATH}{token}"


def _subject_phrase(lines) -> str:
    kinds = {l["item_type"] for l in lines}
    if kinds == {"service"}:
        return "хизматларни кўрсатиш"
    if kinds == {"goods"}:
        return "маҳсулотларни етказиб бериш"
    return "маҳсулотларни етказиб бериш ва хизматларни кўрсатиш"


def _person(membership) -> dict:
    if membership is None:
        return {"user_id": None, "full_name": "", "position": "", "phone": "", "authority": ""}
    u = membership.user
    return {
        "user_id": str(u.id), "full_name": f"{u.last_name} {u.first_name} {u.father_name}".strip(),
        "position": membership.position_title, "phone": membership.phone,
        "authority": f"{membership.authority_doc_number} {membership.authority_doc_date or ''}".strip(),
    }


def _mahalla_signer(order: Order):
    T = YashilMembership.MemberType
    return (YashilMembership.objects.filter(member_type=T.MAHALLA, mahalla_id=order.mahalla_id, can_sign=True, is_active=True)
            .select_related("user").order_by("-created_at").first())


# ----------------------------------------------------------------------------- buyurtmanoma
def order_form_content(order: Order, membership) -> dict:
    s = build_snapshot(order, membership)
    lines = [{
        "n": l["n"], "name": l["name_cyr"], "attrs": " · ".join(str(v) for v in (l["attributes"] or {}).values()) or l["attrs_note"],
        "qty": l["qty"], "unit": l["unit_cyr"], "item_type": l["item_type"], "code": l["code"],
    } for l in s["lines"]]
    attachments = s["attachments"]
    return {
        "doc_type": "order_form",
        "template_version": ORDER_FORM_TEMPLATE_VERSION,
        "order_id": s["order_id"],
        "number": s["number"],
        "version_no": s["version_no"],
        "date": None,  # imzolangan sana imzoda (TZ §11.2) — content imzogacha yaratiladi
        "supplier_name": s["supplier"]["name"],
        "supplier_stir": s["supplier"]["stir"],
        "route": s["route"],
        "mahalla_name": s["mahalla"]["name"],
        "mahalla_code": s["mahalla"]["source_code"],
        "region": s["mahalla"]["region"],
        "district": s["mahalla"]["district"],
        "full_address": f'{s["mahalla"]["region"]}, {s["mahalla"]["district"]}, {s["mahalla"]["name"]}, {s["address"]}',
        "title": s["title"],
        "object_type": s["object_type"]["name_cyr"] if s["object_type"] else None,
        "object_note": s["object_note"],
        "season": s["season"]["label_cyr"] if s["season"] else None,
        "point": f'{s["lat"]}, {s["lon"]}',
        "area_ha": s["area_ha"],
        "subject_phrase": _subject_phrase(s["lines"]),
        "lines": lines,
        "extra_info": " ".join(x for x in (s["extra_info"], s["water_source"] and f'Сув манбаи: {s["water_source"]}', s["problem_note"]) if x).strip(),
        "attachments_text": ", ".join(a["name"] for a in attachments) if attachments else "Йўқ",
        "attachments": attachments,
        "signer": s["signer"],
        "union_unit": s["union_unit"]["name"] if s["union_unit"] else None,
    }


def render_order_form_html(version: DocumentVersion) -> str:
    signature = version.signatures.filter(role=Signature.Role.MAHALLA, is_valid=True).first()
    return render_to_string("yashil/order_form.html", {
        "c": version.content, "version": version, "signed": signature is not None,
        "signature": signature, "verify_url": verify_url(version.qr_token),
    })


def _new_version(document: Document, content: dict, template_version: int) -> DocumentVersion:
    last = document.versions.order_by("-version_no").first()
    document.versions.filter(status=DocumentVersion.Status.UNSIGNED).update(status=DocumentVersion.Status.SUPERSEDED)
    version = DocumentVersion(document=document, version_no=(last.version_no + 1) if last else 1,
                              template_version=template_version, content=content)
    version.save()
    version.html = render_html(version)
    version.save(update_fields=["html"])
    document.current_version = version
    document.save(update_fields=["number", "current_version", "updated_at"])
    return version


@transaction.atomic
def build_order_form(order: Order, membership) -> DocumentVersion:
    """Yangi (imzolanmagan) hujjat versiyasi; avvalgi imzolanmagan versiya «almashtirilgan» bo'ladi."""
    document, _ = Document.objects.get_or_create(order=order, kind=Document.Kind.ORDER_FORM, defaults={"number": order.number or ""})
    if order.number and document.number != order.number:
        document.number = order.number
    return _new_version(document, order_form_content(order, membership), ORDER_FORM_TEMPLATE_VERSION)


# ----------------------------------------------------------------------------- dalolatnoma
def _order_form_date(order: Order) -> str:
    doc = order.documents.filter(kind=Document.Kind.ORDER_FORM).select_related("current_version").first()
    if doc and doc.current_version and doc.current_version.content.get("date"):
        return doc.current_version.content["date"]
    if order.first_submitted_at:
        return local_date(order.first_submitted_at).strftime("%d.%m.%Y")
    return "—"


def act_content(act_version, supplier_membership) -> dict:
    """TZ §12.1 maydonlari; `date` — yetkazib beruvchi imzolagan sana (imzoda to'ldiriladi)."""
    act = act_version.act
    order = act.order
    s = build_snapshot(order)
    lines = []
    for idx, l in enumerate(act_version.lines.select_related("order_line__catalog_item").order_by("order_line__position", "created_at"), start=1):
        item = l.order_line.catalog_item
        lines.append({
            "n": idx, "order_line_id": str(l.order_line_id), "code": item.code, "name": item.name_cyr,
            "attrs": " · ".join(str(v) for v in (item.attributes or {}).values()) or l.order_line.attrs_note,
            "qty": format(l.qty.normalize(), "f"), "unit": UNIT_LABELS.get(item.unit, (item.unit,))[0],
            "ordered_qty": format(l.order_line.qty.normalize(), "f"), "item_type": item.item_type,
        })
    attachments = [{"id": str(a.id), "name": a.original_name, "size": a.size, "kind": a.kind}
                   for a in act.attachments.filter(version_no=act.version_no)]
    object_text = f'{s["address"]}, {s["lat"]}, {s["lon"]} нуқтаси, {s["area_ha"]} гектар'
    return {
        "doc_type": "act",
        "template_version": ACT_TEMPLATE_VERSION,
        "act_id": str(act.id),
        "order_id": str(order.id),
        "number": act.number,
        "act_index": act.index,
        "version_no": act_version.version_no,
        "date": None,
        "is_partial": act.is_partial,
        "place": f'{s["mahalla"]["region"]}, {s["mahalla"]["district"]}, {s["mahalla"]["name"]}, {s["address"]}',
        "order_number": order.number,
        "order_date": _order_form_date(order),
        "supplier_name": s["supplier"]["name"],
        "supplier_stir": s["supplier"]["stir"],
        "mahalla_name": s["mahalla"]["name"],
        "region": s["mahalla"]["region"],
        "district": s["mahalla"]["district"],
        "object_text": object_text,
        "lines": lines,
        "delivery_date": act_version.delivery_date.strftime("%d.%m.%Y"),
        "planned_date": act_version.planned_date.strftime("%d.%m.%Y") if act_version.planned_date else None,
        "responsible": act_version.responsible,
        "delivery_address": act_version.delivery_address or s["address"],
        "note": act_version.note,
        "attachments_text": ", ".join(a["name"] for a in attachments) if attachments else "Йўқ",
        "attachments": attachments,
        "deliverer": {"name": s["supplier"]["name"], **_person(supplier_membership)},
        "receiver": {"name": s["mahalla"]["name"], **_person(_mahalla_signer(order))},
    }


def render_act_html(version: DocumentVersion) -> str:
    sigs = {s.role: s for s in version.signatures.filter(is_valid=True)}
    return render_to_string("yashil/act.html", {
        "c": version.content, "version": version, "supplier_sig": sigs.get(Signature.Role.SUPPLIER),
        "mahalla_sig": sigs.get(Signature.Role.MAHALLA), "fully_signed": version.status == DocumentVersion.Status.SIGNED,
        "verify_url": verify_url(version.qr_token),
    })


@transaction.atomic
def build_act_document(act, membership) -> DocumentVersion:
    """Aktning joriy versiyasi uchun hujjat versiyasi (imzolanmagan); eski imzolanmaganlar «almashtirilgan»."""
    document = act.document
    if document is None:
        document = Document.objects.create(order=act.order, kind=Document.Kind.ACT, number=act.number)
        act.document = document
        act.save(update_fields=["document", "updated_at"])
    version = _new_version(document, act_content(act.current_version, membership), ACT_TEMPLATE_VERSION)
    act.current_version.document_version = version
    act.current_version.save(update_fields=["document_version", "updated_at"])
    return version


# ----------------------------------------------------------------------------- umumiy
def render_html(version: DocumentVersion) -> str:
    if version.document.kind == Document.Kind.ACT:
        return render_act_html(version)
    if version.document.kind == Document.Kind.CANCELLATION:
        return render_to_string("yashil/cancellation.html", {"c": version.content, "version": version, "verify_url": verify_url(version.qr_token)})
    return render_order_form_html(version)


def signed_roles(version: DocumentVersion) -> set:
    return set(version.signatures.filter(is_valid=True).values_list("role", flat=True))


def missing_roles(version: DocumentVersion) -> list[str]:
    required = REQUIRED_ROLES.get(version.document.kind, set())
    order = [Signature.Role.SUPPLIER, Signature.Role.MAHALLA]
    missing = required - signed_roles(version)
    return [str(r.value) for r in order if r in missing]


def after_signature(version: DocumentVersion) -> None:
    """Imzodan keyin: sana (birinchi imzoda), holat (signed / partly_signed), HTML; PDF qayta yaratiladi."""
    if not version.content.get("date"):
        version.content["date"] = local_date(timezone.now()).strftime("%d.%m.%Y")
    version.status = DocumentVersion.Status.PARTLY if missing_roles(version) else DocumentVersion.Status.SIGNED
    version.html = render_html(version)
    if version.pdf_file:
        version.pdf_file.delete(save=False)
        version.pdf_file = None
    version.save(update_fields=["status", "content", "html", "pdf_file", "updated_at"])


mark_signed = after_signature


def public_verify_payload(version: DocumentVersion) -> dict:
    """Ochiq QR sahifasi (TZ §13.2, javob Ж6): shaxsiy ma'lumot, manzil, koordinata yo'q."""
    c = version.content
    document = version.document
    current = document.current_version_id == version.id
    S = DocumentVersion.Status
    if version.status == S.SIGNED:
        status = "valid" if current else "superseded"
    elif version.status == S.PARTLY:
        status = "pending_signature" if current else "superseded"
    elif version.status == S.SUPERSEDED:
        status = "superseded"
    elif version.status == S.CANCELLED:
        status = "cancelled"
    else:
        status = "unsigned"
    return {
        "doc_type": document.kind,
        "number": c.get("number"),
        "version_no": version.version_no,
        "date": c.get("date"),
        "status": status,
        "is_current": current,
        "is_partial": c.get("is_partial"),
        "order_number": c.get("order_number") if document.kind != Document.Kind.ORDER_FORM else c.get("number"),
        "parties": {"mahalla": c.get("mahalla_name"), "supplier": c.get("supplier_name")},
        "signatures": [
            {"role": s.role, "signed_at": timezone.localtime(s.signed_at).isoformat(timespec="seconds"), "valid": s.is_valid}
            for s in version.signatures.all()
        ],
        "missing_roles": missing_roles(version),
        "checked_at": timezone.localtime(timezone.now()).isoformat(timespec="seconds"),
    }
