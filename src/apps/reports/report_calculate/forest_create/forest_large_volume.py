from decimal import Decimal
from collections import defaultdict

from apps.reports.models import Report, ReportItem, ReportItemInner
from apps.reports.services.general_report import normalize


def calculate_large_volume(report: Report):
    columns = list(report.statement.columns.prefetch_related("children").all())

    # === Barcha kerakli ReportItem'lar va Inner'larni oldindan olish ===
    all_items = ReportItem.objects.filter(report=report).prefetch_related("inners", "statement_column")
    items_map = defaultdict(list)
    for item in all_items:
        items_map[item.statement_column_id].append(item)

    # === Amalda ustunlarini topamiz (lekin umumiy Amalda ustunini emas) ===
    amalda_columns = [
        col for col in columns
        if col.ordering and col.ordering.startswith("1.1.")
        and col.ordering.endswith(".2")
        and col.ordering != "1.1.2.2"
    ]

    # === Yig‘indi hisoblash ===
    total_amalda = Decimal(0)
    for col in amalda_columns:
        value = sum_items(items_map.get(col.id, []))
        total_amalda += normalize(value)

    # === Amalda umumiy (1.1.2.2) ===
    amalda_total_column = next((c for c in columns if c.ordering == "1.1.2.2"), None)
    if amalda_total_column:
        save_value(report, amalda_total_column, total_amalda)

    # === Reja (1.1.2.1) ===
    reja_column = next((c for c in columns if c.ordering == "1.1.2.1"), None)
    reja_value = normalize(sum_items(items_map.get(reja_column.id, []))) if reja_column else Decimal(0)

    # === % (1.1.2.3) ===
    foiz_column = next((c for c in columns if c.ordering == "1.1.2.3"), None)
    percent = (total_amalda / reja_value * 100) if reja_value else Decimal(0)
    if foiz_column:
        save_value(report, foiz_column, round(percent, 2))


def sum_items(items: list[ReportItem]) -> float:
    total = 0.0
    for item in items:
        for inner in item.inners.all():
            try:
                total += float(inner.value or 0)
            except (ValueError, TypeError):
                continue
    return total


def save_value(report: Report, column, value: Decimal):
    item, _ = ReportItem.objects.get_or_create(
        report=report,
        statement_column=column
    )

    inner = item.inners.first()
    if inner:
        inner.value = str(value)
        inner.save(update_fields=["value"])
    else:
        ReportItemInner.objects.create(report_item=item, value=str(value))
