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

    # 3. Har bir ordering uchun value ni olish (faqat birinchi inner qiymati olinadi)
    value_map = {}
    for ordering, item in items_map.items():
        inners = list(item.inners.all())
        if inners:
            value_map[ordering] = safe_decimal(inners[0].value)

    # 4. Kerakli column'lar
    all_orderings = [
        "1.1.3.1", "1.1.3.2", "1.1.3.3",
        "1.1.4.1", "1.1.4.2", "1.1.4.3",
        "1.1.2.1", "1.1.2.2", "1.1.2.3"
    ]
    columns_map = {
        col.ordering: col
        for col in StatementColumn.objects.filter(
            statement=report.statement,
            ordering__in=all_orderings
        )
    }

    # 5. Hisoblash
    def safe_div(x, y):
        if not y or y == 0:
            return Decimal("0.00")
        return (Decimal(x) / Decimal(y)).quantize(Decimal("1.00"))

    reja_bahor = value_map.get("1.1.3.1", Decimal(0))
    amalda_bahor = value_map.get("1.1.3.2", Decimal(0))
    reja_kuz = value_map.get("1.1.4.1", Decimal(0))
    amalda_kuz = value_map.get("1.1.4.2", Decimal(0))

    reja_jami = reja_bahor + reja_kuz
    amalda_jami = amalda_bahor + amalda_kuz

    results = {
        "1.1.3.3": safe_div(amalda_bahor, reja_bahor) * 100,
        "1.1.4.3": safe_div(amalda_kuz, reja_kuz) * 100,
        "1.1.2.1": reja_jami,
        "1.1.2.2": amalda_jami,
        "1.1.2.3": safe_div(amalda_jami, reja_jami) * 100,
    }

    # 6. Eski inners'larni o‘chirish (faqat update bo‘ladiganlarini)
    to_delete_ids = []
    for ordering, item in items_map.items():
        if ordering in results:
            inners = list(item.inners.all())
            if inners:
                to_delete_ids.append(inners[0].id)
    if to_delete_ids:
        ReportItemInner.objects.filter(id__in=to_delete_ids).delete()

    # 7. Yangi ReportItem'larni yaratish (agar kerak bo‘lsa)
    to_create_items = []
    for ordering in results:
        if ordering not in items_map and ordering in columns_map:
            to_create_items.append(
                ReportItem(report=report, statement_column=columns_map[ordering])
            )

    created_items = ReportItem.objects.bulk_create(to_create_items)

    for item in created_items:
        items_map[item.statement_column.ordering] = item

    # 8. Yangi inner'larni yaratish
    new_inners = [
        ReportItemInner(report_item=items_map[o], value=v)
        for o, v in results.items() if o in items_map
    ]
    ReportItemInner.objects.bulk_create(new_inners)
