import unicodedata
from decimal import Decimal
from apps.reports.models import ReportItem, ReportItemInner, StatementColumn
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


def upsert_calculated_item(report, column, value):
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


def get_column_by_ordering(columns: list[StatementColumn], ordering: str):
    for col in columns:
        if col.ordering == ordering:
            return col
    return None


def calculate_employee_analysis(report):
    statement = report.statement
    columns = list(statement.columns.prefetch_related("children").all())

    # 1. Umumiy to‘plamlar (shu jumladan -> Jami)
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

    # 2. Kasallik turlari
    KASALLIK_TARGETS = [
        "Yurak va qon tomir kasalliklari",
        "Asab kasalliklari",
        "Oshqozon-ichak kasalliklari"
    ]
    KASALLIK_TARGETS_RU = [
        "Болезни сердца и сосудов",
        "Нервные заболевания",
        "Желудочно-кишечные болезни"
    ]

    for col in columns:
        if normalize(col.title_uz) == "shu jumladan" or normalize(col.title_ru) == "в том числе":
            target_children = list(
                col.children.filter(title_uz__in=KASALLIK_TARGETS) |
                col.children.filter(title_ru__in=KASALLIK_TARGETS_RU)
            )
            if not target_children:
                continue

            total_value = sum_values(report, target_children)

            if col.parent:
                jami_col = col.parent.children.filter(title_uz__iexact="jami").first() \
                    or col.parent.children.filter(title_ru__iexact="всего").first()
                if jami_col:
                    upsert_calculated_item(report, jami_col, total_value)

    # 3. Madaniy-ma’rifiy tadbirlar
    MADANIY_TARGETS = ["Teatr", "Kino", "Konsert", "Boshqalar"]
    MADANIY_TARGETS_RU = ["Театр", "Кино", "Концерт", "Другие"]

    for col in columns:
        if normalize(col.title_uz) == "shu jumladan" or normalize(col.title_ru) == "в том числе":
            target_children = list(
                col.children.filter(title_uz__in=MADANIY_TARGETS) |
                col.children.filter(title_ru__in=MADANIY_TARGETS_RU)
            )
            if not target_children:
                continue

            total_value = sum_values(report, target_children)

            if col.parent:
                jami_col = col.parent.children.filter(title_uz__iexact="jami").first() \
                    or col.parent.children.filter(title_ru__iexact="всего").first()
                if jami_col:
                    upsert_calculated_item(report, jami_col, total_value)

    # 4. Ilova-3 — Hisoblash (ordering orqali)
    col_oliy_jami = get_column_by_ordering(columns, "6.1.2.2.1.1")
    col_orta_maxsus_jami = get_column_by_ordering(columns, "6.1.2.2.2.1")
    col_orta = get_column_by_ordering(columns, "6.1.2.2.3")
    col_jami_target = get_column_by_ordering(columns, "6.1.2.1")

    if col_jami_target:
        total = Decimal(0)
        for col in [col_oliy_jami, col_orta_maxsus_jami, col_orta]:
            if col:
                total += Decimal(sum_values(report, [col]))
        upsert_calculated_item(report, col_jami_target, total)

    # 5. Yillik bo‘yicha (3 yillik blok)
    year_orderings = [
        "6.1.6.2.1.1", "6.1.6.2.1.2", "6.1.6.2.1.3",  # Magister
        "6.1.6.2.2.1", "6.1.6.2.2.2", "6.1.6.2.2.3",  # Oliy
        "6.1.6.2.6.1", "6.1.6.2.6.2", "6.1.6.2.3.3",  # O‘rta-maxsus
    ]
    col_jami_years = get_column_by_ordering(columns, "6.1.6.1")
    if col_jami_years:
        total = Decimal(0)
        for ordering in year_orderings:
            col = get_column_by_ordering(columns, ordering)
            if col:
                total += Decimal(sum_values(report, [col]))
        upsert_calculated_item(report, col_jami_years, total)


# def upsert_calculated_item(report, column, value):
#     """
#     Bor bo‘lsa yangilaydi, bo‘lmasa qo‘shadi.
#     """
#     item, _ = ReportItem.objects.get_or_create(
#         report=report,
#         statement_column=column
#     )
#
#     inner = item.inners.first()
#     if inner:
#         inner.value = str(value)
#         inner.save(update_fields=["value"])
#     else:
#         ReportItemInner.objects.create(
#             report_item=item,
#             value=str(value)
#         )
