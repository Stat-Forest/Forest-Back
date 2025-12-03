from decimal import Decimal
from collections import defaultdict

from apps.reports.models import Report, ReportItem, ReportItemInner
from apps.reports.services.normalize_utils import normalize
from apps.reports.services.get_two_numbers_in_percent import round_decimal


def calculate_large_volume(report: Report):
    columns = list(
        report.statement.columns.prefetch_related("children").all()
    )

    # --- Barcha itemlar va innerlar oldindan olib qo‘yiladi ---
    all_items = ReportItem.objects.filter(report=report).prefetch_related("inners", "statement_column")
    items_map = defaultdict(list)
    item_by_column = {}

    for item in all_items:
        items_map[item.statement_column_id].append(item)
        item_by_column[item.statement_column_id] = item

    # === Amalda ustunlarini aniqlash: 1.1.X (3 dan 88 gacha) ===
    plant_columns = [
        col for col in columns
        if col.ordering and col.ordering.startswith("1.1.")
        and col.ordering.count(".") == 2
        and col.ordering != "1.1.2"
    ]

    total_amalda = Decimal(0)
    for col in plant_columns:
        total_amalda += normalize(sum_items(items_map.get(col.id, [])))

    # === Reja ===
    reja_column = next((c for c in columns if c.ordering == "1.1.2.1"), None)
    reja_value = normalize(sum_items(items_map.get(reja_column.id, []))) if reja_column else Decimal(0)

    # === % ===
    percent = (total_amalda / reja_value * 100) if reja_value else Decimal(0)
    percent = round_decimal(percent, places=1)  # 💡 Aynan bu yerda 1 kasr sonigacha yaxlitlanadi

    # === Saqlash ===
    updates = []

    for ordering, value in [
        ("1.1.2.2", total_amalda),     # Amalda
        ("1.1.2.3", percent),          # Foiz (yaxlitlangan)
    ]:
        column = next((c for c in columns if c.ordering == ordering), None)
        if column:
            item = item_by_column.get(column.id)
            if not item:
                item = ReportItem.objects.create(report=report, statement_column=column)
                item_by_column[column.id] = item

            if item.inners.exists():
                inner = item.inners.all()[0]
                inner.value = str(value)
                updates.append(inner)
            else:
                ReportItemInner.objects.create(report_item=item, value=str(value))

    # --- Bulk update qilish ---
    if updates:
        ReportItemInner.objects.bulk_update(updates, ["value"])


def sum_items(items: list[ReportItem]) -> float:
    total = 0.0
    for item in items:
        for inner in item.inners.all():
            try:
                total += float(inner.value or 0)
            except (ValueError, TypeError):
                continue
    return total
