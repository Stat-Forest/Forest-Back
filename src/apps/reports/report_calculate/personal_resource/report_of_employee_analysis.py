import unicodedata
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

    for col in columns:
        if normalize(col.title_uz) == "shu jumladan" or normalize(col.title_ru) == "в том числе":

            target_children = list(
                col.children.filter(
                    title_uz__in=TARGET_COLUMNS_UZ
                ) | col.children.filter(
                    title_ru__in=TARGET_COLUMNS_RU
                )
            )

            if not target_children:
                continue

            total_value = sum_values(report, target_children)

            if col.parent:
                jami_col = col.parent.children.filter(
                    title_uz__iexact="jami"
                ).first() or col.parent.children.filter(
                    title_ru__iexact="всего"
                ).first()

                if jami_col:
                    upsert_calculated_item(report, jami_col, total_value)


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
