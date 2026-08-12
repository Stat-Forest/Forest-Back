# apps/reports/services/plan_excel.py
"""
Reja (Plan) uchun Excel shablon yaratish va yuklangan Excel faylni
PlanSerializer input formatiga o'girish.

Dizayn qarori:
    Har bir ustun sarlavhasi ostida (2-QATOR, yashirilgan) shu ustunning
    StatementColumn UUID'i saqlanadi. Import paytida sarlavha MATNIGA emas,
    aynan shu UUID'ga qarab column aniqlanadi. Shu sababli:
      - foydalanuvchi sarlavha matnini bir oz o'zgartirib qo'ysa ham import
        buzilmaydi;
      - uz/ru sarlavhalar orasidagi farq muammo tug'dirmaydi;
      - bir xil nomli (lekin turli statement/parent'ga tegishli) ustunlar
        aralashib ketmaydi.

Foydalanuvchi 2-qatorni o'chirib yubormasligi kerak — shuning uchun u
`hidden` qilib qo'yiladi, lekin fayldan butunlay olib tashlanmaydi.
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from apps.reports.models import Plant
from apps.reports.services.plan_columns import get_plan_input_columns

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="4472C4")
ID_ROW = 2
HEADER_ROW = 1


def _column_title(column, lang):
    return getattr(column, f"title_{lang}", column.title_uz) or column.title_uz


def build_plan_template(statement, lang="uz"):
    """
    Statement uchun to'ldirish shablonini (.xlsx, openpyxl Workbook) quradi.

    - use_plant_plan=False bo'lsa: 1 ta ma'lumot qatori (3-qator), har bir
      ustun uchun bitta katak.
    - use_plant_plan=True bo'lsa: har bir leaf Plant uchun bitta qator
      (3-qatordan boshlab), A ustunida Plant ID (o'chirilmasin), B ustunida
      o'simlik nomi (faqat o'qish uchun, import paytida ishlatilmaydi).
    """
    columns = list(get_plan_input_columns(statement))
    if not columns:
        raise ValueError(
            "Bu statement uchun to'ldiriladigan ustunlar topilmadi "
            "(status_plan sozlanmagan bo'lishi mumkin)."
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reja"

    is_plant_plan = bool(getattr(statement, "use_plant_plan", False))
    col_offset = 3 if is_plant_plan else 1

    if is_plant_plan:
        for idx, label in enumerate(("Plant ID (o'zgartirmang)", "O'simlik nomi"), start=1):
            c = ws.cell(row=HEADER_ROW, column=idx, value=label)
            c.font = HEADER_FONT
            c.fill = HEADER_FILL

    for i, column in enumerate(columns):
        cell = ws.cell(row=HEADER_ROW, column=col_offset + i, value=_column_title(column, lang))
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.cell(row=ID_ROW, column=col_offset + i, value=str(column.id))

    ws.row_dimensions[ID_ROW].hidden = True

    if is_plant_plan:
        plants = (
            Plant.objects.filter(statement=statement, children__isnull=True)
            .order_by("name")
        )
        row = 3
        for plant in plants:
            ws.cell(row=row, column=1, value=str(plant.id))
            ws.cell(row=row, column=2, value=plant.name)
            row += 1
        if row == 3:
            # Statement'ga bog'liq leaf plant topilmadi — bo'sh qator qoldiramiz
            ws.cell(row=3, column=2, value="(o'simliklar topilmadi)")
    else:
        # Yagona ma'lumot qatori uchun joy
        ws.cell(row=3, column=1, value=None)

    total_cols = col_offset + len(columns)
    for i in range(1, total_cols + 1):
        ws.column_dimensions[get_column_letter(i)].width = 20 if i > col_offset - 1 else 26

    ws.freeze_panes = "A3"
    return wb


def parse_plan_excel(file_obj, statement):
    """
    Yuklangan Excel faylni o'qib, PlanSerializer ga mos payload qaytaradi:
        - use_plant_plan=False -> {"plan_items": [{"column": <uuid>, "plan_value": <num>}, ...]}
        - use_plant_plan=True  -> {"plants": [{"plant": <uuid>, "items": [...]}, ...]}

    Bo'sh kataklar e'tiborga olinmaydi (0 sifatida emas — umuman yuborilmaydi).
    """
    try:
        wb = openpyxl.load_workbook(file_obj, data_only=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Fayl noto'g'ri formatda: {exc}")

    ws = wb.active
    is_plant_plan = bool(getattr(statement, "use_plant_plan", False))
    col_offset = 3 if is_plant_plan else 1

    id_row_cells = ws[ID_ROW] if ws.max_row >= ID_ROW else []
    column_ids = {}
    for cell in id_row_cells:
        if cell.column < col_offset:
            continue
        if cell.value:
            column_ids[cell.column] = str(cell.value).strip()

    if not column_ids:
        raise ValueError(
            "Shablon noto'g'ri: ustun ID'lari topilmadi. "
            "Iltimos, ushbu statement uchun tizimdan yuklab olingan shablondan foydalaning."
        )

    def _row_items(row_cells):
        items = []
        for cell in row_cells:
            if cell.column < col_offset:
                continue
            col_id = column_ids.get(cell.column)
            if not col_id:
                continue
            value = cell.value
            if value in (None, ""):
                continue
            items.append({"column": col_id, "plan_value": value})
        return items

    if is_plant_plan:
        plants_payload = []
        for row_cells in ws.iter_rows(min_row=3):
            plant_id = row_cells[0].value if row_cells else None
            if not plant_id:
                continue
            items = _row_items(row_cells)
            if items:
                plants_payload.append({"plant": str(plant_id).strip(), "items": items})

        if not plants_payload:
            raise ValueError("Faylda hech qanday o'simlik uchun qiymat topilmadi.")

        return {"plants": plants_payload}

    if ws.max_row < 3:
        raise ValueError("Faylda ma'lumot qatori (3-qator) topilmadi.")

    items = _row_items(ws[3])
    if not items:
        raise ValueError("Faylda hech qanday qiymat topilmadi.")

    return {"plan_items": items}