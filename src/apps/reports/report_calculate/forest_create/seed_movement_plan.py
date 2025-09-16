from decimal import Decimal
from apps.reports.models import Report, ReportItem, ReportItemInner


def calculate_seed_movement_plan(report: Report):
    ordering_map = {
        "REJA": "1.1.2.1",
        "AMALDA": "1.1.2.2",
        "FOIZ": "1.1.2.3",
    }

    # === Barcha itemlar (Reja, Amalda) keltiramiz
    report_items = (
        ReportItem.objects
        .filter(report=report)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    column_map = {item.statement_column.ordering: item for item in report_items}

    # === Qiymatlarni olish
    def get_total(ordering: str) -> Decimal:
        item = column_map.get(ordering)
        if not item:
            return Decimal(0)
        return sum(Decimal(str(i.value or 0)) for i in item.inners.all())

    reja = get_total(ordering_map["REJA"])
    amalda = get_total(ordering_map["AMALDA"])

    # === Foiz hisoblash
    foiz = (amalda / reja * 100) if reja else Decimal(0)

    # === Foiz ustunini saqlash
    foiz_item = column_map.get(ordering_map["FOIZ"])
    if foiz_item:
        inner = foiz_item.inners.first()
        if inner:
            inner.value = str(foiz)
            inner.save(update_fields=["value"])
        else:
            ReportItemInner.objects.create(report_item=foiz_item, value=str(foiz))
    else:
        from apps.reports.models import StatementColumn
        col = StatementColumn.objects.filter(
            statement=report.statement,
            ordering=ordering_map["FOIZ"]
        ).first()
        if col:
            new_item = ReportItem.objects.create(report=report, statement_column=col)
            ReportItemInner.objects.create(report_item=new_item, value=str(foiz))
