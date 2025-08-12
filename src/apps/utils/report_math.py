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


def safe_float_convertible(val):
    try:
        float(val)
        return True
    except (ValueError, TypeError):
        return False