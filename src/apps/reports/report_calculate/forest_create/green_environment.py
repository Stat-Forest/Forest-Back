from decimal import Decimal, InvalidOperation
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.services.get_two_numbers_in_percent import round_decimal


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

    # 3. Har bir ordering uchun value ni olish
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
            return Decimal("0")
        return round_decimal(Decimal(x) / Decimal(y) * 100, 2)  # ← FOIZ GA AYLANTIRIB + ROUND

    reja_bahor = value_map.get("1.1.3.1", Decimal(0))
    amalda_bahor = value_map.get("1.1.3.2", Decimal(0))
    reja_kuz   = value_map.get("1.1.4.1", Decimal(0))
    amalda_kuz = value_map.get("1.1.4.2", Decimal(0))

    # Bahor va kuz jami
    reja_jami = reja_bahor + reja_kuz
    amalda_jami = amalda_bahor + amalda_kuz

    # 6. Natijalar
    results = {
        "1.1.3.3": safe_div(amalda_bahor, reja_bahor),   # bahor %
        "1.1.4.3": safe_div(amalda_kuz, reja_kuz),       # kuz %
        "1.1.2.1": round_decimal(reja_jami, 2),          # jami reja
        "1.1.2.2": round_decimal(amalda_jami, 2),        # jami amalda
        "1.1.2.3": safe_div(amalda_jami, reja_jami),     # jami %
    }

    # 7. Eski inners’larni o‘chirish
    to_delete_ids = []
    for ordering, item in items_map.items():
        if ordering in results:
            inners = list(item.inners.all())
            if inners:
                to_delete_ids.append(inners[0].id)

    if to_delete_ids:
        ReportItemInner.objects.filter(id__in=to_delete_ids).delete()

    # 8. Yangi itemlarni yaratish
    to_create_items = []
    for ordering in results:
        if ordering not in items_map and ordering in columns_map:
            to_create_items.append(
                ReportItem(report=report, statement_column=columns_map[ordering])
            )

    created_items = ReportItem.objects.bulk_create(to_create_items)

    for item in created_items:
        items_map[item.statement_column.ordering] = item

    # 9. Yangi innerlar yaratish
    new_inners = [
        ReportItemInner(report_item=items_map[o], value=str(v))
        for o, v in results.items() if o in items_map
    ]

    ReportItemInner.objects.bulk_create(new_inners)
