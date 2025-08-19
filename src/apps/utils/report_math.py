from decimal import Decimal

from apps.reports.models import ReportItem, Report, StatementColumn, ReportItemInner


def sum_values(report: Report, columns: list[StatementColumn]) -> float:
    # Bog‘liq ReportItem'larni olib kelamiz
    report_item_ids = ReportItem.objects.filter(
        report=report, statement_column__in=columns
    ).values_list("id", flat=True)

    # Innerlar bo‘yicha qiymatlarni to‘playmiz (faqat float convert bo‘ladiganlarini)
    inners = ReportItemInner.objects.filter(report_item_id__in=report_item_ids)

    total = 0.0
    for inner in inners:
        try:
            total += float(inner.value)
        except (ValueError, TypeError):
            continue  # faqat son bo‘lgan qiymatlar yig‘iladi

    return total


def sum_values_analysis(report_items_by_column_id, column: StatementColumn) -> float:
    total = Decimal(0)
    items = report_items_by_column_id.get(column.id, [])

    for item in items:
        for inner in item.inners.all():
            try:
                total += Decimal(inner.value)
            except (ValueError, TypeError):
                continue

    return float(total)