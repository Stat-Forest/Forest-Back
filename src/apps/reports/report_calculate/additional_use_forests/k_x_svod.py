from decimal import Decimal
from collections import defaultdict
from apps.reports.models import ReportItem, ReportItemInner


def calculate_kxsvod_custom(report, columns):
    """
    K-X svod qiymatlarini hisoblab, kerakli ustunlarga yozadi.
    """

    # === 1. ORDERING MAPPING ===
    # Asosiy parentlar
    aggregation_map = {
        # Jami Reja gektar
        "9.1.2.1": ["9.1.3.1.1", "9.1.3.2.1", "9.1.3.3.1", "9.1.3.4.1", "9.1.3.5.1"],
        # Jami Reja tonna
        "9.1.2.2": ["9.1.3.1.2", "9.1.3.2.2", "9.1.3.3.2", "9.1.3.4.2", "9.1.3.5.2"],
        # Fermer + boshqa ustunlar qo‘shiladi quyidagicha
        "9.1.3.1.3": ["1.1.2.1", "5.1.2.1"],
        "9.1.3.1.4": ["1.1.2.2", "5.1.2.2"],
        "9.1.3.2.3": ["2.1.2.1", "3.1.2.1"],
        "9.1.3.2.4": ["2.1.2.2", "3.1.2.2"],
        "9.1.3.3.3": ["4.1.2.1"],
        "9.1.3.3.4": ["4.1.2.2"],
        "9.1.3.4.3": ["6.1.2.1"],
        "9.1.3.4.4": ["6.1.2.2"],
        "9.1.3.5.3": ["7.1.2.1", "8.1.2.1"],
        "9.1.3.5.4": ["7.1.2.3", "8.1.2.3"],
    }

    all_orderings = set(aggregation_map.keys()) | set(sum(aggregation_map.values(), []))
    column_map = {col.ordering: col for col in columns if col.ordering in all_orderings}

    # === 2. Ma’lumotlarni oldindan olish ===
    report_items = (
        ReportItem.objects
        .filter(report=report, statement_column__ordering__in=all_orderings)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    # === 3. Qiymatlarni yig‘ish ===
    ordering_totals = defaultdict(Decimal)
    for item in report_items:
        ordering = item.statement_column.ordering
        if not ordering:
            continue
        total = sum(Decimal(inner.value or 0) for inner in item.inners.all())
        ordering_totals[ordering] += total

    # === 4. Yakuniy qiymatlar ===
    result_map = {}
    for parent_ordering, children in aggregation_map.items():
        result_map[parent_ordering] = sum(ordering_totals.get(child, Decimal(0)) for child in children)

    # === 5. Eski qiymatlarni o‘chirish ===
    ReportItem.objects.filter(report=report, statement_column__ordering__in=result_map.keys()).delete()

    # === 6. Yangi qiymatlarni yaratish ===
    new_items = []
    new_inners = []

    for ordering, value in result_map.items():
        column = column_map.get(ordering)
        if not column:
            continue
        item = ReportItem(report=report, statement_column=column)
        new_items.append(item)
        new_inners.append(ReportItemInner(value=str(value), report_item=item))

    ReportItem.objects.bulk_create(new_items)
    for inner, item in zip(new_inners, new_items):
        inner.report_item = item
    ReportItemInner.objects.bulk_create(new_inners)
