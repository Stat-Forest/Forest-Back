from decimal import Decimal
from apps.reports.models import ReportItem, ReportItemInner


def calculate_kxsvod(report, columns):
    """
    K-X SVOD (9-ilova) uchun quyidagi ustunlarni hisoblaydi:
    - 9.1.2.2 → Amalda gektar
    - 9.1.2.3 → s/ga
    - 9.1.2.4 → Amalda (tonna)
    """
    # Target ustunlar
    target_orderings = {
        "9.1.2.2": [  # Amalda gektar
            "9.1.3.1.1", "9.1.3.2.1", "9.1.3.3.1", "9.1.3.4.1", "9.1.3.5.1", "9.1.3.6.1",
            "9.1.4.1.1", "9.1.5.1.1"
        ],
        "9.1.2.3": [  # s/ga
            "9.1.3.1.2", "9.1.3.2.2", "9.1.3.3.2", "9.1.3.4.2", "9.1.3.5.2", "9.1.3.6.2",
            "9.1.4.1.3", "9.1.5.1.3"
        ],
        "9.1.2.4": [  # Amalda (tonna)
            "9.1.3.1.3", "9.1.3.2.3", "9.1.3.3.3", "9.1.3.4.3", "9.1.3.5.3", "9.1.3.6.3",
            "9.1.4.1.4", "9.1.5.1.4"
        ],
    }

    # Parent ustunlarni topamiz
    column_map = {col.ordering: col for col in columns if col.ordering in target_orderings.keys()}

    # Barcha ReportItem'larni oldindan olib qo‘yamiz
    report_items_map = {
        item.statement_column_id: item
        for item in report.report_items.prefetch_related("inners").all()
    }

    # Yig‘ish natijalari
    result_map = {
        "9.1.2.2": Decimal(0),
        "9.1.2.3": Decimal(0),
        "9.1.2.4": Decimal(0),
    }

    # Crop orderinglar → value yig‘ish
    crop_ordering_set = set(sum(target_orderings.values(), []))  # barcha source orderings

    for col in columns:
        if col.ordering in crop_ordering_set:
            item = report_items_map.get(col.id)
            if item and item.inners.exists():
                try:
                    total = sum(Decimal(inner.value or 0) for inner in item.inners.all())
                    for target, sources in target_orderings.items():
                        if col.ordering in sources:
                            result_map[target] += total
                            break
                except:
                    continue

    # Natijani tegishli ustunlarga yozish
    for ordering, total_value in result_map.items():
        column = column_map.get(ordering)
        if column:
            item, _ = ReportItem.objects.get_or_create(
                report=report,
                statement_column=column
            )
            inner = item.inners.first()
            if inner:
                inner.value = str(total_value)
                inner.save(update_fields=["value"])
            else:
                ReportItemInner.objects.create(report_item=item, value=str(total_value))
