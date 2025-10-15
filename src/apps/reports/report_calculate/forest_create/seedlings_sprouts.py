from uuid import UUID
from decimal import Decimal, InvalidOperation
from collections import defaultdict

from apps.reports.models import Report, ReportItem, StatementColumn, ReportItemInner
from apps.reports.report_calculate.forest_create.create_third_svod_seedlings import calculate_third_seedlings_svod


def normalize(value):
    try:
        if value is None or value == "":
            return Decimal("0")
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def preload_plant_values_by_ordering(report: Report) -> dict[str, dict[UUID, Decimal]]:
    """
    ordering → {plant_id → value} formatda barcha qiymatlarni return qiladi.
    """
    result = defaultdict(lambda: defaultdict(Decimal))

    inners = ReportItemInner.objects.filter(
        report_item__report=report
    ).select_related("report_item__statement_column")

    for inner in inners:
        ordering = inner.report_item.statement_column.ordering
        plant_id = inner.plant_id
        value = normalize(inner.value)
        if plant_id:
            result[ordering][plant_id] += value

    return result


def preload_statement_columns_and_items(report: Report):
    """
    Columnlar va mavjud ReportItem'larni yuklaydi.
    """
    columns = {
        col.ordering: col
        for col in StatementColumn.objects.filter(statement=report.statement)
    }

    report_items = list(
        ReportItem.objects.filter(report=report)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    report_item_map = {item.statement_column_id: item for item in report_items}

    inner_cache = {
        item.id: {inner.plant_id: normalize(inner.value) for inner in item.inners.all()}
        for item in report_items
    }

    return columns, report_item_map, inner_cache




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


def create_plant_values(
    report, column, plant_totals, report_item_map,
    inner_cache, create_buffer, update_buffer
):
    """
    Har bir column uchun:
    - ReportItem yaratadi (agar mavjud bo‘lmasa)
    - Har bir plant_id uchun yangi ReportItemInner yaratadi yoki yangilaydi
    ⚡ To‘liq plant-based ishlaydi (bir nechta o‘simlik uchun ham)
    ⚡ get_or_create ishlatmaydi, bulk_create/update uchun optimallashtirilgan
    """
    # 🔹 ReportItem topamiz yoki yaratamiz
    item = report_item_map.get(column.id)
    if not item:
        item = ReportItem(report=report, statement_column=column)
        report_item_map[column.id] = item
        create_buffer["report_items"].append(item)
        inner_cache[item.id] = {}

    # 🔹 Eski qiymatlar (plant_id → value)
    old_values = inner_cache.get(item.id, {}) or {}

    # 🔹 Har bir plant_id bo‘yicha tekshirish
    for plant_id, new_val in plant_totals.items():
        normalized_val = normalize(new_val)

        # Agar eski qiymat yo‘q — yangi qo‘shamiz
        if plant_id not in old_values:
            create_buffer["inners"].append(
                ReportItemInner(
                    report_item=item,
                    plant_id=plant_id,
                    value=normalized_val
                )
            )
            # inner_cache ni ham yangilaymiz
            old_values[plant_id] = normalized_val

        # Agar qiymat o‘zgargan bo‘lsa — update qilamiz
        elif old_values[plant_id] != normalized_val:
            update_buffer["inners"].append(
                ReportItemInner(
                    id=None,  # bulk_update uchun ID keyin ishlatiladi
                    report_item=item,
                    plant_id=plant_id,
                    value=normalized_val
                )
            )
            old_values[plant_id] = normalized_val

    # 🔹 inner_cache ni yangilab qo‘yamiz (keyingi hisoblarda ishlaydi)
    inner_cache[item.id] = old_values



def calculate_seedlings(report: Report):
    columns, report_item_map, inner_cache = preload_statement_columns_and_items(report)
    plant_values_map = preload_plant_values_by_ordering(report)

    create_buffer = {"report_items": [], "inners": []}
    update_buffer = {"inners": []}

    def accumulate(orderings: list[str]) -> dict:
        result = defaultdict(Decimal)
        for ordering in orderings:
            for pid, val in plant_values_map.get(ordering, {}).items():
                result[pid] += val
        return result

    # === KO‘CHAT ===
    total_1_1_4 = accumulate(["1.1.3.1", "1.1.3.2", "1.1.3.3"])
    if "1.1.4" in columns:
        create_plant_values(report, columns["1.1.4"], total_1_1_4,
                            report_item_map, inner_cache, create_buffer, update_buffer)

    total_1_1_5_8 = accumulate(["1.1.5.1", "1.1.5.2", "1.1.5.3", "1.1.5.4",
                                "1.1.5.5.3", "1.1.5.6.1", "1.1.5.7"])
    if "1.1.5.8" in columns:
        create_plant_values(report, columns["1.1.5.8"], total_1_1_5_8,
                            report_item_map, inner_cache, create_buffer, update_buffer)

    val_1_1_2 = plant_values_map.get("1.1.2", {})
    total_1_1_5_9 = defaultdict(Decimal)
    for pid in set(val_1_1_2) | set(total_1_1_4) | set(total_1_1_5_8):
        total_1_1_5_9[pid] = (
            val_1_1_2.get(pid, 0)
            + total_1_1_4.get(pid, 0)
            - total_1_1_5_8.get(pid, 0)
        )
    if "1.1.5.9" in columns:
        create_plant_values(report, columns["1.1.5.9"], total_1_1_5_9,
                            report_item_map, inner_cache, create_buffer, update_buffer)

    # === NIHOL ===
    total_2_1_4 = accumulate(["2.1.3.1", "2.1.3.2", "2.1.3.3"])
    if "2.1.4" in columns:
        create_plant_values(report, columns["2.1.4"], total_2_1_4,
                            report_item_map, inner_cache, create_buffer, update_buffer)

    total_2_1_5_8 = accumulate(["2.1.5.1", "2.1.5.2", "2.1.5.3", "2.1.5.4",
                                "2.1.5.5.3", "2.1.5.6.1", "2.1.5.7"])
    if "2.1.5.8" in columns:
        create_plant_values(report, columns["2.1.5.8"], total_2_1_5_8,
                            report_item_map, inner_cache, create_buffer, update_buffer)

    val_2_1_2 = plant_values_map.get("2.1.2", {})
    total_2_1_5_9 = defaultdict(Decimal)
    for pid in set(val_2_1_2) | set(total_2_1_4) | set(total_2_1_5_8):
        total_2_1_5_9[pid] = (
            val_2_1_2.get(pid, 0)
            + total_2_1_4.get(pid, 0)
            - total_2_1_5_8.get(pid, 0)
        )
    if "2.1.5.9" in columns:
        create_plant_values(report, columns["2.1.5.9"], total_2_1_5_9,
                            report_item_map, inner_cache, create_buffer, update_buffer)

    # === SAVE QILISH ===
    if create_buffer["report_items"]:
        ReportItem.objects.bulk_create(create_buffer["report_items"])
    if create_buffer["inners"]:
        ReportItemInner.objects.bulk_create(create_buffer["inners"])
    if update_buffer["inners"]:
        ReportItemInner.objects.bulk_update(update_buffer["inners"], ["value"])

    calculate_third_seedlings_svod(report)
