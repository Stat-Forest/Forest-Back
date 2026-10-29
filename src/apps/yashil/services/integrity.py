"""
Ma'lumotlar yaxlitligi (TZ §13.2, §17.3, Q25, Q36).

`version_problems` — hujjat versiyasi mazmuni saqlangan hash'ga, imzolar esa shu hash'ga
mos kelishini tekshiradi (bazada mazmun o'zgartirilsa QR sahifasi «ҳақиқий» demaydi).
`collect` — tiklash sinovi va pilotdan oldin: sanoqlar, imzo va harakatlar barmoq izi,
yo'qolgan fayllar, ledger solishtiruvi. Ikki muhitdagi natijani solishtirib ma'lumot mosligi
tekshiriladi.
"""
import hashlib

from django.core.files.storage import default_storage
from django.db.models import Count, Sum
from django.utils import timezone

from apps.yashil.models.documents import canonical_hash


def _content_matches(version, signatures) -> bool:
    content = version.content or {}
    if canonical_hash(content) == version.content_hash:
        return True
    # Imzodan keyin faqat `date` to'ldiriladi (birinchi imzo kuni, documents.after_signature):
    # hash imzodan oldingi mazmunga tegishli, sana esa birinchi imzo sanasiga teng bo'lishi shart.
    if not content.get("date") or not signatures:
        return False
    first = min(s.signed_at for s in signatures)
    if timezone.localtime(first).strftime("%d.%m.%Y") != content["date"]:
        return False
    return canonical_hash({**content, "date": None}) == version.content_hash


def version_problems(version) -> list[str]:
    problems = []
    signatures = list(version.signatures.all())
    if not _content_matches(version, signatures):
        problems.append("content_hash")
    for sig in signatures:
        signed_hash = (sig.verify_result or {}).get("content_hash")
        if signed_hash and signed_hash != version.content_hash:
            problems.append(f"signature_hash:{sig.role}")
    return problems


def _digest(rows) -> str:
    h = hashlib.sha256()
    for row in rows:
        h.update("|".join("" if v is None else str(v) for v in row).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _missing_files(model, field: str, limit: int) -> tuple[int, list[str]]:
    missing, sample = 0, []
    qs = model.objects.exclude(**{field: ""}).exclude(**{f"{field}__isnull": True}).values_list("pk", field)
    for pk, name in qs.iterator(chunk_size=2000):
        if not default_storage.exists(name):
            missing += 1
            if len(sample) < limit:
                sample.append(f"{model.__name__}:{pk}:{name}")
    return missing, sample


def collect(*, check_files: bool = True, sample_limit: int = 20) -> dict:
    from apps.yashil.models import (
        Acceptance, Act, ActAttachment, CalendarDay, DocumentVersion, Mahalla, Order, OrderAttachment, OrderEvent,
        Signature, StockMovement, YashilMembership,
    )
    from apps.yashil.tasks import ERROR_KINDS, _collect_issues

    counts = {
        "mahallas": Mahalla.objects.count(),
        "memberships": YashilMembership.objects.count(),
        "calendar_days": CalendarDay.objects.count(),
        "orders": Order.objects.count(),
        "order_events": OrderEvent.objects.count(),
        "acts": Act.objects.count(),
        "document_versions": DocumentVersion.objects.count(),
        "signatures": Signature.objects.count(),
        "acceptances": Acceptance.objects.count(),
        "stock_movements": StockMovement.objects.count(),
        "order_attachments": OrderAttachment.objects.count(),
        "act_attachments": ActAttachment.objects.count(),
    }
    by_state = dict(Order.objects.values_list("state").annotate(n=Count("id")).values_list("state", "n"))
    qty_by_kind = {k: str(v) for k, v in StockMovement.objects.values_list("kind").annotate(s=Sum("qty")).values_list("kind", "s")}
    fingerprints = {
        "signatures": _digest(Signature.objects.order_by("id").values_list("id", "document_version_id", "role", "pkcs7")),
        "stock_movements": _digest(StockMovement.objects.order_by("id").values_list("id", "warehouse_id", "catalog_item_id", "kind", "qty", "status")),
        "document_hashes": _digest(DocumentVersion.objects.order_by("id").values_list("id", "content_hash", "status")),
        "orders": _digest(Order.objects.order_by("id").values_list("id", "number", "state", "version_no")),
    }
    tampered = []
    for v in DocumentVersion.objects.prefetch_related("signatures").iterator(chunk_size=500):
        problems = version_problems(v)
        if problems:
            tampered.append({"id": str(v.id), "problems": problems})
    files = {}
    if check_files:
        for model, field in ((DocumentVersion, "pdf_file"), (OrderAttachment, "file"), (ActAttachment, "file"),
                             (StockMovement, "file"), (YashilMembership, "authority_file"), (CalendarDay, "source_file")):
            if field not in {f.name for f in model._meta.get_fields()}:
                continue
            n, sample = _missing_files(model, field, sample_limit)
            files[f"{model.__name__}.{field}"] = {"missing": n, "sample": sample}
    issues = _collect_issues()
    ledger_errors = sorted(f"{kind}:{key}" for kind, key in issues if kind in ERROR_KINDS)
    ok = not tampered and not ledger_errors and not any(v["missing"] for v in files.values())
    return {
        "ok": ok,
        "counts": counts,
        "orders_by_state": by_state,
        "stock_qty_by_kind": qty_by_kind,
        "fingerprints": fingerprints,
        "tampered_versions": tampered[:sample_limit],
        "tampered_count": len(tampered),
        "missing_files": files,
        "ledger_errors": ledger_errors[:sample_limit],
        "ledger_error_count": len(ledger_errors),
        "negative_forest_items": sum(1 for kind, _ in issues if kind == "stock_negative"),
    }


def compare(expected: dict, actual: dict) -> list[str]:
    """Ikki `collect` natijasi farqi: sanoqlar, holatlar, ombor yig'indilari va barmoq izlari."""
    diff = []
    for group in ("counts", "orders_by_state", "stock_qty_by_kind", "fingerprints"):
        a, b = expected.get(group) or {}, actual.get(group) or {}
        for key in sorted(set(a) | set(b)):
            if a.get(key) != b.get(key):
                diff.append(f"{group}.{key}: {a.get(key, 0)} → {b.get(key, 0)}")
    return diff
