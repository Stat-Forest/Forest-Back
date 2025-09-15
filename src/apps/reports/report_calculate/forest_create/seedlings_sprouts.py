from decimal import Decimal
from apps.reports.models import Report, ReportItem, StatementColumn, ReportItemInner


def normalize(value):
    if value is None:
        return Decimal(0)
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal(0)


def sum_values_by_ordering(report: Report, ordering: str) -> float:
    try:
        column = StatementColumn.objects.get(ordering=ordering, statement=report.statement)
    except StatementColumn.DoesNotExist:
        return 0.0

    items = ReportItem.objects.filter(report=report, statement_column=column, plant=None).prefetch_related("inners")
    total = Decimal(0)
    for item in items:
        for inner in item.inners.all():
            try:
                total += Decimal(str(inner.value))
            except (TypeError, ValueError):
                continue
    return float(total)


def create_or_update_item(report, ordering: str, value: Decimal):
    try:
        column = StatementColumn.objects.get(ordering=ordering, statement=report.statement)
    except StatementColumn.DoesNotExist:
        print(f"StatementColumn with ordering '{ordering}' not found.")
        return

    item, _ = ReportItem.objects.get_or_create(
        report=report,
        statement_column=column,
        plant=None
    )

    inner, _ = ReportItemInner.objects.get_or_create(
        report_item=item,
        organization=None
    )
    inner.value = str(value)
    inner.save()


def calculate_seedlings(report: Report):
    v_1_1_3_1 = sum_values_by_ordering(report, "1.1.3.1")
    v_1_1_3_2 = sum_values_by_ordering(report, "1.1.3.2")
    v_1_1_3_3 = sum_values_by_ordering(report, "1.1.3.3")
    v_1_1_4 = v_1_1_3_1 + v_1_1_3_2 + v_1_1_3_3
    create_or_update_item(report, "1.1.4", v_1_1_4)

    v_1_1_5_1 = sum_values_by_ordering(report, "1.1.5.1")
    v_1_1_5_2 = sum_values_by_ordering(report, "1.1.5.2")
    v_1_1_5_3 = sum_values_by_ordering(report, "1.1.5.3")
    v_1_1_5_4 = sum_values_by_ordering(report, "1.1.5.4")
    v_1_1_5_5_3 = sum_values_by_ordering(report, "1.1.5.5.3")
    v_1_1_5_6_1 = sum_values_by_ordering(report, "1.1.5.6.1")
    v_1_1_5_7 = sum_values_by_ordering(report, "1.1.5.7")

    v_1_1_5_8 = (
        v_1_1_5_1 + v_1_1_5_2 + v_1_1_5_3 +
        v_1_1_5_4 + v_1_1_5_5_3 + v_1_1_5_6_1 + v_1_1_5_7
    )
    create_or_update_item(report, "1.1.5.8", v_1_1_5_8)

    v_1_1_2 = sum_values_by_ordering(report, "1.1.2")
    v_1_1_5_9 = v_1_1_2 + v_1_1_4 - v_1_1_5_8
    create_or_update_item(report, "1.1.5.9", v_1_1_5_9)
