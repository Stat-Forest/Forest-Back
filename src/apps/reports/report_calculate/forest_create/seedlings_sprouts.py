from collections import defaultdict
from decimal import Decimal
from apps.reports.models import Report, ReportItem, StatementColumn, ReportItemInner
from apps.reports.report_calculate.forest_create.create_third_svod_seedlings import calculate_third_seedlings_svod


def normalize(value):
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def preload_report_data(report: Report):
    """
    Oldindan barcha kerakli ma'lumotlarni olish:
    - StatementColumn
    - ReportItem + ReportItemInner (prefetch bilan)
    """
    # Barcha columns ni cache
    columns = {
        col.ordering: col
        for col in StatementColumn.objects.filter(statement=report.statement)
    }

    # Barcha ReportItem + ichki plantlar
    report_items = list(
        ReportItem.objects.filter(report=report)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    # ordering bo‘yicha grouping
    items_by_ordering = defaultdict(list)
    for item in report_items:
        ordering = item.statement_column.ordering
        items_by_ordering[ordering].append(item)

    # mapping (statement_column_id → item)
    report_item_map = {item.statement_column_id: item for item in report_items}

    # ichki qiymatlar cache (report_item_id → {plant_id: value})
    inner_cache = {
        item.id: {inner.plant_id: normalize(inner.value) for inner in item.inners.all()}
        for item in report_items
    }

    return columns, items_by_ordering, report_item_map, inner_cache


def sum_items_by_plants(items: list[ReportItem]) -> dict:
    """
    Har bir plant_id uchun umumiy qiymatni hisoblaydi.
    """
    totals = defaultdict(Decimal)
    for item in items:
        for inner in item.inners.all():
            if inner.plant_id:
                totals[inner.plant_id] += normalize(inner.value)
    return totals


def create_plant_values(report, column, plant_totals, report_item_map, inner_cache, create_buffer, update_buffer):
    """
    Har bir column uchun:
    - ReportItem yaratadi (agar mavjud bo‘lmasa)
    - mavjud innerlarni yangilaydi yoki yaratadi
    ⚡ hech qanday delete yoki get_or_create ishlatilmaydi
    """
    item = report_item_map.get(column.id)
    if not item:
        item = ReportItem(report=report, statement_column=column)
        report_item_map[column.id] = item
        create_buffer["report_items"].append(item)
        inner_cache[item.id] = {}

    old_values = inner_cache.get(item.id, {})

    for plant_id, new_val in plant_totals.items():
        old_val = old_values.get(plant_id)
        if old_val is None:
            # yangi inner kerak
            create_buffer["inners"].append(
                ReportItemInner(report_item=item, plant_id=plant_id, value=new_val)
            )
        elif old_val != normalize(new_val):
            # mavjudini yangilash kerak
            update_buffer["inners"].append(
                ReportItemInner(id=None, report_item=item, plant_id=plant_id, value=new_val)
            )


def calculate_seedlings(report: Report):
    """
    ⚡ Minimal query bilan optimallashtirilgan “Ko‘chat” va “Nihol” hisob-kitobi.
    """
    columns, items_by_ordering, report_item_map, inner_cache = preload_report_data(report)
    create_buffer = {"report_items": [], "inners": []}
    update_buffer = {"inners": []}

    # === KO‘CHAT ===
    total_1_1_4 = sum_items_by_plants(items_by_ordering.get("1.1.3.1", []))
    for o in ["1.1.3.2", "1.1.3.3"]:
        for pid, v in sum_items_by_plants(items_by_ordering.get(o, [])).items():
            total_1_1_4[pid] += v
    if "1.1.4" in columns:
        create_plant_values(report, columns["1.1.4"], total_1_1_4, report_item_map, inner_cache, create_buffer, update_buffer)

    total_1_1_5_8 = defaultdict(Decimal)
    for o in ["1.1.5.1", "1.1.5.2", "1.1.5.3", "1.1.5.4", "1.1.5.5.3", "1.1.5.6.1", "1.1.5.7"]:
        for pid, v in sum_items_by_plants(items_by_ordering.get(o, [])).items():
            total_1_1_5_8[pid] += v
    if "1.1.5.8" in columns:
        create_plant_values(report, columns["1.1.5.8"], total_1_1_5_8, report_item_map, inner_cache, create_buffer, update_buffer)

    val_1_1_2 = sum_items_by_plants(items_by_ordering.get("1.1.2", []))
    total_1_1_5_9 = defaultdict(Decimal)
    for pid in set(val_1_1_2) | set(total_1_1_4) | set(total_1_1_5_8):
        total_1_1_5_9[pid] = val_1_1_2.get(pid, 0) + total_1_1_4.get(pid, 0) - total_1_1_5_8.get(pid, 0)
    if "1.1.5.9" in columns:
        create_plant_values(report, columns["1.1.5.9"], total_1_1_5_9, report_item_map, inner_cache, create_buffer, update_buffer)

    # === NIHOL ===
    total_2_1_4 = sum_items_by_plants(items_by_ordering.get("2.1.3.1", []))
    for o in ["2.1.3.2", "2.1.3.3"]:
        for pid, v in sum_items_by_plants(items_by_ordering.get(o, [])).items():
            total_2_1_4[pid] += v
    if "2.1.4" in columns:
        create_plant_values(report, columns["2.1.4"], total_2_1_4, report_item_map, inner_cache, create_buffer, update_buffer)

    total_2_1_5_8 = defaultdict(Decimal)
    for o in ["2.1.5.1", "2.1.5.2", "2.1.5.3", "2.1.5.4", "2.1.5.5.3", "2.1.5.6.1", "2.1.5.7"]:
        for pid, v in sum_items_by_plants(items_by_ordering.get(o, [])).items():
            total_2_1_5_8[pid] += v
    if "2.1.5.8" in columns:
        create_plant_values(report, columns["2.1.5.8"], total_2_1_5_8, report_item_map, inner_cache, create_buffer, update_buffer)

    val_2_1_2 = sum_items_by_plants(items_by_ordering.get("2.1.2", []))
    total_2_1_5_9 = defaultdict(Decimal)
    for pid in set(val_2_1_2) | set(total_2_1_4) | set(total_2_1_5_8):
        total_2_1_5_9[pid] = val_2_1_2.get(pid, 0) + total_2_1_4.get(pid, 0) - total_2_1_5_8.get(pid, 0)
    if "2.1.5.9" in columns:
        create_plant_values(report, columns["2.1.5.9"], total_2_1_5_9, report_item_map, inner_cache, create_buffer, update_buffer)

    # 🔻 Bulk yaratish / update qilish
    if create_buffer["report_items"]:
        ReportItem.objects.bulk_create(create_buffer["report_items"])
    if create_buffer["inners"]:
        ReportItemInner.objects.bulk_create(create_buffer["inners"])
    if update_buffer["inners"]:
        ReportItemInner.objects.bulk_update(update_buffer["inners"], ["value"])

    calculate_third_seedlings_svod(report)