from decimal import Decimal
from collections import defaultdict

from apps.reports.models import Report, ReportItemInner, ReportItem
from apps.reports.services.general_report import normalize


def calculate_additional(report: Report):
    """
    Hisobot: Metallolom ilovasi (ordering: 7.1)
    Optimallashtirilgan: duplicate SELECT larni kamaytirish uchun oldindan kiritilgan qiymatlar cache qilinadi.
    """
    statement = report.statement
    columns = statement.columns.filter(ordering__startswith="7.1.")
    column_map = {col.ordering: col for col in columns}

    all_inners = ReportItemInner.objects.filter(
        report_item__report=report
    ).select_related("report_item", "report_item__statement_column")

    inner_values = defaultdict(list)
    for inner in all_inners:
        col_id = inner.report_item.statement_column_id
        inner_values[col_id].append(inner.value)

    def get_first_value(col):
        values = inner_values.get(col.id, [])
        return values[0] if values else "0"

    def get_sum(col):
        total = Decimal(0)
        for val in inner_values.get(col.id, []):
            try:
                total += Decimal(str(val))
            except (ValueError, TypeError):
                continue
        return total

    yillik_reja = Decimal(0)
    yillik_amalda = Decimal(0)

    items_to_create = []

    for i in range(1, 5):
        chorak_prefix = f"7.1.{i + 4}"

        reja_col = column_map.get(f"{chorak_prefix}.1")
        amalda_col = column_map.get(f"{chorak_prefix}.2")
        foiz_col = column_map.get(f"{chorak_prefix}.3")

        if not (reja_col and amalda_col and foiz_col):
            continue

        reja_value = get_first_value(reja_col)
        amalda_value = get_sum(amalda_col)

        yillik_reja += normalize(reja_value)
        yillik_amalda += normalize(amalda_value)

        percent = Decimal(0)
        if normalize(reja_value) > 0:
            percent = normalize(amalda_value) / normalize(reja_value) * 100

        items_to_create.append((foiz_col, percent))

    # Yillik ustunlar
    yillik_amalda_col = column_map.get("7.1.3", None)
    yillik_percent_col = column_map.get("7.1.4", None)

    if yillik_amalda_col:
        items_to_create.append((yillik_amalda_col, yillik_amalda))

    if yillik_percent_col and normalize(yillik_reja) > 0:
        yillik_foiz = yillik_amalda / yillik_reja * 100
        items_to_create.append((yillik_percent_col, yillik_foiz))

    # Hamma itemlarni bir marta bulk_create bilan saqlaymiz
    create_calculated_items_bulk(report, items_to_create)


def create_calculated_items_bulk(report, items_data):
    """
    Hisoblangan qiymatlarni bulk_create bilan bazaga saqlaydi.
    `items_data` ro‘yxati: (column, value) tuplardan iborat.
    """
    report_items = []
    report_inners = []

    for column, value in items_data:
        report_item = ReportItem(
            report=report,
            statement_column=column,
        )
        report_items.append(report_item)

    # Birinchi bulk_create: ReportItem
    ReportItem.objects.bulk_create(report_items)

    for report_item, (column, value) in zip(report_items, items_data):
        report_inners.append(ReportItemInner(
            report_item=report_item,
            value=str(value),
        ))

    # Ikkinchi bulk_create: ReportItemInner
    ReportItemInner.objects.bulk_create(report_inners)
