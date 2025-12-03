from decimal import Decimal
from apps.reports.models import ReportItem, Report, ReportItemInner
from apps.reports.services.get_two_numbers_in_percent import round_decimal


def calculate_land(report: Report):
    """
    Choraklar yig‘indisi asosida Amalda va Foiz ustunlarini hisoblaydi.
    """
    # 1-ilova ==================================
    # Barcha kerakli ustunlar oldindan olinadi

    O_REJA = "1.1.2"  # Reja
    O_AMALDA = "1.1.3"  # Amalda
    O_FOIZ = "1.1.5"  # Foiz
    O_CHORAKS = [  # Choraklar
        "1.1.4.1", "1.1.4.2", "1.1.4.3", "1.1.4.4"
    ]

    # ReportItem larni xaritaga yuklab olish
    report_items_map = {
        item.statement_column.ordering: item
        for item in report.report_items.prefetch_related("inners", "statement_column").all()
    }

    reja_val = get_decimal_value(report_items_map.get(O_REJA))
    chorak_sum = sum(get_decimal_value(report_items_map.get(o)) for o in O_CHORAKS)
    foiz_val = (chorak_sum / reja_val * 100) if reja_val > 0 else Decimal(0)

    # ✅ Foizni yaxlitlab olamiz: 1 xonali aniqlikda
    foiz_val = round_decimal(foiz_val, places=1)

    # Natijalarni saqlash
    save_value(report, report_items_map, O_AMALDA, chorak_sum)
    save_value(report, report_items_map, O_FOIZ, foiz_val)


def get_decimal_value(item: ReportItem | None) -> Decimal:
    """
    ReportItem'dan Decimal qiymatni qaytaradi (inners.first() orqali)
    """
    if not item or not item.inners.exists():
        return Decimal(0)
    try:
        return Decimal(item.inners.first().value or 0)
    except:
        return Decimal(0)


def save_value(report: Report, report_items_map: dict, ordering: str, value: Decimal):
    """
    Berilgan ordering bo‘yicha qiymatni yangilaydi yoki yaratadi.
    """
    item = report_items_map.get(ordering)

    if item:
        inner = item.inners.first()
        if inner:
            inner.value = str(value)
            inner.save(update_fields=["value"])
        else:
            ReportItemInner.objects.create(report_item=item, value=str(value))
    else:
        from apps.reports.models import StatementColumn
        column = StatementColumn.objects.get(statement=report.statement, ordering=ordering)
        new_item = ReportItem.objects.create(report=report, statement_column=column)
        ReportItemInner.objects.create(report_item=new_item, value=str(value))
