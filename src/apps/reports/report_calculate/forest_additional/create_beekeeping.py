from decimal import Decimal
from collections import defaultdict
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


def group_inners_by_ordering(report: Report) -> dict[str, list[ReportItemInner]]:
    inners = ReportItemInner.objects.filter(
        report_item__report=report
    ).select_related("report_item__statement_column")

    ordering_map = defaultdict(list)
    for inner in inners:
        ordering = inner.report_item.statement_column.ordering
        ordering_map[ordering].append(inner)

    return ordering_map


def sum_from_group(ordering_map: dict[str, list[ReportItemInner]], orderings: list[str]) -> Decimal:
    total = Decimal(0)
    for ordering in orderings:
        for inner in ordering_map.get(ordering, []):
            total += normalize(inner.value)
    return total


def calculate_beekeeping(report: Report):
    column_map = get_statement_columns_map(report)
    ordering_map = group_inners_by_ordering(report)

    calculations: list[tuple[str, Decimal]] = []

    # ========== Asalarichilik ==========
    total_beekeeping = sum_from_group(ordering_map, ["5.1.6.2", "5.1.7.2"])
    calculations.append(("5.1.8.2", total_beekeeping))

    # ========== Parrandachilik ==========
    hojalik_total = sum_from_group(ordering_map, ["4.1.8.2.1", "4.1.8.2.2", "4.1.8.2.3"])
    xususiy_total = sum_from_group(ordering_map, ["4.1.9.2.1", "4.1.9.2.2", "4.1.9.2.3"])
    total_parranda = hojalik_total + xususiy_total

    calculations.extend([
        ("4.1.8.1.2", hojalik_total),
        ("4.1.9.1.2", xususiy_total),
        ("4.1.10.1.2", total_parranda),
        ("4.1.10.2.1", sum_from_group(ordering_map, ["4.1.8.2.1", "4.1.9.2.1"])),
        ("4.1.10.2.2", sum_from_group(ordering_map, ["4.1.8.2.2", "4.1.9.2.2"])),
        ("4.1.10.2.3", sum_from_group(ordering_map, ["4.1.8.2.3", "4.1.9.2.3"])),
    ])

    # ========== Baliqchilik ==========
    total_baliq_maydoni = sum_from_group(ordering_map, ["6.1.5", "6.1.7"])
    total_baliq_mahsulot = sum_from_group(ordering_map, ["6.1.6", "6.1.8"])

    calculations.extend([
        ("6.1.2", total_baliq_maydoni),
        ("6.1.3", total_baliq_mahsulot),
    ])

    # Yaratish
    report_items = []
    report_item_inners = []

    for ordering, value in calculations:
        column = column_map.get(ordering)
        if not column:
            continue
        item = ReportItem(report=report, statement_column=column)
        report_items.append(item)

    ReportItem.objects.bulk_create(report_items)

    for item, (ordering, value) in zip(report_items, calculations):
        report_item_inners.append(
            ReportItemInner(report_item=item, value=str(value))
        )

    ReportItemInner.objects.bulk_create(report_item_inners)
