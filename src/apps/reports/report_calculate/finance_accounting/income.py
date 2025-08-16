from decimal import Decimal, InvalidOperation
from apps.reports.models import ReportItem, ReportItemInner, StatementColumn, Report


def calculate_income_summary(report: Report):
    statement = report.statement
    columns = statement.columns.prefetch_related("children").all()

    # === 1-ILOVA: 1.1 va 1.1.19 ni hisoblash ===
    for column in columns:
        if column.ordering == "1.1":
            input_columns = []
            jami_column = None

            for child in column.children.all():
                if not child.ordering:
                    continue

                if child.ordering.startswith("1.1."):
                    if child.ordering == "1.1.19":
                        jami_column = child
                    else:
                        input_columns.append(child)

            if jami_column:
                total = sum_values(report, input_columns)
                create_calculated_items(report, jami_column, total)

    # === 2-ILOVA: Choraklar (Amalda) yig‘indisi va Yillik reja nisbati (%) ===
    chorak_amalda_orderings = [f"1.1.{i}" for i in (3, 5, 7, 9)]
    chorak_amalda_columns = []

    for column in columns:
        if column.ordering in chorak_amalda_orderings:
            for child in column.children.all():
                if child.title_uz == "Amalda":
                    chorak_amalda_columns.append(child)

    tushum_column = next(
        (col for col in columns if col.ordering == "1.1.11.1"), None
    )
    if tushum_column:
        total_amalda = sum_values(report, chorak_amalda_columns)
        create_calculated_items(report, tushum_column, total_amalda)

    reja_column = next(
        (col for col in columns if col.ordering == "1.1.2"), None
    )
    foiz_column = next(
        (col for col in columns if col.ordering == "1.1.11.2"), None
    )

    if reja_column and foiz_column:
        reja_value = sum_values(report, [reja_column])
        if reja_value > 0:
            foiz = (total_amalda / reja_value) * 100
        else:
            foiz = Decimal(0)
        create_calculated_items(report, foiz_column, foiz)


def create_calculated_items(report, column, value: Decimal):
    item, _ = ReportItem.objects.get_or_create(
        report=report,
        statement_column=column
    )

    inner = item.inners.first()
    if inner:
        inner.value = str(round(value, 2))
        inner.save(update_fields=["value"])
    else:
        ReportItemInner.objects.create(
            report_item=item,
            value=str(round(value, 2))
        )


def sum_values(report: Report, columns: list[StatementColumn]) -> Decimal:
    report_item_ids = ReportItem.objects.filter(
        report=report, statement_column__in=columns
    ).values_list("id", flat=True)

    inners = ReportItemInner.objects.filter(report_item_id__in=report_item_ids)

    total = Decimal("0")
    for inner in inners:
        try:
            total += Decimal(str(inner.value))
        except (InvalidOperation, TypeError, ValueError):
            continue

    return total
