"""
Hisobotlar ro'yxati uchun item/qiymatlarni yengil lug'atlar sifatida yuklash.

ORM prefetch (ReportItem + statement_column + parent + inners obyektlari) 200
hisobot x 120 ustun uchun ~100 000 model obyekti yaratib, 4-5 soniya olardi.
`values()` bilan faqat kerakli ustunlar lug'at sifatida keladi (~5x tez).

Natija: {report_id(str): [{"id", "statement_column_id", "inners": [{"id", "value"}, ...]}, ...]}
inners tartibi — (created_at, id): eksport qator raqamini shu tartibdan oladi.
"""
from collections import defaultdict

from django.db.models import CharField
from django.db.models.functions import Cast

from apps.reports.models import ReportItem, ReportItemInner


def load_report_items(report_ids) -> dict:
    report_ids = [rid for rid in report_ids if rid]
    if not report_ids:
        return {}
    # UUID'lar bazadan matn sifatida (CAST): 200 hisobot uchun ~120 000 uuid.UUID
    # obyekti yaratilmaydi (profil: 0.9 s dan 1.9 s).
    inners_by_item = defaultdict(list)
    for iid, item_id, value in (
        ReportItemInner.objects
        .filter(report_item__report_id__in=report_ids)
        .order_by("created_at", "id")
        .annotate(sid=Cast("id", CharField()), iid=Cast("report_item_id", CharField()))
        .values_list("sid", "iid", "value")
    ):
        inners_by_item[item_id].append({"id": iid, "value": value})

    by_report = defaultdict(list)
    for item_id, report_id, column_id in (
        ReportItem.objects
        .filter(report_id__in=report_ids)
        .order_by()
        .annotate(sid=Cast("id", CharField()), rid=Cast("report_id", CharField()),
                  cid=Cast("statement_column_id", CharField()))
        .values_list("sid", "rid", "cid")
    ):
        by_report[report_id].append({
            "id": item_id,
            "statement_column_id": column_id,
            "inners": inners_by_item.get(item_id, []),
        })
    return dict(by_report)


def items_from_prefetch(report) -> list:
    """Prefetch qilingan obyektlardan xuddi shu lug'at tuzilmasi (eksport, boshqa view'lar)."""
    result = []
    for item in report.report_items.all():
        inners = sorted(item.inners.all(), key=lambda i: (i.created_at, str(i.id)))
        result.append({
            "id": str(item.id),
            "statement_column_id": str(item.statement_column_id) if item.statement_column_id else None,
            "inners": [{"id": str(i.id), "value": i.value} for i in inners],
        })
    return result
