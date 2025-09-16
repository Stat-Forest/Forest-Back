from decimal import Decimal, InvalidOperation
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


def calculate_terrassa_statement(report: Report):
    """
    Hisoblash formulasi:
    1.1.5 = (1.1.4 / 1.1.3) * 100
    Ya'ni: % = (Amalda / Reja) * 100
    Optimallashtirilgan: minimal SQL so‘rovlar bilan.
    """

    # ==== 1. Columnlarni bitta query bilan olish ====
    columns = (
        StatementColumn.objects
        .filter(statement=report.statement, ordering__in=["1.1.3", "1.1.4", "1.1.5"])
    )
    column_map = {col.ordering: col for col in columns}

    col_reja = column_map.get("1.1.3")
    col_amalda = column_map.get("1.1.4")
    col_foiz = column_map.get("1.1.5")

    if not col_reja or not col_amalda or not col_foiz:
        return  # kerakli ustunlar bo‘lmasa chiqamiz

    # ==== 2. ReportItem + Inners ni bitta queryda olib kelamiz ====
    report_items = (
        ReportItem.objects
        .filter(report=report, statement_column__in=[col_reja, col_amalda, col_foiz])
        .prefetch_related("inners")
    )
    item_map = {str(item.statement_column_id): item for item in report_items}

    # ==== 3. Qiymatlarni olish ====
    def get_value(col: StatementColumn) -> Decimal:
        item = item_map.get(str(col.id))
        if not item or not item.inners.exists():
            return Decimal(0)

        inner = item.inners.first()
        if not inner or inner.value is None:
            return Decimal(0)

        try:
            return Decimal(str(inner.value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal(0)

    # ==== 4. Qiymatlarni hisoblash ====
    reja = get_value(col_reja)
    amalda = get_value(col_amalda)

    foiz = Decimal(0)
    if reja > 0:
        foiz = (amalda / reja * 100).quantize(Decimal("1.00"))

    # ==== 5. Qiymatni saqlash ====
    def save_value(col: StatementColumn, value: Decimal):
        item = item_map.get(str(col.id))
        if not item:
            item = ReportItem.objects.create(report=report, statement_column=col)

        inner = item.inners.first()
        if inner:
            inner.value = value
            inner.save()
        else:
            ReportItemInner.objects.create(report_item=item, value=value)

    save_value(col_foiz, foiz)
