from decimal import Decimal
from django.db import transaction
from apps.reports.models import ReportItem, ReportItemInner


def normalize(value):
    try:
        return Decimal(str(value)) if value is not None else Decimal(0)
    except:
        return Decimal(0)


@transaction.atomic
def calculate_jamgarma(report):
    """
    Jamg‘arma hisoboti hisoblash funksiyasi (ordering asosida):
    - Foydalanuvchi quyidagilarni kiritadi: Jami tushum, To‘lanishi kerak, To‘landi
    - Qoldiq = To‘lanishi kerak - To‘landi (hisoblanadi)
    - Yakuniy umumiy blok avtomatik hisoblanadi
    """

    statement = report.statement
    columns = {col.ordering: col for col in statement.columns.all()}

    # Income orderings: 1.1.3 -> 1.1.8
    income_base_orderings = [f"1.1.{i}" for i in range(3, 9)]

    total_tushum = Decimal(0)
    total_tolanishi_kerak = Decimal(0)
    total_tolandi = Decimal(0)

    for base_ord in income_base_orderings:
        jami_tushum_col = columns.get(f"{base_ord}.1")
        tol_kerak_col = columns.get(f"{base_ord}.2.1")
        tolandi_col = columns.get(f"{base_ord}.2.2")
        qoldiq_col = columns.get(f"{base_ord}.2.3")

        tol_kerak_val = get_value(report, tol_kerak_col)
        tolandi_val = get_value(report, tolandi_col)
        jami_tushum_val = get_value(report, jami_tushum_col)

        if jami_tushum_val == 0:
            jami_tushum_val = tol_kerak_val

        total_tushum += normalize(jami_tushum_val)
        total_tolanishi_kerak += normalize(tol_kerak_val)
        total_tolandi += normalize(tolandi_val)

        qoldiq_val = normalize(tol_kerak_val) - normalize(tolandi_val)

        create_item(report, jami_tushum_col, jami_tushum_val)
        create_item(report, qoldiq_col, qoldiq_val)

    jamg_jami_tushum = columns.get("1.1.9.1")
    create_item(report, jamg_jami_tushum, total_tushum)

    # Umumiy blok (ordering: 1.1.9.2.1 - 1.1.9.2.3)
    jamg_tushum_col = columns.get("1.1.9.2.1")
    jamg_tolandi_col = columns.get("1.1.9.2.2")
    jamg_qoldiq_col = columns.get("1.1.9.2.3")

    create_item(report, jamg_tushum_col, total_tolanishi_kerak)
    create_item(report, jamg_tolandi_col, total_tolandi)
    create_item(report, jamg_qoldiq_col, total_tolanishi_kerak - total_tolandi)


def get_value(report, column):
    if not column:
        return Decimal(0)
    item = ReportItem.objects.filter(report=report, statement_column=column).first()
    if not item:
        return Decimal(0)
    inner = item.inners.first()
    return normalize(inner.value) if inner else Decimal(0)


def create_item(report, column, value):
    if not column:
        return
    item = ReportItem.objects.create(report=report, statement_column=column)
    ReportItemInner.objects.create(report_item=item, value=str(value))