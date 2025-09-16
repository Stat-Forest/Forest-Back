from decimal import Decimal, InvalidOperation
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


def safe_decimal(value) -> Decimal:
    try:
        return Decimal(str(value)) if value is not None else Decimal(0)
    except (InvalidOperation, ValueError):
        return Decimal(0)


def calculate_green_environment(report: Report):
    # 1. Barcha item va inner'larni oldindan yuklab olish
    report_items = report.report_items.prefetch_related("inners", "statement_column").all()

    # 2. ReportItem'larni ordering bo‘yicha xarita
    items_map = {
        item.statement_column.ordering: item for item in report_items
    }

    # 3. Inner qiymatlarni olish (N+1 so‘rov YO‘Q!)
    value_map = {}
    for ordering, item in items_map.items():
        # inners.all() => bu prefetch bo‘lib kelyapti, yangi so‘rov emas
        inners = list(item.inners.all())
        if inners:
            value_map[ordering] = safe_decimal(inners[0].value)

    # 4. Oldindan kerakli column'larni olish
    all_orderings = ["1.1.3.3", "1.1.4.3", "1.1.2.2", "1.1.2.3"]
    columns_map = {
        col.ordering: col
        for col in StatementColumn.objects.filter(
            statement=report.statement,
            ordering__in=all_orderings
        )
    }

    # 5. Hisoblashlar
    def safe_div(x, y):
        if y in (None, 0):
            return Decimal(0)
        return (Decimal(x) / Decimal(y)).quantize(Decimal("1.00"))

    amalda_bahor = value_map.get("1.1.3.2", Decimal(0))
    reja_bahor = value_map.get("1.1.3.1", Decimal(0))
    amalda_kuz = value_map.get("1.1.4.2", Decimal(0))
    reja_kuz = value_map.get("1.1.4.1", Decimal(0))
    reja_jami = value_map.get("1.1.2.1", Decimal(0))

    results = {
        "1.1.3.3": safe_div(amalda_bahor, reja_bahor) * 100,
        "1.1.4.3": safe_div(amalda_kuz, reja_kuz) * 100,
        "1.1.2.2": amalda_bahor + amalda_kuz,
        "1.1.2.3": safe_div(amalda_bahor + amalda_kuz, reja_jami) * 100,
    }

    # 6. Eski inners'larni bulk delete
    to_delete_ids = []
    for ordering, item in items_map.items():
        if ordering in results:
            inners = list(item.inners.all())
            if inners:
                to_delete_ids.append(inners[0].id)

    if to_delete_ids:
        ReportItemInner.objects.filter(id__in=to_delete_ids).delete()

    # 7. Yangi ReportItem'lar bulk_create qilish
    to_create_items = []
    for ordering in results:
        if ordering not in items_map:
            column = columns_map.get(ordering)
            if column:
                to_create_items.append(
                    ReportItem(report=report, statement_column=column)
                )

    created_items = ReportItem.objects.bulk_create(to_create_items)

    # 8. items_map'ga yangi itemlarni qo‘shish
    for item in created_items:
        items_map[item.statement_column.ordering] = item

    # 9. Yangi innerlarni bulk_create qilish
    new_inners = [
        ReportItemInner(report_item=items_map[o], value=v)
        for o, v in results.items()
        if o in items_map
    ]
    ReportItemInner.objects.bulk_create(new_inners)
