# information_analytical/views/build_value.py
from apps.reports.models import ReportItem


def build_report_value_map(report):
    if not report:
        return {}

    items = (
        ReportItem.objects
        .filter(report=report)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    value_map = {}

    for item in items:
        col = item.statement_column
        inners = list(item.inners.all())

        if not inners:
            value_map[col.ordering] = item.value
        else:
            # ✅ UUID ni string ga o'zgartirish
            value_map[col.ordering] = {
                str(inner.plant_id): inner.value  # UUID -> string
                for inner in inners
                if inner.plant_id
            }

    return value_map