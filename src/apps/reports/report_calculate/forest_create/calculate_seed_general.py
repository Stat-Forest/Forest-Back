from decimal import Decimal
from apps.reports.models import Report, ReportItem, ReportItemInner
from apps.reports.services.get_two_numbers_in_percent import round_decimal


def calculate_seed_plants(report: Report):
    """
    Hisobot: 1-ilova (Niholxona va Ko'chatxona hisoboti)
    Hisoblanadigan ustunlar:
    - 1.1.2.2 = 1.1.3.1.2 + 1.1.3.2.2 (Amalda)
    - 1.1.2.3 = 1.1.2.2 / 1.1.2.1 (Foiz)
    - 1.1.3.1.3 = 1.1.3.1.2 / 1.1.3.1.1 (Foiz)
    - 1.1.3.2.3 = 1.1.3.2.2 / 1.1.3.2.1 (Foiz)
    """
    columns = report.statement.columns.select_related("parent").all()
    ordering_map = {col.ordering: col for col in columns}

    # Oldindan mavjud ReportItem va Innerlarni olish
    items = report.report_items.prefetch_related("inners").all()
    item_map = {item.statement_column_id: item for item in items}
    inner_map = {
        item.statement_column_id: item.inners.first()
        for item in items if item.inners.exists()
    }

    def get_decimal(ordering: str) -> Decimal:
        col = ordering_map.get(ordering)
        if not col:
            return Decimal(0)
        inner = inner_map.get(col.id)
        try:
            return Decimal(inner.value or 0)
        except:
            return Decimal(0)

    def write_value(ordering: str, value: Decimal):
        col = ordering_map.get(ordering)
        if not col:
            return
        item = item_map.get(col.id)
        if not item:
            item = ReportItem.objects.create(report=report, statement_column=col)
            item_map[col.id] = item
        inner = inner_map.get(col.id)
        if not inner:
            inner = ReportItemInner.objects.create(report_item=item, value=str(value))
            inner_map[col.id] = inner
        else:
            inner.value = str(value)
            inner.save(update_fields=["value"])

    # 1.1.2.2 = 1.1.3.1.2 + 1.1.3.2.2
    amalda_jami = get_decimal("1.1.3.1.2") + get_decimal("1.1.3.2.2")
    write_value("1.1.2.2", amalda_jami)

    # 1.1.3.1.3 = 1.1.3.1.2 / 1.1.3.1.1
    reja_1 = get_decimal("1.1.3.1.1")
    amalda_1 = get_decimal("1.1.3.1.2")
    foiz_1 = (amalda_1 / reja_1 * 100) if reja_1 else Decimal(0)
    write_value("1.1.3.1.3", round_decimal(foiz_1))

    # 1.1.3.2.3 = 1.1.3.2.2 / 1.1.3.2.1
    reja_2 = get_decimal("1.1.3.2.1")
    amalda_2 = get_decimal("1.1.3.2.2")
    foiz_2 = (amalda_2 / reja_2 * 100) if reja_2 else Decimal(0)
    write_value("1.1.3.2.3", round_decimal(foiz_2))

    # 1.1.2.3 = 1.1.2.2 / 1.1.2.1
    reja_jami = get_decimal("1.1.2.1")
    foiz_jami = (amalda_jami / reja_jami * 100) if reja_jami else Decimal(0)
    write_value("1.1.2.3", round_decimal(foiz_jami))

    return
