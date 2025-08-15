import unicodedata
from decimal import Decimal
from apps.reports.models import ReportItem, ReportItemInner
from apps.utils.report_math import sum_values

TARGET_COLUMNS_UZ = [
    "Departament mudiri",
    "Boshqarma boshlig‘i",
    "Bo‘lim boshlig‘i",
    "Sho‘ba mudiri",
    "Mutaxassislar‑2"
]

TARGET_COLUMNS_RU = [
    "Начальник департамента",
    "Начальник управления",
    "Начальник отдела",
    "Начальник сектора",
    "Специалисты-2"
]


def normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = " ".join(text.split())
    return text.strip().lower()


def calculate_employee_analysis(report):
    statement = report.statement
    columns = statement.columns.prefetch_related("children").all()
    column_map = {col.ordering: col for col in columns}

    # -----------------------
    # Ilova-2 hisoblash (avvalgi qism)
    for col in columns:
        if normalize(col.title_uz) == "shu jumladan" or normalize(col.title_ru) == "в том числе":

            target_children = list(
                col.children.filter(title_uz__in=TARGET_COLUMNS_UZ) |
                col.children.filter(title_ru__in=TARGET_COLUMNS_RU)
            )

            if not target_children:
                continue

            total_value = sum_values(report, target_children)

            if col.parent:
                jami_col = col.parent.children.filter(title_uz__iexact="jami").first() \
                    or col.parent.children.filter(title_ru__iexact="всего").first()

                if jami_col:
                    upsert_calculated_item(report, jami_col, total_value)

    # -----------------------
    # Ilova-3 — Hisoblash 1
    col_oliy_jami = column_map.get("1.6.1.2.2.1.1")
    col_orta_maxsus_jami = column_map.get("1.6.1.2.2.2.1")
    col_orta = column_map.get("1.6.1.2.2.3")
    col_jami_target = column_map.get("1.6.1.2.1")

    if col_jami_target:
        total = Decimal(0)
        for col in [col_oliy_jami, col_orta_maxsus_jami, col_orta]:
            if col:
                total += Decimal(sum_values(report, [col]))
        upsert_calculated_item(report, col_jami_target, total)

    year_orderings = [
        "1.6.1.6.2.1.1", "1.6.1.6.2.1.2", "1.6.1.6.2.1.3",
        "1.6.1.6.2.2.1", "1.6.1.6.2.2.2", "1.6.1.6.2.2.3",
        "1.6.1.6.2.3.1", "1.6.1.6.2.3.2", "1.6.1.6.2.3.3",
    ]
    col_jami_years = column_map.get("1.6.1.6.1")
    if col_jami_years:
        total = Decimal(0)
        for ordering in year_orderings:
            col = column_map.get(ordering)
            if col:
                total += Decimal(sum_values(report, [col]))
        upsert_calculated_item(report, col_jami_years, total)


def upsert_calculated_item(report, column, value):
    """
    Bor bo‘lsa yangilaydi, bo‘lmasa qo‘shadi.
    """
    item, _ = ReportItem.objects.get_or_create(
        report=report,
        statement_column=column
    )

    inner = item.inners.first()
    if inner:
        inner.value = str(value)
        inner.save(update_fields=["value"])
    else:
        ReportItemInner.objects.create(
            report_item=item,
            value=str(value)
        )
