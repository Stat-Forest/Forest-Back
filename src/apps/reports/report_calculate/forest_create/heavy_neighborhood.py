from decimal import Decimal
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


def normalize(value):
    if value is None:
        return Decimal(0)
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal(0)


def sum_values(item):
    """
    Berilgan ReportItem ichidagi barcha ReportItemInner qiymatlarini yig‘adi.
    """
    if item is None:
        return Decimal(0)
    return sum([normalize(inner.value) for inner in item.inners.all()], Decimal(0))


def calculate_heavy_neighborhood(report: Report):
    """
    1.1.6 (%) = 1.1.5 (Amalda yetkazib berildi) / 1.1.4 (Yetkazib beriladigan ko‘chatlar soni) * 100
    """
    items = (
        report.report_items
        .filter(statement_column__ordering__in=[
            "1.1.4",  # Yetkazib beriladigan
            "1.1.5",  # Amalda yetkazildi
            "1.1.6",  # Foiz
        ])
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    items_by_ordering = {item.statement_column.ordering: item for item in items}

    yetkazilishi_item = items_by_ordering.get("1.1.4")
    amalga_oshgan_item = items_by_ordering.get("1.1.5")
    foiz_item = items_by_ordering.get("1.1.6")

    yetkazilishi_value = sum_values(yetkazilishi_item)
    amalga_oshgan_value = sum_values(amalga_oshgan_item)

    # === % (1.1.6) ===
    foiz_value = (
        (amalga_oshgan_value / yetkazilishi_value * 100)
        if yetkazilishi_value > 0 else Decimal(0)
    ).quantize(Decimal("1.00"))

    # === Create or Update 1.1.6 ===
    if foiz_item:
        foiz_item.inners.all().delete()
    else:
        column_foiz = StatementColumn.objects.get(
            statement=report.statement,
            ordering="1.1.6"
        )
        foiz_item = ReportItem.objects.create(
            report=report,
            statement_column=column_foiz
        )

    ReportItemInner.objects.create(
        report_item=foiz_item,
        value=foiz_value
    )
