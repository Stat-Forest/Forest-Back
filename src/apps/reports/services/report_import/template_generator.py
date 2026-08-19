# apps/reports/services/report_import/template_generator.py
"""
"Amalda" qiymatlar importi uchun Excel (.xlsx) shablon yaratish.

Shablonda:
    Row 1..N — ko'p qatorli sarlavhalar (merged cells — jadval tuzilmasiga mos)
    Row N+1  — (yashirin) StatementColumn UUID'lari (faqat importable)
    Row N+2+ — foydalanuvchi qiymat yozadigan qatorlar

Reja (status_plan berilgan) ustunlar shablonga UMUMAN kiritilmaydi —
na sarlavhada, na data zonasida ko'rinmaydi. Tashkilot nomi ustuni
ham shablonga kiritilmaydi — foydalanuvchi saytda tashkilotni allaqachon
tanlagan bo'ladi. UUID qatoriga faqat importable ustunlar tushadi —
shu orqali parser qaysi ustunlarni o'qish kerakligini biladi.

Plantlik statement uchun:
    Col A  — O'simlik nomi / Daromad manbalari (foydalanuvchi o'zi yozadi)
    Col B+ — Leaf ustunlar (importable = ko'k, avto-hisob = kulrang)

Oddiy statement uchun:
    Col A+ — Leaf ustunlar (importable = ko'k, avto-hisob = kulrang)
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, Protection
from openpyxl.utils import get_column_letter

from apps.reports.models import Plant, StatementColumn
from apps.reports.services.report_import.columns import (
    StatementColumnIndex,
    is_plant_based_statement,
    ordering_key,
)

# ── Stillar ──
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
HEADER_FILL = PatternFill("solid", fgColor="4472C4")  # Ko'k — importable
HEADER_ALIGNMENT = Alignment(wrap_text=True, vertical="center", horizontal="center")

# Reja/avto-hisob ustunlar uchun — kulrang sarlavha
READONLY_HEADER_FILL = PatternFill("solid", fgColor="808080")
READONLY_DATA_FILL = PatternFill("solid", fgColor="D9D9D9")

THIN_BORDER = Border(
    left=Side(style="thin", color="000000"),
    right=Side(style="thin", color="000000"),
    top=Side(style="thin", color="000000"),
    bottom=Side(style="thin", color="000000"),
)

HEADER_START_ROW = 1


def _ordering_key(ordering_str):
    """'1.1.10' → (1, 1, 10) — matn sifatida emas, son sifatida saralash."""
    return ordering_key(ordering_str)


def _get_all_visible_leaf_ids(statement):
    """
    Statement uchun shablonda ko'rsatiladigan leaf ustun ID'larini qaytaradi.

    Chiqarib tashlanadi:
        - is_organization=True bo'lgan ustunlar (tashkilot ustunlari)
        - is_user_input=False bo'lgan ustunlar (avto-hisob ustunlari)
        - status_plan berilgan ustunlar (reja ustunlari)
    """
    all_cols = list(
        StatementColumn.objects.filter(statement=statement)
        .select_related("parent")
        .order_by("ordering")
    )
    # Leaf = bolalari bo'lmagan
    all_ids = {str(c.id) for c in all_cols}
    parent_ids = {str(c.parent_id) for c in all_cols if c.parent_id}
    leaf_ids = all_ids - parent_ids

    # Filtrlash: faqat is_user_input=True, is_organization=False,
    # status_plan=null (reja emas) bo'lgan leaf ustunlar
    result = set()
    for c in all_cols:
        if (
            str(c.id) in leaf_ids
            and not getattr(c, "is_organization", False)
            and getattr(c, "is_user_input", True)  # Avto-hisob ustunlarini chiqarib tashlaymiz
            and not c.status_plan  # Reja ustunlarini chiqarib tashlaymiz
        ):
            result.add(str(c.id))
    return result


def _build_column_tree(statement, visible_leaf_ids, lang="uz"):
    """
    Statement ustunlari daraxtini qurib, sarlavha yaratish uchun kerakli
    ma'lumotlarni qaytaradi.

    visible_leaf_ids — shablonda ko'rsatiladigan BARCHA leaf ustun ID'lari
    (importable + reja + avto-hisob, ORG dan tashqari).

    Returns:
        (roots, children_map, leaf_ids, id_map)
    """
    all_cols = list(
        StatementColumn.objects.filter(statement=statement)
        .select_related("parent")
        .order_by("ordering")
    )
    id_map = {str(c.id): c for c in all_cols}

    # Leaf ustunlarning barcha ota-onalarini topish
    included_ids = set(visible_leaf_ids)
    for cid in list(visible_leaf_ids):
        cur = id_map.get(cid)
        while cur and cur.parent_id:
            included_ids.add(str(cur.parent_id))
            cur = id_map.get(str(cur.parent_id))

    # Children xaritasi — faqat kerakli ustunlar
    children_map = {}
    for cid in included_ids:
        c = id_map.get(cid)
        if not c:
            continue
        # is_organization ustunlarni olib tashlaymiz
        if getattr(c, "is_organization", False):
            continue
        parent_key = str(c.parent_id) if c.parent_id else None
        children_map.setdefault(parent_key, []).append(c)

    for k in children_map:
        children_map[k].sort(key=lambda x: _ordering_key(x.ordering or ""))

    roots = children_map.get(None, [])

    def dfs(node):
        ch = children_map.get(str(node.id), [])
        if not ch:
            return [node] if str(node.id) in visible_leaf_ids else []
        return [x for c in ch for x in dfs(c)]

    leaf_ids = []
    for root in roots:
        leaf_ids.extend(str(c.id) for c in dfs(root))

    return roots, children_map, leaf_ids, id_map


def _compute_depth(node, children_map):
    """Daraxt chuqurligi."""
    ch = children_map.get(str(node.id), [])
    return 1 if not ch else 1 + max(_compute_depth(c, children_map) for c in ch)


def _compute_span(node, children_map, span_cache):
    """Node ning qancha leaf ustunni qamrab olishi."""
    if node.id in span_cache:
        return span_cache[node.id]
    ch = children_map.get(str(node.id), [])
    result = 1 if not ch else sum(
        _compute_span(c, children_map, span_cache) for c in ch
    )
    span_cache[node.id] = result
    return result


def _title_of(column, lang):
    """Ustun sarlavhasini tanlangan tilda qaytaradi."""
    if lang == "ru":
        return column.title_ru or column.title_uz or column.title or ""
    return column.title_uz or column.title or ""


def build_import_template(statement, lang="uz"):
    """
    Statement uchun import shablonini (.xlsx Workbook) quradi.

    Reja (status_plan berilgan) ustunlar shablonga kiritilmaydi.
    Tashkilot nomi ustuni ham shablonga kiritilmaydi — foydalanuvchi
    saytda tashkilotni allaqachon tanlagan bo'ladi.

    Plantlik jadvalda bitta fixed ustun bo'ladi (O'simlik nomi /
    Daromad manbalari), oddiy jadvalda fixed ustun yo'q.

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

    importable_ids = {str(c.id) for c in columns}
    is_plant_based = is_plant_based_statement(statement)

    # Barcha ko'rinadigan leaf ustunlar (ORG dan tashqari)
    all_visible_ids = _get_all_visible_leaf_ids(statement)

    # Ustun daraxtini qurish — BARCHA ko'rinadigan leaf ustunlar
    roots, children_map, leaf_ids, id_map = _build_column_tree(
        statement, all_visible_ids, lang=lang
    )

    if not roots:
        raise ValueError("Jadval tuzilmasi topilmadi.")

    wb = openpyxl.Workbook()
    ws = wb.active

    # Sheet nomini statement nomidan olamiz (max 31 belgi — Excel limiti)
    sheet_title = getattr(statement, f"name_{lang}", statement.name) or statement.name
    ws.title = sheet_title[:31]

    # ── Sarlavha tuzilmasi ──
    # Plantlik jadvalda: O'simlik nomi / Daromad manbalari — 1 ta fixed ustun
    # Oddiy jadvalda: fixed ustun yo'q
    fixed_cols = 1 if is_plant_based else 0

    # Daraxt chuqurligi — har bir root uchun alohida
    max_depth = max(_compute_depth(root, children_map) for root in roots)
    total_leaf_count = len(leaf_ids)
    total_cols = fixed_cols + total_leaf_count

    # Sarlavha grid'ini yaratish
    header_grid = [["" for _ in range(total_cols)] for _ in range(max_depth)]

    # Fixed ustunlar sarlavhalari (faqat plantlik jadvalda)
    if is_plant_based:
        # Daromad statementda "Daromad manbalari" sarlavhasi ishlatiladi
        stmt_name = (statement.name_uz or statement.name or "").lower()
        if "daromad" in stmt_name:
            header_grid[0][0] = "Daromad manbalari" if lang == "uz" else "Источники дохода"
        else:
            header_grid[0][0] = "O'simlik nomi" if lang == "uz" else "Название растения"

    span_cache = {}
    merges = []

    def place(node, level, col):
        """Daraxt node'ini header_grid'ga joylashtiradi va merge diapazoni qo'shadi."""
        header_grid[level][col] = _title_of(node, lang)
        sp = _compute_span(node, children_map, span_cache)
        ch = children_map.get(str(node.id), [])

        if not ch:
            # Leaf ustun — pastki qatorgacha vertikal merge
            if level < max_depth - 1:
                merges.append((
                    HEADER_START_ROW + level, col + 1,
                    HEADER_START_ROW + max_depth - 1, col + 1,
                ))
            return col + 1

        # Guruh ustun — gorizontal merge
        merges.append((
            HEADER_START_ROW + level, col + 1,
            HEADER_START_ROW + level, col + sp,
        ))

        cur = col
        for c in ch:
            cur = place(c, level + 1, cur)
        return col + sp

    # Har bir root uchun joylashtirish
    current_col = fixed_cols
    for root in roots:
        current_col = place(root, 0, current_col)

    # Grid'ni worksheetga yozish
    for row_data in header_grid:
        ws.append(row_data)

    # Fixed ustunlarni vertikal merge qilish
    for fixed_col in range(1, fixed_cols + 1):
        if max_depth > 1:
            ws.merge_cells(
                start_row=HEADER_START_ROW, start_column=fixed_col,
                end_row=HEADER_START_ROW + max_depth - 1, end_column=fixed_col,
            )

    # Merge diapasonlarini qo'llash
    for r1, c1, r2, c2 in merges:
        ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)

    # ── Sarlavha stili ──
    # Avval barcha sarlavha kataklariga default stil beramiz
    for row in ws.iter_rows(
        min_row=HEADER_START_ROW, max_row=HEADER_START_ROW + max_depth - 1,
        min_col=1, max_col=total_cols,
    ):
        for cell in row:
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = HEADER_ALIGNMENT
            cell.border = THIN_BORDER

    # Avto-hisob ustunlarning sarlavhalarini kulrang qilish
    # Leaf ustunning Excel ustun indeksini aniqlash
    readonly_excel_cols = set()
    for i, leaf_id in enumerate(leaf_ids):
        if leaf_id not in importable_ids:
            excel_col = fixed_cols + 1 + i
            readonly_excel_cols.add(excel_col)

    # Kulrang sarlavha — faqat leaf ustunning o'ziga va
    # uning ustidagi sarlavha kataklariga (agar barchasi readonly bo'lsa)
    for excel_col in readonly_excel_cols:
        for row in range(HEADER_START_ROW, HEADER_START_ROW + max_depth):
            cell = ws.cell(row=row, column=excel_col)
            cell.fill = READONLY_HEADER_FILL

    # ── UUID qatori (sarlavhalardan keyin, yashirin + ko'rinmas) ──
    # FAQAT importable ustunlar uchun UUID yoziladi
    id_row = HEADER_START_ROW + max_depth
    uuid_font = Font(color="FFFFFF", size=1)
    for i, leaf_id in enumerate(leaf_ids):
        excel_col = fixed_cols + 1 + i
        if leaf_id in importable_ids:
            cell = ws.cell(row=id_row, column=excel_col, value=leaf_id)
            cell.font = uuid_font

    ws.row_dimensions[id_row].hidden = True
    ws.row_dimensions[id_row].height = 0.1

    # ── Data start row ──
    data_start_row = id_row + 1

    # ── Plantlik jadvalda — barcha leaf plantlarni data qatorlariga yozish ──
    leaf_plants = []
    if is_plant_based:
        leaf_plants = list(
            Plant.objects.filter(
                statement=statement,
                children__isnull=True,  # faqat leaf plantlar
            ).order_by("name")
        )
        plant_name_font = Font(size=11)
        plant_name_alignment = Alignment(vertical="center")
        for plant_idx, plant in enumerate(leaf_plants):
            row_num = data_start_row + plant_idx
            # Tilga qarab plant nomini tanlash
            plant_name = (
                getattr(plant, f"name_{lang}", None) or plant.name or ""
            )
            cell = ws.cell(row=row_num, column=1, value=plant_name)
            cell.font = plant_name_font
            cell.alignment = plant_name_alignment
            cell.border = THIN_BORDER

    # ── Readonly ustunlar data zonasida kulrang fon ──
    # Dastlabki 20 qatorga (yoki plant soni qadar) kulrang fon qo'yamiz
    data_row_count = max(20, len(leaf_plants))
    for excel_col in readonly_excel_cols:
        for data_row in range(data_start_row, data_start_row + data_row_count):
            cell = ws.cell(row=data_row, column=excel_col)
            cell.fill = READONLY_DATA_FILL

    # ── Ustun kengliklari ──
    # Fixed ustunlar uchun kenglikni eng uzun text asosida hisoblaymiz
    if fixed_cols > 0:
        max_text_len = 0
        # Sarlavha textlarini tekshirish
        for row_idx in range(max_depth):
            for fc in range(fixed_cols):
                text = header_grid[row_idx][fc]
                if text:
                    max_text_len = max(max_text_len, len(str(text)))
        # Data zonasidagi textlarni tekshirish (plant nomlari va h.k.)
        for fc in range(1, fixed_cols + 1):
            for data_row in range(data_start_row, data_start_row + len(leaf_plants)):
                cell_val = ws.cell(row=data_row, column=fc).value
                if cell_val:
                    max_text_len = max(max_text_len, len(str(cell_val)))
        # Kenglik: har bir belgi uchun ~1.2, minimal 20, +4 padding
        fixed_col_width = max(20, max_text_len * 1.2 + 4)
        for fc in range(1, fixed_cols + 1):
            letter = get_column_letter(fc)
            ws.column_dimensions[letter].width = fixed_col_width

    # Statement ustunlari uchun standart kenglik
    for i in range(fixed_cols + 1, total_cols + 1):
        letter = get_column_letter(i)
        ws.column_dimensions[letter].width = 22

    # Sarlavha va ID qatorlarini muzlatib qo'yamiz
    ws.freeze_panes = f"A{data_start_row}"

    return wb
