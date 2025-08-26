from decimal import Decimal

from django.db.models import Sum

from apps.reports.models import Report, StatementColumn, ReportItemInner, ReportItem
from apps.reports.services.general_report import normalize


def calculate_additional(report: Report):
    """
    Hisobot: Metallolom ilovasi (ordering: 7.1)

    - Har chorak uchun: % = Amalda / Reja * 100
    - Yillik: reja = chorak rejalari yig'indisi
               amalda = chorak amaldalari yig'indisi
               % = yillik_am / yillik_reja * 100
    """
    statement = report.statement
    columns = statement.columns.filter(ordering__startswith="7.1.")
    column_map = {col.ordering: col for col in columns}

    # Choraklar: 1–4
    yillik_reja = Decimal(0)
    yillik_amalda = Decimal(0)

    for i in range(1, 5):
        chorak_prefix = f"7.1.{i+1}"

        reja_col = column_map.get(f"{chorak_prefix}.1")
        amalda_col = column_map.get(f"{chorak_prefix}.2")
        foiz_col = column_map.get(f"{chorak_prefix}.3")

        if not (reja_col and amalda_col and foiz_col):
            continue

        # Reja qiymatini olish (birinchi item qiymatini olamiz)
        reja_value = ReportItemInner.objects.filter(
            report_item__report=report,
            report_item__statement_column=reja_col
        ).values_list("value", flat=True).first() or 0

        amalda_value = sum_values(report, amalda_col)

        yillik_reja += normalize(reja_value)
        yillik_amalda += normalize(amalda_value)

        # % = amalda / reja * 100
        percent = Decimal(0)
        if normalize(reja_value) > 0:
            percent = normalize(amalda_value) / normalize(reja_value) * 100

        create_calculated_items(report, foiz_col, percent)

    # Yillik ustunlar
    yillik_reja_col = column_map.get("7.1.2", None)
    yillik_amalda_col = column_map.get("7.1.2", None)
    yillik_percent_col = column_map.get("7.1.2", None)

    for col in columns:
        if col.ordering == "7.1.2" and col.status_plan == StatementColumn.PlanStatus.YILLIK:
            yillik_reja_col = col
        elif col.ordering == "7.1.2" and not col.is_user_input:
            if not yillik_amalda_col:
                yillik_amalda_col = col
            elif not yillik_percent_col:
                yillik_percent_col = col

    # Natijalarni yozish
    if yillik_amalda_col:
        create_calculated_items(report, yillik_amalda_col, yillik_amalda)

    if yillik_percent_col and normalize(yillik_reja) > 0:
        yillik_foiz = yillik_amalda / yillik_reja * 100
        create_calculated_items(report, yillik_percent_col, yillik_foiz)


def sum_values(report: Report, column) -> Decimal:
    """
    Report va column uchun ReportItemInner.value qiymatlarini yig'indisini hisoblaydi.
    value maydoni CharField bo'lsa, Decimal ga o'tkazib qo'lda summalaydi.
    """
    values = ReportItemInner.objects.filter(
        report_item__report=report,
        report_item__statement_column=column
    ).values_list("value", flat=True)

    total = Decimal(0)
    for val in values:
        try:
            total += Decimal(str(val))
        except (ValueError, TypeError):
            continue
    return total


def create_calculated_items(report, column, value):
    """
    Hisoblangan natijalarni ReportItem va ReportItemInner orqali saqlaydi.
    """
    item = ReportItem.objects.create(
        report=report,
        statement_column=column
    )
    ReportItemInner.objects.create(
        report_item=item,
        value=str(value)
    )