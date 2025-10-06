from decimal import Decimal

from apps.reports.models import Report


def calculate_total_column(report: Report, target_ordering: str, source_orderings: list[str]):
    from apps.reports.models import StatementColumn, ReportItem, ReportItemInner

    try:
        target_column = StatementColumn.objects.get(ordering=target_ordering, statement=report.statement)
    except StatementColumn.DoesNotExist:
        return

    source_items = ReportItem.objects.filter(
        report=report,
        statement_column__ordering__in=source_orderings
    ).prefetch_related("inners")

    total = Decimal(0)
    for item in source_items:
        inner = item.inners.first()
        if inner:
            try:
                total += Decimal(inner.value or 0)
            except:
                pass

    # update or create
    report_item, _ = ReportItem.objects.get_or_create(
        report=report,
        statement_column=target_column
    )
    ReportItemInner.objects.update_or_create(
        report_item=report_item,
        defaults={"value": total}
    )
