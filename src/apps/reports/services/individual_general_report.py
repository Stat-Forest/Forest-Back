from collections import defaultdict
from decimal import Decimal

from apps.utils.services.is_that_number import is_number


def aggregate_individual_report(source_report):
    from apps.reports.models import Report, ReportItem, ReportItemInner

    # Avvaldan bor bo‘lsa o‘chirib tashlaymiz
    Report.objects.filter(
        organization=source_report.organization,
        statement=source_report.statement,
        deadline=source_report.deadline,
        is_individual_general=True
    ).delete()

    all_items = source_report.report_items.prefetch_related("inners")

    # Individual Jami reportni yaratamiz
    individual_report = Report.objects.create(
        organization=source_report.organization,
        statement=source_report.statement,
        deadline=source_report.deadline,
        status=Report.StatusChoices.SAVED,
        is_general=False,
        is_individual_general=True,
        region=source_report.region,
        republic=source_report.republic,
    )

    column_values_map = defaultdict(list)
    for item in all_items:
        for inner in item.inners.all():
            column_values_map[item.statement_column_id].append(inner.value)

    new_items = []
    new_inners = []

    for column_id, values in column_values_map.items():
        report_item = ReportItem(
            report=individual_report,
            statement_column_id=column_id
        )
        new_items.append(report_item)

        numeric_values = [Decimal(v) for v in values if is_number(v)]
        if numeric_values:
            total = sum(numeric_values)
            new_inners.append(
                ReportItemInner(report_item=report_item, value=str(total))
            )
        else:
            new_inners.append(
                ReportItemInner(report_item=report_item, value=values[0])
            )

    ReportItem.objects.bulk_create(new_items)
    ReportItemInner.objects.bulk_create(new_inners)

    return individual_report
