from django.db.models import Sum
from apps.reports.models import ReportItem


def get_report_item_value(report_qs, col):
    qs = ReportItem.objects.filter(
        report__in=report_qs,
        statement_column__title=col["column_title"],
        statement_column__ordering=col["column_ordering"],
        statement_column__parent__title=col["parent_column_title"],
        statement_column__parent__ordering=col["parent_column_ordering"],
    )

    total = qs.aggregate(total=Sum("value"))["total"]

    try:
        return float(total)
    except (TypeError, ValueError):
        return 0
