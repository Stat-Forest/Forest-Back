"""
Buyurtmanoma hujjati (TZ §11): serverda tasdiqlangan shablondan to'ldiriladi,
o'zgarmas `content` + `html`, hash va QR identifikatori. PDF — 3-bosqich.
"""
from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.yashil.models import Document, DocumentVersion, Order, Signature
from apps.yashil.services.snapshot import build_snapshot
from apps.yashil.services.workdays import local_date

ORDER_FORM_TEMPLATE_VERSION = 1
PUBLIC_VERIFY_PATH = "/yashil/verify/"


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


@transaction.atomic
def build_order_form(order: Order, membership) -> DocumentVersion:
    """Yangi (imzolanmagan) hujjat versiyasi; avvalgi imzolanmagan versiya «almashtirilgan» bo'ladi."""
    document, _ = Document.objects.get_or_create(order=order, kind=Document.Kind.ORDER_FORM, defaults={"number": order.number or ""})
    if order.number and document.number != order.number:
        document.number = order.number
    last = document.versions.order_by("-version_no").first()
    document.versions.filter(status=DocumentVersion.Status.UNSIGNED).update(status=DocumentVersion.Status.SUPERSEDED)
    version = DocumentVersion(
        document=document, version_no=(last.version_no + 1) if last else 1,
        template_version=ORDER_FORM_TEMPLATE_VERSION, content=order_form_content(order, membership),
    )
    version.save()
    version.html = render_order_form_html(version)
    version.save(update_fields=["html"])
    document.current_version = version
    document.save(update_fields=["number", "current_version", "updated_at"])
    return version


def mark_signed(version: DocumentVersion) -> None:
    version.status = DocumentVersion.Status.SIGNED
    version.content["date"] = local_date(timezone.now()).strftime("%d.%m.%Y")
    version.html = render_order_form_html(version)
    version.save(update_fields=["status", "html", "updated_at"])


def public_verify_payload(version: DocumentVersion) -> dict:
    """Ochiq QR sahifasi (TZ §13.2, javob Ж6): shaxsiy ma'lumot, manzil, koordinata yo'q."""
    c = version.content
    document = version.document
    current = document.current_version_id == version.id
    if version.status == DocumentVersion.Status.SIGNED and current:
        status = "valid"
    elif version.status == DocumentVersion.Status.SIGNED and not current:
        status = "superseded"
    elif version.status == DocumentVersion.Status.SUPERSEDED:
        status = "superseded"
    elif version.status == DocumentVersion.Status.CANCELLED:
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
        "parties": {"mahalla": c.get("mahalla_name"), "supplier": c.get("supplier_name")},
        "signatures": [
            {"role": s.role, "signed_at": timezone.localtime(s.signed_at).isoformat(timespec="seconds"), "valid": s.is_valid}
            for s in version.signatures.all()
        ],
        "checked_at": timezone.localtime(timezone.now()).isoformat(timespec="seconds"),
    }
