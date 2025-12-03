from collections import defaultdict

from decimal import Decimal, InvalidOperation

from apps.reports.mapping_columns import SECOND_ORDERING_MAP
from apps.reports.services.get_two_numbers_in_percent import round_decimal


def calculate_svod_chorva(report, grouped=None):
    from apps.reports.models import ReportItemInner, StatementColumn, ReportItem

    if grouped is None:
        inners = ReportItemInner.objects.filter(
            report_item__report=report
        ).select_related("report_item__statement_column")

        grouped = defaultdict(list)
        for inner in inners:
            ordering = inner.report_item.statement_column.ordering
            raw_value = inner.value or "0"
            try:
                val = Decimal(str(raw_value).strip())
            except (TypeError, ValueError, InvalidOperation):
                val = Decimal(0)
            grouped[ordering].append(val)

    totals = {}
    for result_ordering, source_orderings in SECOND_ORDERING_MAP.items():
        total = sum(sum(grouped.get(src, [])) for src in source_orderings)
        totals[result_ordering] = total

        try:
            col = StatementColumn.objects.get(ordering=result_ordering, statement=report.statement)
        except StatementColumn.DoesNotExist:
            continue

        item, _ = ReportItem.objects.get_or_create(report=report, statement_column=col)
        ReportItemInner.objects.update_or_create(
            report_item=item,
            defaults={"value": str(total)}
        )
        grouped[result_ordering].append(total)

    # Farqi va % hisoblash
    val_7_1_2 = totals.get("7.1.2", Decimal(0))  # Reja
    val_7_1_4 = totals.get("7.1.4", Decimal(0))  # Mavjud

    farqi = val_7_1_2 - val_7_1_4
    foiz = round_decimal((val_7_1_4 / val_7_1_2 * 100), 1) if val_7_1_2 else Decimal(0)

    for ordering, value in [("7.1.5", farqi), ("7.1.6", foiz)]:
        try:
            col = StatementColumn.objects.get(ordering=ordering, statement=report.statement)
        except StatementColumn.DoesNotExist:
            continue
        item, _ = ReportItem.objects.get_or_create(report=report, statement_column=col)
        ReportItemInner.objects.update_or_create(
            report_item=item,
            defaults={"value": str(round_decimal(value, 1))}
        )
        grouped[ordering].append(value)

    # Tashkilot nomi
    try:
        org_col = StatementColumn.objects.get(ordering="7.1.1", statement=report.statement)
    except StatementColumn.DoesNotExist:
        org_col = None

    if org_col and report.organization and report.organization.name:
        item, _ = ReportItem.objects.get_or_create(report=report, statement_column=org_col)
        ReportItemInner.objects.update_or_create(
            report_item=item,
            defaults={"value": report.organization.name}
        )