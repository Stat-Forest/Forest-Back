from decimal import Decimal
from collections import defaultdict


def calculate_kxsvod(report, columns):
    from apps.reports.models import ReportItem, ReportItemInner

    target_orderings = {
        "9.1.2.2": [
            "9.1.3.1.1", "9.1.3.2.1", "9.1.3.3.1", "9.1.3.4.1", "9.1.3.5.1", "9.1.3.6.1",
            "9.1.4.1.1", "9.1.5.1.1"
        ],
        "9.1.2.3": [
            "9.1.3.1.2", "9.1.3.2.2", "9.1.3.3.2", "9.1.3.4.2", "9.1.3.5.2", "9.1.3.6.2",
            "9.1.4.1.3", "9.1.5.1.3"
        ],
        "9.1.2.4": [
            "9.1.3.1.3", "9.1.3.2.3", "9.1.3.3.3", "9.1.3.4.3", "9.1.3.5.3", "9.1.3.6.3",
            "9.1.4.1.4", "9.1.5.1.4"
        ],
    }

    all_orderings = set(sum(target_orderings.values(), [])) | set(target_orderings.keys())
    column_map = {col.ordering: col for col in columns if col.ordering in all_orderings}

    # Barcha kerakli ReportItem va ReportItemInnerlarni bitta queryda oldik
    report_items = (
        ReportItem.objects.filter(report=report, statement_column__ordering__in=all_orderings)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    # ordering => total_sum
    ordering_totals = defaultdict(Decimal)

    for item in report_items:
        ordering = item.statement_column.ordering
        if not ordering:
            continue
        total = sum(Decimal(inner.value or 0) for inner in item.inners.all())
        ordering_totals[ordering] += total

    # Yakuniy natijalar uchun result_map
    result_map = {key: Decimal(0) for key in target_orderings}
    for parent_ordering, child_orderings in target_orderings.items():
        for child in child_orderings:
            result_map[parent_ordering] += ordering_totals.get(child, Decimal(0))

    # Eski hisoblangan ReportItemlar tozalanadi
    target_columns = [column_map[o] for o in result_map if o in column_map]
    ReportItem.objects.filter(report=report, statement_column__in=target_columns).delete()

    # Yangi itemlar tayyorlash
    new_items = []
    new_inners = []

    for ordering, total in result_map.items():
        column = column_map.get(ordering)
        if not column:
            continue
        item = ReportItem(report=report, statement_column=column)
        new_items.append(item)
        new_inners.append(ReportItemInner(value=str(total), report_item=item))

    # Bulk create bilan saqlash
    ReportItem.objects.bulk_create(new_items)
    for inner, item in zip(new_inners, new_items):
        inner.report_item = item
    ReportItemInner.objects.bulk_create(new_inners)
