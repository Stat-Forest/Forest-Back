# apps/information_analytical/services/report_values.py

from decimal import Decimal, InvalidOperation
from django.db.models import Prefetch
from apps.reports.models import Report, ReportItem, ReportItemInner


def to_decimal(v):
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def build_report_value_map_from_items(report_items):
    """
    report_items: ReportItem queryset yoki list
    returns: ordering -> value
    """
    value_map = {}
    for item in report_items:
        ordering = item.statement_column.ordering
        inners = list(getattr(item, "_prefetched_inners", None) or item.inners.all())

        if not inners:
            value_map[ordering] = item.value
        else:
            # ✅ UUID ni string ga o'zgartirish
            value_map[ordering] = {
                str(inner.plant_id): inner.value  # UUID -> string
                for inner in inners
                if inner.plant_id
            }
    return value_map


def fetch_latest_accepted_reports_map(*, org_ids, statement_ids):
    """
    returns:
      reports_map[(org_id, statement_id)] = Report instance (latest accepted)
    """
    qs = (
        Report.objects
        .filter(
            organization_id__in=org_ids,
            statement_id__in=statement_ids,
            status=Report.StatusChoices.ACCEPTED,
        )
        .order_by("organization_id", "statement_id", "-created_at")
        .distinct("organization_id", "statement_id")
        .select_related("organization", "statement")
    )

    # Report ID larni olish
    report_ids = qs.values_list('id', flat=True)

    # ReportItem va ReportItemInner ni prefetch qilish
    if report_ids:
        qs = qs.prefetch_related(
            Prefetch(
                "report_items",
                queryset=ReportItem.objects.filter(
                    report_id__in=report_ids
                ).select_related("statement_column").prefetch_related(
                    Prefetch(
                        "inners",
                        queryset=ReportItemInner.objects.all().only(
                            'id', 'report_item_id', 'plant_id', 'value'
                        ),
                        to_attr="_prefetched_inners"
                    )
                ).only(
                    'id', 'report_id', 'statement_column_id', 'value'
                ),
                to_attr="_prefetched_items"
            )
        )

    out = {}
    for r in qs:
        out[(r.organization_id, r.statement_id)] = r
    return out