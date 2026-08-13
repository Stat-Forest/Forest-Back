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

from apps.reports.models import Plant, StatementColumn
from apps.reports.services.plan_columns import get_plan_input_columns

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="4472C4")
ID_ROW = 2
HEADER_ROW = 1


def _column_title(column, lang):
    return getattr(column, f"title_{lang}", column.title_uz) or column.title_uz


# Guruh yorlig'i sifatida ishlatiladigan parent title uchun maksimal uzunlik.
# Undan uzun sarlavhalar — bu statement'ning tavsifiy (uzun) sarlavha
# ustunlari (masalan "...2026-yilda tayyorlanadigan urug'larni...") bo'lib,
# ular har bir ustunda takrorlanadi va ajratuvchi ma'lumot bermaydi.
MAX_LABEL_PART_LEN = 40


def _full_column_label(column, lang, max_ancestors=2):
    """
    Ustun uchun ajratuvchi (parent ierarxiyasi + leaf) sarlavha.

    Ko'p statement'larda leaf ustun nomi bir xil ("Reja") bo'ladi — masalan
    Daromad'da 12 ta oy ustuni ham "Reja" deb nomlangan. Faqat leaf title'ni
    header qilib qo'ysak, foydalanuvchi qaysi ustun qaysi oyga tegishli
    ekanini ajrata olmaydi.

    Shu sababli leaf'ga eng yaqin qisqa guruh yorliqlarini (chorak, oy,
    kategoriya) qo'shamiz — masalan "1-chorak - Yanvar - Reja". Uzun tavsifiy
    parent sarlavhalar (statement header ustunlari) tashlab yuboriladi, chunki
    ular ajratuvchi emas va sarlavhani o'qib bo'lmas darajada uzun qiladi.
    """
    ancestors = []
    node = getattr(column, "parent", None)
    while node is not None:
        title = _column_title(node, lang)
        if title and len(title) <= MAX_LABEL_PART_LEN:
            ancestors.append(title)
        node = getattr(node, "parent", None)
    # leaf'ga eng yaqin `max_ancestors` ta qisqa yorliqni olamiz
    nearest = ancestors[:max_ancestors]
    nearest.reverse()
    nearest.append(_column_title(column, lang))
    return " - ".join(part for part in nearest if part)


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
        cell = ws.cell(row=HEADER_ROW, column=col_offset + i, value=_full_column_label(column, lang))
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


def _ordering_sort_key(column):
    """`ordering` maydonini ("1.3.2.1") raqamli tuple sifatida saralaydi —
    string sort ko'p raqamli segmentlarni ("1.10" vs "1.3") noto'g'ri
    tartiblamasligi uchun."""
    parts = []
    for seg in str(getattr(column, "ordering", "") or "0").split("."):
        try:
            parts.append(int(seg))
        except ValueError:
            parts.append(0)
    return parts


def _export_columns(statement):
    """Eksport uchun ustunlar — foydalanuvchi kiritadigan (oylik) VA hisoblangan
    (chorak / yillik / jami) barcha status_plan leaf ustunlari, reja tartibida."""
    columns = list(
        StatementColumn.objects.filter(
            statement=statement,
            parent__isnull=False,
            status_plan__isnull=False,
        ).select_related(
            "parent", "parent__parent", "parent__parent__parent",
            "parent__parent__parent__parent",
        )
    )
    columns.sort(key=_ordering_sort_key)
    return columns


def build_plan_export(plan, lang="uz"):
    """
    Yaratilgan Plan'ni to'ldirilgan (o'qish uchun) .xlsx sifatida quradi.

    Layout:
      - use_plant_plan=False -> 1-qator sarlavha, 2-qator qiymatlar.
      - use_plant_plan=True  -> har bir plant uchun bitta qator (A: plant nomi),
        ustunlarda shu plant uchun qiymatlar.

    Ustunlar to'liq breakdown: foydalanuvchi kiritgan oylik qiymatlar hamda
    ular asosida hisoblangan chorak / yillik / jami ustunlari ham ko'rsatiladi.
    """
    statement = plan.statement
    columns = _export_columns(statement)
    if not columns:
        raise ValueError(
            "Bu reja uchun ustunlar topilmadi (status_plan sozlanmagan bo'lishi mumkin)."
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reja"

    is_plant_plan = bool(getattr(statement, "use_plant_plan", False))
    col_offset = 2 if is_plant_plan else 1

    if is_plant_plan:
        c = ws.cell(row=HEADER_ROW, column=1, value="O'simlik nomi")
        c.font = HEADER_FONT
        c.fill = HEADER_FILL

    for i, column in enumerate(columns):
        cell = ws.cell(row=HEADER_ROW, column=col_offset + i, value=_full_column_label(column, lang))
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")

    if is_plant_plan:
        row = 2
        plant_plans = (
            plan.plant_plans
            .select_related("plant")
            .prefetch_related("items")
            .all()
        )
        for pp in plant_plans:
            ws.cell(row=row, column=1, value=pp.plant.name)
            values = {item.column_id: item.plan_value for item in pp.items.all()}
            for i, column in enumerate(columns):
                value = values.get(column.id)
                if value is not None:
                    ws.cell(row=row, column=col_offset + i, value=float(value))
            row += 1
        if row == 2:
            ws.cell(row=2, column=1, value="(rejaga o'simlik kiritilmagan)")
    else:
        values = {item.column_id: item.plan_value for item in plan.plan_items.all()}
        for i, column in enumerate(columns):
            value = values.get(column.id)
            if value is not None:
                ws.cell(row=2, column=col_offset + i, value=float(value))

    total_cols = col_offset + len(columns) - 1
    for i in range(1, total_cols + 1):
        ws.column_dimensions[get_column_letter(i)].width = 20 if i >= col_offset else 26

    ws.freeze_panes = "A2"
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