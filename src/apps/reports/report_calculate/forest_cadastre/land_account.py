from collections import defaultdict
from decimal import Decimal

from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


def calculate_leased_land(report: Report):
    """
    Yer o‘zlashtirish → 2-ilova: Imtiyozli maydon Jami hisoblash (2.1.9.1)
    """
    JAMI_ORDERING = "2.1.9.1"
    PLANTATION_CHILDREN = [
        "2.1.9.2.1",
        "2.1.9.2.2",
        "2.1.9.2.3",
        "2.1.9.2.4",
    ]

    # ReportItemlarni ordering bo‘yicha guruhlash
    report_items_map = defaultdict(list)
    for item in report.report_items.prefetch_related("inners", "statement_column").all():
        ordering = item.statement_column.ordering
        report_items_map[ordering].append(item)

    # Jami hisoblash
    jami_total = sum(get_decimal_value(report_items_map.get(ordering)) for ordering in PLANTATION_CHILDREN)

    # Natijani saqlash
    save_value(report, report_items_map, JAMI_ORDERING, jami_total)


def get_decimal_value(items: list[ReportItem] | None) -> Decimal:
    """
    ReportItem list ichidan qiymatlarni yig‘adi
    """
    total = Decimal(0)
    if not items:
        return total

    for item in items:
        inner = item.inners.first()
        if inner:
            try:
                total += Decimal(inner.value or 0)
            except:
                continue
    return total


def save_value(report: Report, report_items_map: dict, ordering: str, value: Decimal):
    """
    Berilgan ordering bo‘yicha qiymatni yangilaydi yoki yaratadi.
    """
    items = report_items_map.get(ordering)

    if items:
        item = items[0]
        inner = item.inners.first()
        if inner:
            inner.value = str(value)
            inner.save(update_fields=["value"])
        else:
            ReportItemInner.objects.create(report_item=item, value=str(value))
    else:
        try:
            column = StatementColumn.objects.get(statement=report.statement, ordering=ordering)
        except StatementColumn.DoesNotExist:
            print(f"[XATO] Column topilmadi: {ordering}")
            return

        new_item = ReportItem.objects.create(report=report, statement_column=column)
        ReportItemInner.objects.create(report_item=new_item, value=str(value))
        report_items_map[ordering] = [new_item]
