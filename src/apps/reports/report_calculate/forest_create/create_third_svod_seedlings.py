from decimal import Decimal, InvalidOperation
from collections import defaultdict

from apps.reports.mapping_columns import THIRD_ORDERING_MAP
from apps.reports.models import ReportItemInner, StatementColumn, ReportItem, Plant

def normalize_decimal(value):
    try:
        return Decimal(str(value).strip())
    except (TypeError, ValueError, InvalidOperation):
        return Decimal(0)


def calculate_third_seedlings_svod(report):
    """
    3-ilova SVOD: Ko‘chat-va-Nihol-ilovasi uchun umumiy column-value summalarni hisoblaydi.
    """
    from django.db.models import Prefetch

    # === 1. Avvalgi qiymatlarni yig‘ib olish ===
    inners = ReportItemInner.objects.filter(
        report_item__report=report
    ).select_related("report_item__statement_column")

    grouped = defaultdict(list)
    for inner in inners:
        ordering = inner.report_item.statement_column.ordering
        value = normalize_decimal(inner.value)
        grouped[ordering].append(value)

    # === 2. Recursive hisoblash
    cache = {}

    def resolve(ordering):
        if ordering in cache:
            return cache[ordering]
        if ordering not in THIRD_ORDERING_MAP:
            total = sum(grouped.get(ordering, []))
            cache[ordering] = total
            return total
        total = Decimal(0)
        for src in THIRD_ORDERING_MAP[ordering]:
            is_negative = src.startswith("-")
            src_ordering = src[1:] if is_negative else src
            src_val = resolve(src_ordering)
            total += -src_val if is_negative else src_val
        cache[ordering] = total
        return total

    # === 3. Columnlar va mavjud ReportItem'larni oldindan olib qo‘yamiz
    columns_qs = StatementColumn.objects.filter(statement=report.statement)
    columns = {col.ordering: col for col in columns_qs}

    existing_items_qs = ReportItem.objects.filter(report=report)
    existing_items = {
        (item.statement_column_id): item for item in existing_items_qs
    }

    new_items = []
    updated_items = []
    inners_to_create = []

    for ordering, total in [(o, resolve(o)) for o in THIRD_ORDERING_MAP.keys()]:
        column = columns.get(ordering)
        if not column:
            continue

        item = existing_items.get(column.id)
        if item:
            item.value = str(round(total, 2))
            updated_items.append(item)
        else:
            item = ReportItem(
                report=report,
                statement_column=column,
                value=str(round(total, 2))
            )
            new_items.append(item)

    # === 4. Yaratamiz yoki yangilaymiz
    if new_items:
        ReportItem.objects.bulk_create(new_items)

    if updated_items:
        ReportItem.objects.bulk_update(updated_items, ["value"])

    # 🔻 Inners larni yaratish — plantlarsiz, 1ta inner per column
    all_items = {
        item.statement_column.ordering: item for item in
        ReportItem.objects.filter(report=report).select_related("statement_column")
        if item.statement_column.ordering in THIRD_ORDERING_MAP
    }

    for ordering in THIRD_ORDERING_MAP:
        item = all_items.get(ordering)
        if item:
            inners_to_create.append(ReportItemInner(
                report_item=item,
                value=item.value  # plant yo‘q hali
            ))

    # Tozalash va bulk_create
    ReportItemInner.objects.filter(
        report_item__report=report,
        report_item__statement_column__ordering__in=THIRD_ORDERING_MAP.keys()
    ).delete()

    if inners_to_create:
        ReportItemInner.objects.bulk_create(inners_to_create)



# def calculate_third_seedlings_svod(report):
#     """
#     3-ilova SVOD (Ko‘chat va Nihol umumlashgan) — har bir plant_id bo‘yicha hisoblaydi.
#     """
#     from decimal import Decimal
#     from collections import defaultdict
#     from apps.reports.mapping_columns import THIRD_ORDERING_MAP
#
#     # === Avvalgi plant-based qiymatlarni yig‘amiz ===
#     inners = ReportItemInner.objects.filter(
#         report_item__report=report,
#         plant_id__isnull=False
#     ).select_related("report_item__statement_column")
#
#     grouped = defaultdict(lambda: defaultdict(Decimal))  # ordering → plant_id → Decimal
#     for inner in inners:
#         ordering = inner.report_item.statement_column.ordering
#         value = normalize_decimal(inner.value)
#         grouped[ordering][inner.plant_id] += value
#
#     # === Recursive hisoblash (plant_id asosida)
#     cache = {}
#
#     def resolve(ordering):
#         if ordering in cache:
#             return cache[ordering]
#         if ordering not in THIRD_ORDERING_MAP:
#             return grouped.get(ordering, {})
#
#         result = defaultdict(Decimal)
#         for src in THIRD_ORDERING_MAP[ordering]:
#             is_negative = src.startswith("-")
#             src_ordering = src[1:] if is_negative else src
#             values = resolve(src_ordering)
#             for pid, v in values.items():
#                 result[pid] += -v if is_negative else v
#
#         cache[ordering] = result
#         return result
#
#     # === Mavjud ustunlar va ReportItem lar
#     columns = {
#         col.ordering: col
#         for col in StatementColumn.objects.filter(statement=report.statement)
#     }
#
#     existing_items = {
#         i.statement_column_id: i
#         for i in ReportItem.objects.filter(report=report)
#     }
#
#     # === Eskilarni o‘chirish
#     ReportItemInner.objects.filter(
#         report_item__report=report,
#         report_item__statement_column__ordering__in=THIRD_ORDERING_MAP.keys()
#     ).delete()
#
#     # === Hisoblangan qiymatlarni ReportItem + ReportItemInner ga yozish
#     new_items = []
#     update_items = []
#     new_inners = []
#
#     for ordering, plant_totals in [(o, resolve(o)) for o in THIRD_ORDERING_MAP]:
#         column = columns.get(ordering)
#         if not column:
#             continue
#
#         item = existing_items.get(column.id)
#         if not item:
#             item = ReportItem(
#                 report=report,
#                 statement_column=column,
#                 value="",  # ⚠️ plant-based bo‘lgani uchun umumiy value yo‘q
#             )
#             item.save()
#         else:
#             item.value = ""
#             item.save()
#
#         for plant_id, value in plant_totals.items():
#             new_inners.append(ReportItemInner(
#                 report_item=item,
#                 plant_id=plant_id,
#                 value=str(round(value, 2))
#             ))
#
#     if new_inners:
#         ReportItemInner.objects.bulk_create(new_inners)
