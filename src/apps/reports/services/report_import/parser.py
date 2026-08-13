# apps/reports/services/report_import/parser.py
"""
Yuklangan Excel (.xlsx) faylni parse qilib, frontend uchun
strukturalangan JSON payload qaytaradi.

DB ga hech narsa YOZILMAYDI — faqat o'qish va validatsiya.

Return formati (oddiy):
    {"status": "success"|"partial"|"error",
     "items": [{"column": "<uuid>", "value": "..."}, ...],
     "warnings": [...], "errors": [...]}

Return formati (plantlik):
    {"status": "success"|"partial"|"error",
     "plants": [{"plant": "<uuid>", "plant_name": "...",
                  "items": [{"column": "<uuid>", "value": "..."}, ...]}, ...],
     "warnings": [...], "errors": [...]}
"""

import openpyxl

from apps.reports.models import StatementColumn, Plant
from apps.reports.services.change_coma_to_dote import normalize_decimal_input_dote
from apps.reports.services.report_import.columns import get_importable_columns

HEADER_ROW = 1
ID_ROW = 2


def _build_column_id_map_from_uuid_row(ws, col_offset, amalda_ids):
    """
    Row 2 dagi yashirin UUID'lardan {excel_column_index: column_uuid_str} map quradi.
    Faqat Amalda ustunlarga tegishli UUID'lar olinadi.
    """
    column_map = {}
    id_row_cells = ws[ID_ROW] if ws.max_row >= ID_ROW else []
    for cell in id_row_cells:
        if cell.column < col_offset:
            continue
        raw = cell.value
        if raw is None or str(raw).strip() == "":
            continue
        uuid_str = str(raw).strip()
        if uuid_str in amalda_ids:
            column_map[cell.column] = uuid_str
    return column_map


def _build_column_id_map_from_titles(ws, col_offset, importable_columns, lang):
    """
    Fallback: sarlavha matniga qarab moslashtirish.
    Row 1..10 dagi sarlavhalar → importable_columns title_uz/title_ru bilan solishtirish.
    """
    # title → column id mapping (kichik harfda, stripped)
    title_to_id = {}
    for col in importable_columns:
        for field in ("title_uz", "title_ru"):
            t = getattr(col, field, None)
            if t:
                title_to_id[t.strip().lower()] = str(col.id)

    column_map = {}
    max_header_row = 1

    # Detect if this is an export file (starts with "№" and "Tashkilot nomi")
    actual_col_offset = col_offset
    cell_a1 = str(ws.cell(row=1, column=1).value or "").strip()
    cell_b1 = str(ws.cell(row=1, column=2).value or "").strip()
    cell_c1 = str(ws.cell(row=1, column=3).value or "").strip()
    
    if cell_a1 == "№" and cell_b1.lower() == "tashkilot nomi":
        if cell_c1.lower() in ["o'simlik nomi", "название растения"]:
            actual_col_offset = 4
        else:
            actual_col_offset = 3

    for row_idx in range(1, min(ws.max_row, 10) + 1):
        row_cells = ws[row_idx] if ws.max_row >= row_idx else []
        for cell in row_cells:
            if cell.column < actual_col_offset:
                continue
            if cell.column in column_map:
                continue

            raw = cell.value
            if raw is None:
                continue
            
            header_text = str(raw).strip().lower()
            col_id = title_to_id.get(header_text)
            if col_id:
                column_map[cell.column] = col_id
                if row_idx > max_header_row:
                    max_header_row = row_idx

    return column_map, max_header_row, actual_col_offset


def _extract_row_items(row_cells, col_offset, column_map, row_number, title_by_id, errors):
    """
    Bitta qatordagi katakchalardan {column, value} juftliklarini yig'adi.
    Bo'sh kataklarni o'tkazib yuboradi. Qiymatlarni normalize qiladi.
    """
    items = []
    for cell in row_cells:
        if cell.column < col_offset:
            continue
        col_id = column_map.get(cell.column)
        if not col_id:
            continue

        value = cell.value
        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue

        # Normalize (vergul → nuqta, whitespace tozalash)
        normalized = normalize_decimal_input_dote(value)
        if normalized is None:
            continue

        items.append({"column": col_id, "value": str(normalized)})

    return items


def parse_import_excel(file_obj, statement, sheet_name=None, lang="uz"):
    """
    Yuklangan Excel faylni o'qib, frontend uchun payload qaytaradi.

    Args:
        file_obj: InMemoryUploadedFile yoki file-like object
        statement: Statement model instance
        sheet_name: O'qiladigan sheet nomi (None bo'lsa active sheet)
        lang: Til kodi ("uz" yoki "ru")

    Returns:
        dict — response payload (status, items/plants, warnings, errors)

    Raises:
        ValueError — fayl formati noto'g'ri yoki o'qib bo'lmasa
    """
    # ── 1. Workbook ochish ──
    try:
        wb = openpyxl.load_workbook(file_obj, data_only=True)
    except Exception as exc:
        raise ValueError(f"Fayl noto'g'ri formatda yoki buzilgan: {exc}")

    # ── 2. Sheet tanlash ──
    if sheet_name:
        if sheet_name not in wb.sheetnames:
            raise ValueError(
                f"'{sheet_name}' nomli sheet topilmadi. "
                f"Mavjud sheetlar: {', '.join(wb.sheetnames)}"
            )
        ws = wb[sheet_name]
    else:
        ws = wb.active

    # ── 3. Import qilinadigan ustunlarni olish ──
    amalda_columns = list(get_importable_columns(statement))
    if not amalda_columns:
        raise ValueError(
            "Bu statement uchun import qilinadigan ustunlar topilmadi."
        )
    amalda_ids = {str(c.id) for c in amalda_columns}

    # title_by_id — xatolik xabarlarida ustun nomini ko'rsatish uchun
    title_by_id = {}
    for c in amalda_columns:
        title = getattr(c, f"title_{lang}", c.title_uz) or c.title_uz
        title_by_id[str(c.id)] = title

    is_plant_based = bool(getattr(statement, "use_plant_plan", False))
    col_offset = 3 if is_plant_based else 1

    # ── 4. Ustun moslashtirish ──
    data_start_row = 3
    column_map = _build_column_id_map_from_uuid_row(ws, col_offset, amalda_ids)

    warnings = []
    if not column_map:
        # UUID'lar topilmadi — sarlavha matniga fallback
        column_map, max_header_row, new_col_offset = _build_column_id_map_from_titles(ws, col_offset, amalda_columns, lang)
        if new_col_offset > col_offset:
            col_offset = new_col_offset
            
        if column_map:
            data_start_row = max_header_row + 1
            warnings.append({
                "row": None,
                "column_title": None,
                "message": (
                    "Yashirin UUID qatori topilmadi — sarlavha matniga qarab "
                    "moslashtirish ishlatildi."
                ),
            })

    if not column_map:
        raise ValueError(
            "Fayldan birorta ham ustunni aniqlab bo'lmadi. "
            "Ustun sarlavhalari bazadagi jadval bilan mos kelmayapti. "
            "Iltimos, tizimdan shablon yuklab oling va shu formatda to'ldiring."
        )

    errors = []

    # ── 5. Parse: plantlik ──
    if is_plant_based:
        return _parse_plant_based(
            ws=ws,
            statement=statement,
            col_offset=col_offset,
            column_map=column_map,
            title_by_id=title_by_id,
            warnings=warnings,
            errors=errors,
            lang=lang,
            data_start_row=data_start_row,
        )

    # ── 6. Parse: oddiy (flat) ──
    return _parse_flat(
        ws=ws,
        col_offset=col_offset,
        column_map=column_map,
        title_by_id=title_by_id,
        warnings=warnings,
        errors=errors,
        data_start_row=data_start_row,
    )


def _parse_flat(ws, col_offset, column_map, title_by_id, warnings, errors, data_start_row):
    """Oddiy (flat) report parse."""
    if ws.max_row < data_start_row:
        raise ValueError(
            f"Faylda ma'lumot qatori topilmadi (kamida {data_start_row}-qator kerak)."
        )

    all_items = []
    for row_cells in ws.iter_rows(min_row=data_start_row):
        row_num = row_cells[0].row if row_cells else None
        items = _extract_row_items(
            row_cells, col_offset, column_map, row_num, title_by_id, errors
        )
        all_items.extend(items)

    if not all_items and not errors:
        raise ValueError("Faylda hech qanday qiymat topilmadi.")

    status = "success" if not errors else ("partial" if all_items else "error")
    return {
        "status": status,
        "items": all_items,
        "warnings": warnings,
        "errors": errors,
    }


def _parse_plant_based(ws, statement, col_offset, column_map, title_by_id,
                       warnings, errors, lang, data_start_row):
    """Plantlik report parse."""
    # Tegishli leaf plantlarni yuklash
    valid_plants = {
        str(p.id): p
        for p in Plant.objects.filter(
            statement=statement,
            children__isnull=True,
        )
    }

    plants_payload = []

    for row_cells in ws.iter_rows(min_row=data_start_row):
        if not row_cells:
            continue
        row_num = row_cells[0].row

        # Col A — Plant ID
        plant_id_raw = row_cells[0].value if len(row_cells) > 0 else None
        if plant_id_raw is None or str(plant_id_raw).strip() == "":
            continue  # Bo'sh qator — o'tkazib yuboramiz

        plant_id = str(plant_id_raw).strip()
        plant = valid_plants.get(plant_id)

        if not plant:
            errors.append({
                "row": row_num,
                "column_title": "Plant ID",
                "message": f"O'simlik topilmadi yoki bu statement ga tegishli emas: '{plant_id}'",
            })
            continue

        items = _extract_row_items(
            row_cells, col_offset, column_map, row_num, title_by_id, errors
        )

        if items:
            plant_name = getattr(plant, f"name_{lang}", plant.name) or plant.name
            plants_payload.append({
                "plant": plant_id,
                "plant_name": plant_name,
                "items": items,
            })

    if not plants_payload and not errors:
        raise ValueError("Faylda hech qanday o'simlik uchun qiymat topilmadi.")

    status = "success" if not errors else ("partial" if plants_payload else "error")
    return {
        "status": status,
        "plants": plants_payload,
        "warnings": warnings,
        "errors": errors,
    }
