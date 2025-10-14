from decimal import Decimal, InvalidOperation
from collections import defaultdict

from apps.reports.mapping_columns import THIRD_ORDERING_MAP
from apps.reports.models import ReportItemInner, StatementColumn, ReportItem, Plant


def get_plants_from_sub_ilovas(report):
    """
    Berilgan reportdagi (Ko‘chat-ilovasi yoki Nihol-ilovasi) barcha ishlatilgan plantlarni olib keladi.
    Faqat ushbu reportdagi `inners` orqali aniqlanadi.
    """
    plant_ids = (
        ReportItemInner.objects
        .filter(report_item__report=report, plant__isnull=False)
        .values_list("plant_id", flat=True)
        .distinct()
    )

    return Plant.objects.filter(id__in=plant_ids)


def normalize_decimal(value):
    try:
        return Decimal(str(value).strip())
    except (TypeError, ValueError, InvalidOperation):
        return Decimal(0)


def calculate_third_seedlings_svod(report):
    """
    3-ilova SVOD: Ko‘chat-va-Nihol-ilovasi uchun umumiy column-value summalarni hisoblaydi.
    Har bir column uchun umumiy qiymat (value) va barcha plantlar bo‘yicha bo‘sh ReportItemInner yoziladi.
    """

    # === 1. Barcha mavjud qiymatlarni yig‘ib olish ===
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

    # === 3. Columnlar va plantlarni olish
    columns = {
        col.ordering: col
        for col in StatementColumn.objects.filter(statement=report.statement)
    }
    plants = list(get_plants_from_sub_ilovas(report))  # Faqat 1 marta chaqiriladi

    # === 4. Har bir target ordering uchun item va inner yaratish
    inners_to_create = []

    for ordering in THIRD_ORDERING_MAP.keys():
        column = columns.get(ordering)
        if not column:
            continue

        total = resolve(ordering)
        item, _ = ReportItem.objects.get_or_create(report=report, statement_column=column)
        item.value = str(round(total, 2))
        item.save()

        for plant in plants:
            inners_to_create.append(ReportItemInner(
                report_item=item,
                plant=plant,
                value=str(round(total, 2))
            ))

    # === 5. Eski plant-based innerslarni tozalab, yangilarini bulk_create qilish
    svod_items = ReportItem.objects.filter(
        report=report,
        statement_column__ordering__in=THIRD_ORDERING_MAP.keys()
    )

    ReportItemInner.objects.filter(report_item__in=svod_items, plant__isnull=False).delete()

    if inners_to_create:
        ReportItemInner.objects.bulk_create(inners_to_create)
