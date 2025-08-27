from decimal import Decimal
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


def normalize(value):
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return Decimal(0)


def get_statement_columns_map(report: Report) -> dict[str, StatementColumn]:
    return {
        col.ordering: col
        for col in StatementColumn.objects.filter(statement=report.statement)
    }


def sum_values(report, column_orderings: list[str]) -> Decimal:
    total = Decimal(0)
    inners = ReportItemInner.objects.filter(
        report_item__report=report,
        report_item__statement_column__ordering__in=column_orderings
    ).select_related("report_item__statement_column")

    for inner in inners:
        total += normalize(inner.value)

    return total


def calculate_beekeeping(report: Report):
    """
    Hisobotdagi barcha hisob-kitob ustunlarini bulk orqali yaratish.
    """
    column_map = get_statement_columns_map(report)

    # Yig‘iladigan natijalar
    calculations: list[tuple[str, Decimal]] = []

    # ========== Asalarichilik ilovasi ==========
    total_beekeeping = sum_values(report, ["5.1.6.2", "5.1.7.2"])
    calculations.append(("5.1.8.2", total_beekeeping))

    # ========== Parrandachilik ilovasi ==========
    hojalik_total = sum_values(report, ["4.1.8.2.1", "4.1.8.2.2", "4.1.8.2.3"])
    xususiy_total = sum_values(report, ["4.1.9.2.1", "4.1.9.2.2", "4.1.9.2.3"])
    total_parranda = hojalik_total + xususiy_total

    calculations.extend([
        ("4.1.8.1.2", hojalik_total),
        ("4.1.9.1.2", xususiy_total),
        ("4.1.10.1.2", total_parranda),
        ("4.1.10.2.1", sum_values(report, ["4.1.8.2.1", "4.1.9.2.1"])),
        ("4.1.10.2.2", sum_values(report, ["4.1.8.2.2", "4.1.9.2.2"])),
        ("4.1.10.2.3", sum_values(report, ["4.1.8.2.3", "4.1.9.2.3"])),
    ])

    # ========== Baliqchilik ilovasi ==========
    total_baliq_maydoni = sum_values(report, ["6.1.5", "6.1.7"])
    total_baliq_mahsulot = sum_values(report, ["6.1.6", "6.1.8"])

    calculations.extend([
        ("6.1.2", total_baliq_maydoni),
        ("6.1.3", total_baliq_mahsulot),
    ])

    # Yig‘ilgan qiymatlarni ReportItem va ReportItemInner orqali yaratamiz
    report_items = []
    report_item_inners = []

    for ordering, value in calculations:
        column = column_map.get(ordering)
        if not column:
            continue
        item = ReportItem(report=report, statement_column=column)
        report_items.append(item)

    # bulk_create: ReportItem
    ReportItem.objects.bulk_create(report_items)

    # bulk_create: ReportItemInner
    for item, (ordering, value) in zip(report_items, calculations):
        report_item_inners.append(
            ReportItemInner(report_item=item, value=str(value))
        )

    ReportItemInner.objects.bulk_create(report_item_inners)
