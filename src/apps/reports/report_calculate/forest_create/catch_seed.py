from decimal import Decimal
from apps.reports.models import Report, ReportItem, ReportItemInner
from apps.reports.report_calculate.forest_create.seedlings_sprouts import normalize


def sum_values(item):
    if item is None:
        return Decimal(0)
    return sum([normalize(inner.value) for inner in item.inners.all()], Decimal(0))


def calculate_catch_seed(report: Report):
    """
    'Tut yetishtirish' bo‘limi uchun hisob-kitob:
        - Amalda (1.1.2.2) = Tut Nihol (1.1.2.4.1) + Tut Ko‘chat (1.1.2.4.2)
        - Foiz (1.1.2.3) = Amalda / Reja * 100
    """
    relevant_orderings = [
        "1.1.2.1",  # Reja
        "1.1.2.2",  # Amalda (hisoblanadi)
        "1.1.2.3",  # Foiz (hisoblanadi)
        "1.1.2.4.1",  # Tut Nihol
        "1.1.2.4.2",  # Tut Ko‘chat
    ]

    # Bazadagi mavjud itemlarni yuklash
    existing_items = (
        report.report_items
        .filter(statement_column__ordering__in=relevant_orderings)
        .select_related("statement_column")
        .prefetch_related("inners")
    )
    items_by_ordering = {item.statement_column.ordering: item for item in existing_items}

    # Yetishmayotgan columnlar uchun ReportItem larni yaratish
    from apps.reports.models import StatementColumn

    columns = StatementColumn.objects.filter(
        statement=report.statement,
        ordering__in=relevant_orderings
    )

    for col in columns:
        if col.ordering not in items_by_ordering:
            new_item = ReportItem.objects.create(
                report=report,
                statement_column=col
            )
            items_by_ordering[col.ordering] = new_item

    # --- Amalda = Tut Nihol + Tut Ko‘chat
    nihol_sum = sum_values(items_by_ordering.get("1.1.2.4.1"))
    kochat_sum = sum_values(items_by_ordering.get("1.1.2.4.2"))
    amalda_value = normalize(nihol_sum) + normalize(kochat_sum)

    amalda_item = items_by_ordering.get("1.1.2.2")
    if amalda_item:
        amalda_item.inners.all().delete()
        ReportItemInner.objects.create(
            report_item=amalda_item,
            value=amalda_value
        )

    # --- Foiz = Amalda / Reja * 100
    reja_value = sum_values(items_by_ordering.get("1.1.2.1"))
    foiz_value = (
        (normalize(amalda_value) / normalize(reja_value) * 100)
        if normalize(reja_value) > 0 else Decimal(0)
    )

    foiz_item = items_by_ordering.get("1.1.2.3")
    if foiz_item:
        foiz_item.inners.all().delete()
        ReportItemInner.objects.create(
            report_item=foiz_item,
            value=foiz_value.quantize(Decimal("1.00"))  # 2 decimals
        )
