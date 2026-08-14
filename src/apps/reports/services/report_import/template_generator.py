# apps/reports/services/report_import/template_generator.py
"""
"Amalda" qiymatlar importi uchun Excel (.xlsx) shablon yaratish.

Shablonda:
    Row 1  — ustun sarlavhalari (faqat Amalda)
    Row 2  — (yashirin) StatementColumn UUID'lari
    Row 3+ — foydalanuvchi qiymat yozadigan qatorlar

Plantlik statement uchun qo'shimcha:
    Col A  — Plant ID (o'zgartirmang)
    Col B  — O'simlik nomi (faqat o'qish)
    Col C+ — Amalda ustunlar
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Protection
from openpyxl.utils import get_column_letter

from apps.reports.models import Plant
from apps.reports.services.report_import.columns import StatementColumnIndex

HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
HEADER_FILL = PatternFill("solid", fgColor="4472C4")
HEADER_ALIGNMENT = Alignment(wrap_text=True, vertical="center", horizontal="center")

PLANT_LABEL_FONT = Font(italic=True, color="333333")

HEADER_ROW = 1
ID_ROW = 2
DATA_START_ROW = 3


def build_import_template(statement, lang="uz"):
    """
    Statement uchun import shablonini (.xlsx Workbook) quradi.

    Returns:
        openpyxl.Workbook
    Raises:
        ValueError — agar to'ldiriladigan Amalda ustunlar topilmasa.
    """
    index = StatementColumnIndex(statement, lang=lang)
    columns = index.importable
    if not columns:
        raise ValueError(
            "Bu statement uchun import qilinadigan ustunlar topilmadi "
            "(barcha oxirgi ustunlar reja yoki avto-hisob sifatida belgilangan)."
        )

    is_plant_based = bool(getattr(statement, "use_plant_plan", False))

    wb = openpyxl.Workbook()
    ws = wb.active

    # Sheet nomini statement nomidan olamiz (max 31 belgi — Excel limiti)
    sheet_title = getattr(statement, f"name_{lang}", statement.name) or statement.name
    ws.title = sheet_title[:31]

    # Plantlik bo'lsa, A va B ustunlar Plant uchun ajratiladi
    col_offset = 3 if is_plant_based else 1

    # ── Plant sarlavhalari (faqat plantlik) ──
    if is_plant_based:
        for idx, label in enumerate(
            ("Plant ID (o'zgartirmang)", "O'simlik nomi"),
            start=1,
        ):
            cell = ws.cell(row=HEADER_ROW, column=idx, value=label)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = HEADER_ALIGNMENT

    # ── Amalda ustun sarlavhalari ──
    # Sarlavha — statement ichida yagona bo'lishi kafolatlangan nom
    # ("Amalda" 12 ta bo'lsa → "Yanvar » Amalda"). Yashirin UUID qatori
    # o'chib ketsa ham, parser shu nom bo'yicha to'g'ri ustunni topadi.
    for i, column in enumerate(columns):
        cell = ws.cell(
            row=HEADER_ROW,
            column=col_offset + i,
            value=index.label(column),
        )
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT

        # Yashirin qatorda UUID saqlaymiz
        ws.cell(row=ID_ROW, column=col_offset + i, value=str(column.id))

    # ID qatorini yashiramiz
    ws.row_dimensions[ID_ROW].hidden = True

    # ── Plantlik: leaf o'simliklarni qatorlarga yozish ──
    if is_plant_based:
        plants = (
            Plant.objects
            .filter(statement=statement, children__isnull=True)
            .order_by("name")
        )
        row = DATA_START_ROW
        for plant in plants:
            ws.cell(row=row, column=1, value=str(plant.id))
            plant_name = getattr(plant, f"name_{lang}", plant.name) or plant.name
            name_cell = ws.cell(row=row, column=2, value=plant_name)
            name_cell.font = PLANT_LABEL_FONT
            name_cell.protection = Protection(locked=True)
            row += 1

        if row == DATA_START_ROW:
            ws.cell(
                row=DATA_START_ROW,
                column=2,
                value="(o'simliklar topilmadi)",
            )

    # ── Ustun kengliklari ──
    total_cols = col_offset + len(columns)
    for i in range(1, total_cols + 1):
        letter = get_column_letter(i)
        if is_plant_based and i <= 2:
            ws.column_dimensions[letter].width = 28
        else:
            ws.column_dimensions[letter].width = 22

    # Sarlavha va ID qatorlarini muzlatib qo'yamiz
    ws.freeze_panes = f"A{DATA_START_ROW}"

    return wb
