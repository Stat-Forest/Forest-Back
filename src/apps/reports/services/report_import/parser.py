# apps/reports/services/report_import/parser.py
"""
Yuklangan Excel (.xlsx) faylni parse qilib, frontend uchun
strukturalangan JSON payload qaytaradi.

DB ga hech narsa YOZILMAYDI — faqat o'qish va validatsiya.

Qaytariladigan har bir `column` — shu statement ning import qilinadigan
(Amalda) ustuni ID si. Frontend aynan shu ID bo'yicha forma inputini
topadi, shuning uchun payloadga boshqa hech qanday ustun (reja, guruh
sarlavhasi, avto-hisob) tushmasligi kerak.

Return formati (oddiy hisobot — is_plant_based=False):
    {"status": "success"|"partial"|"error",
     "is_plant_based": false,
     "items": [{"column": "<uuid>", "value": "..."}, ...],
     "warnings": [...], "errors": [...]}

Return formati (plantlik hisobot — is_plant_based=True):
    {"status": "success"|"partial"|"error",
     "is_plant_based": true,
     "items": [{"column": "<uuid>", "plant": "<uuid>",
                "plant_name": "...", "value": "..."}, ...],
     "plants": [{"plant": "<uuid>", "plant_name": "...",
                  "items": [{"column": "<uuid>", "value": "..."}, ...]}, ...],
     "warnings": [...], "errors": [...]}

`items` har doim bor va bir xil ishlatiladi — plantlik hisobotda har bir
element qo'shimcha `plant` bilan keladi. `plants` esa o'sha ma'lumotning
o'simlik bo'yicha guruhlangan ko'rinishi (Excel qatorlari kabi).

`warnings` va `errors` elementlari bir xil shaklda:
    {"row": <int|null>, "column_title": <str|null>, "message": "..."}
"""

import openpyxl

from apps.reports.models import Plant
from apps.reports.services.change_coma_to_dote import normalize_decimal_input_dote
from apps.reports.services.report_import.columns import (
    StatementColumnIndex,
    is_plant_based_statement,
    normalize_title,
    split_title_path,
    strip_ordinal,
)

HEADER_ROW = 1
ID_ROW = 2

# Sarlavhalar shuncha qatordan ichida qidiriladi (export fayllarida
# sarlavha 2-qatordan boshlanadi va 4-5 qavat bo'lishi mumkin).
MAX_HEADER_SCAN_ROWS = 12

# Payload cheksiz o'smasligi uchun ogohlantirishlar chegarasi
MAX_UNMATCHED_WARNINGS = 10

# Ma'lumot ustuni EMAS — xizmat ustunlari (№, tashkilot, o'simlik nomi)
PLANT_ID_HEADERS = {"plant id", "plant id (o'zgartirmang)", "o'simlik id"}
PLANT_NAME_HEADERS = {"o'simlik nomi", "название растения", "o'simlik"}
ORGANIZATION_HEADERS = {"tashkilot nomi", "название организации"}
ROW_NUMBER_HEADERS = {"№", "n", "t/r", "№ п/п"}
SERVICE_HEADERS = (
    PLANT_ID_HEADERS | PLANT_NAME_HEADERS | ORGANIZATION_HEADERS | ROW_NUMBER_HEADERS
)


def _issue(message, row=None, column_title=None):
    """warnings/errors uchun yagona format."""
    return {"row": row, "column_title": column_title, "message": message}


# ──────────────────────────────────────────────────────────────────────
#  Sarlavhalarni o'qish
# ──────────────────────────────────────────────────────────────────────

def _merged_header_values(ws, last_row):
    """
    Birlashtirilgan (merged) kataklar qiymatini butun diapazonga yoyadi.

    openpyxl da merged range ning faqat chap-yuqori katagida qiymat
    turadi — export fayllarida guruh sarlavhasi shunday bo'ladi
    ("1-chorak reja" H4:J4). Yoyilmasa, H dan boshqa ustunlar o'z
    guruhini "ko'rmaydi".
    """
    values = {}
    for cell_range in ws.merged_cells.ranges:
        if cell_range.min_row > last_row:
            continue
        value = ws.cell(row=cell_range.min_row, column=cell_range.min_col).value
        if value is None:
            continue
        for row in range(cell_range.min_row, min(cell_range.max_row, last_row) + 1):
            for col in range(cell_range.min_col, cell_range.max_col + 1):
                values[(row, col)] = value
    return values


def _is_known_header_text(index, value):
    """Matn bazadagi ustun nomi yoki xizmat sarlavhasimi?"""
    text = normalize_title(value)
    if not text:
        return False
    if text in SERVICE_HEADERS or text in index.known_titles:
        return True
    return any(part in index.known_titles for part in split_title_path(value))


def _classify_row(ws, index, merged_values, row):
    """
    Qator turini aniqlaydi: "header" | "data" | "empty".

    Sarlavha qatorida tanish nomlar ustunlik qiladi, ma'lumot qatorida esa
    tashkilot nomi / sonlar — ya'ni notanish qiymatlar.
    """
    known = unknown = 0
    for col in range(1, ws.max_column + 1):
        value = merged_values.get((row, col), ws.cell(row=row, column=col).value)
        if value is None or str(value).strip() == "":
            continue
        if _is_known_header_text(index, value):
            known += 1
        else:
            unknown += 1

    if not known and not unknown:
        return "empty"
    if known and known >= unknown:
        return "header"
    return "data"


def _header_rows(ws, index, merged_values, last_scan_row):
    """
    Sarlavha bloki qaysi qatorlar ekanini aniqlaydi.

    Shablonda bu 1-qator, export faylda 2..6-qatorlar (1-qatorda
    "Export qilingan vaqt" turadi). Blok birinchi ma'lumot qatorida
    tugaydi — bo'sh qatorlar blokni uzmaydi.
    """
    states = {
        row: _classify_row(ws, index, merged_values, row)
        for row in range(1, last_scan_row + 1)
    }

    first = next((row for row, state in states.items() if state == "header"), None)
    if first is None:
        return []

    last = first
    for row in range(first + 1, last_scan_row + 1):
        if states[row] == "header":
            last = row
        elif states[row] == "data":
            break  # ma'lumot boshlandi — sarlavha tugadi
    return list(range(first, last + 1))


def _column_header_paths(ws, index, merged_values, header_rows):
    """
    Har bir Excel ustuni uchun sarlavha yo'lini quradi:

        C ustuni → ["1-ilova", "2025-yilda ... ma'lumot", "tumanlar nomi"]

    Yuqoridan pastga: har bir sarlavha qatoridagi matn qo'shiladi
    (takrorlanuvchilar tashlanadi).
    """
    paths = {}
    for col in range(1, ws.max_column + 1):
        path = []
        for row in header_rows:
            value = merged_values.get((row, col), ws.cell(row=row, column=col).value)
            text = normalize_title(value)
            if not text:
                continue
            # To'liq nom bazada bor bo'lsa — bo'lmaymiz
            # ("Telefon raqami / Telegram" kabi nomlar buzilmasligi uchun)
            parts = (
                [text]
                if (text in index.known_titles or text in SERVICE_HEADERS)
                else split_title_path(value)
            )
            for part in parts:
                if part and (not path or path[-1] != part):
                    path.append(part)
        if path:
            paths[col] = path
    return paths


def _score_candidate(index, column, excel_path):
    """
    Nomzod ustunning ota-onalari Excel sarlavha yo'lida qanchalik
    uchrashini sanaydi (tartibni saqlagan holda).

    "Amalda" 12 ta bo'lgan joyda aynan qaysi biri ekanini shu ajratadi:
    Excel yo'li ["1-chorak", "yanvar", "amalda"] bo'lsa, "Yanvar" ostidagi
    "Amalda" 2 ochko, boshqalari 1 yoki 0 ochko oladi.
    """
    score = 0
    position = 0
    for variants in index.ancestor_title_variants(column):
        for i in range(position, len(excel_path) - 1):
            if excel_path[i] in variants:
                score += 1
                position = i + 1
                break
    return score


def _match_columns_by_title(ws, index, merged_values, header_rows):
    """
    Sarlavha matni bo'yicha moslashtirish (yashirin UUID qatori yo'q fayllar uchun).

    Returns:
        (column_map, service_columns, unmatched)
        column_map      — {excel_column_index: column_uuid_str}
        service_columns — {"plant_id": idx, "plant_name": idx, "organization": idx}
        unmatched       — [(excel_column_index, header_text)]
    """
    paths = _column_header_paths(ws, index, merged_values, header_rows)

    column_map = {}
    service_columns = {}
    unmatched = []
    ambiguous = []

    for col, path in paths.items():
        leaf = path[-1]

        if leaf in SERVICE_HEADERS:
            if leaf in PLANT_ID_HEADERS:
                service_columns.setdefault("plant_id", col)
            elif leaf in PLANT_NAME_HEADERS:
                service_columns.setdefault("plant_name", col)
            elif leaf in ORGANIZATION_HEADERS:
                service_columns.setdefault("organization", col)
            else:
                service_columns.setdefault("row_number", col)
            continue

        # 1. To'liq yo'l mos kelsa — eng aniq natija.
        #    Import qilinmaydigan ustun (reja, avto-hisob) bo'lsa ham
        #    aynan tanilgani uchun jim o'tkazamiz.
        exact = index.columns_by_path(path)
        if len(exact) == 1:
            column_id = str(exact[0].id)
            if column_id in index.importable_ids:
                column_map[col] = column_id
            continue

        # 2. Shablondagi qisqartirilgan sarlavha ("Yanvar » Amalda") —
        #    to'liq yo'lning oxiriga mos kelishi yetarli.
        suffix_matches = index.importable_by_path_suffix(path)
        if len(suffix_matches) == 1:
            column_map[col] = str(suffix_matches[0].id)
            continue

        # 3. Sarlavha oxiridagi tartib raqami ("... (2)") — bir xil nomli,
        #    bir xil ota-onali ustunlarni faqat shu ajratadi.
        base_title, ordinal = strip_ordinal(leaf)
        if ordinal:
            twin = index.importable_by_path_ordinal(path[:-1] + [base_title], ordinal)
            if twin is not None:
                column_map[col] = str(twin.id)
                continue

        # 4. Oxirgi chora: nom bo'yicha nomzodlar + ota-onalar bo'yicha ochko
        candidates = index.candidates_by_leaf_title(leaf)
        if not candidates:
            # Bazada bunday nom umuman yo'q bo'lsa — ogohlantiramiz.
            # Bor-u, lekin import qilinmaydigan bo'lsa (reja, avto-hisob,
            # guruh sarlavhasi) — bu normal holat, jim o'tkazamiz.
            if leaf not in index.known_titles:
                unmatched.append((col, path[-1]))
            continue

        if len(candidates) == 1:
            column_map[col] = str(candidates[0].id)
            continue

        scored = [(_score_candidate(index, c, path), c) for c in candidates]
        best_score = max(score for score, _ in scored)
        best = [c for score, c in scored if score == best_score]
        if len(best) == 1:
            column_map[col] = str(best[0].id)
        else:
            ambiguous.append((col, path[-1]))

    return column_map, service_columns, unmatched + ambiguous


def _match_columns_by_uuid_row(ws, index):
    """
    2-qatordagi yashirin UUID'lardan {excel_column_index: column_uuid} quradi.
    Faqat import qilinadigan ustunlar qabul qilinadi.
    """
    column_map = {}
    foreign = []
    if ws.max_row < ID_ROW:
        return column_map, foreign

    for cell in ws[ID_ROW]:
        raw = cell.value
        if raw is None or str(raw).strip() == "":
            continue
        uuid_str = str(raw).strip()
        if uuid_str in index.importable_ids:
            column_map[cell.column] = uuid_str
        elif "-" in uuid_str:  # UUID ko'rinishida, lekin import qilinmaydi
            foreign.append((cell.column, uuid_str))
    return column_map, foreign


def _find_service_columns_in_template(ws, index, merged_values):
    """Shablon fayldagi xizmat ustunlari (Plant ID, O'simlik nomi)."""
    service_columns = {}
    for col in range(1, ws.max_column + 1):
        text = normalize_title(
            merged_values.get((HEADER_ROW, col), ws.cell(row=HEADER_ROW, column=col).value)
        )
        if text in PLANT_ID_HEADERS:
            service_columns.setdefault("plant_id", col)
        elif text in PLANT_NAME_HEADERS:
            service_columns.setdefault("plant_name", col)
        elif text in ORGANIZATION_HEADERS:
            service_columns.setdefault("organization", col)
    return service_columns


# ──────────────────────────────────────────────────────────────────────
#  Qiymatlarni o'qish
# ──────────────────────────────────────────────────────────────────────

def _extract_row_items(row_cells, column_map):
    """
    Bitta qatordagi kataklardan {column, value} juftliklarini yig'adi.
    Faqat moslashtirilgan ustunlar o'qiladi, bo'sh kataklar tashlanadi.
    """
    items = []
    for cell in row_cells:
        column_id = column_map.get(cell.column)
        if not column_id:
            continue

        value = cell.value
        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue

        normalized = normalize_decimal_input_dote(value)
        if normalized is None or str(normalized).strip() == "":
            continue

        items.append({"column": column_id, "value": str(normalized)})
    return items


def _cell_text(row_cells, col):
    """Qatordagi berilgan ustun katagi matni ("" agar bo'sh bo'lsa)."""
    if not col:
        return ""
    for cell in row_cells:
        if cell.column == col:
            return "" if cell.value is None else str(cell.value).strip()
    return ""


# ──────────────────────────────────────────────────────────────────────
#  Asosiy kirish nuqtasi
# ──────────────────────────────────────────────────────────────────────

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

    # ── 3. Import qilinadigan ustunlar ──
    index = StatementColumnIndex(statement, lang=lang)
    if not index.importable:
        raise ValueError(
            "Bu statement uchun import qilinadigan ustunlar topilmadi "
            "(barcha oxirgi ustunlar reja yoki avto-hisob sifatida belgilangan)."
        )

    warnings = []
    errors = []

    last_scan_row = min(ws.max_row, MAX_HEADER_SCAN_ROWS)
    merged_values = _merged_header_values(ws, last_scan_row)

    # ── 4. Ustunlarni moslashtirish ──
    # 4a. Shablon: 2-qatordagi yashirin UUID'lar (eng ishonchli yo'l)
    column_map, foreign_uuids = _match_columns_by_uuid_row(ws, index)

    if column_map:
        data_start_row = ID_ROW + 1
        service_columns = _find_service_columns_in_template(ws, index, merged_values)
        if foreign_uuids:
            warnings.append(_issue(
                f"{len(foreign_uuids)} ta ustun import qilinmaydi "
                f"(reja, avto-hisob yoki boshqa jadval ustuni) — o'tkazib yuborildi."
            ))
    else:
        # 4b. Fallback: sarlavha matni bo'yicha (export yoki qo'lda tuzilgan fayl)
        header_rows = _header_rows(ws, index, merged_values, last_scan_row)
        if not header_rows:
            raise ValueError(
                "Fayldan birorta ham ustunni aniqlab bo'lmadi. "
                "Ustun sarlavhalari bazadagi jadval bilan mos kelmayapti. "
                "Iltimos, tizimdan shablon yuklab oling va shu formatda to'ldiring."
            )

        column_map, service_columns, unmatched = _match_columns_by_title(
            ws, index, merged_values, header_rows
        )
        data_start_row = header_rows[-1] + 1

        if column_map:
            warnings.append(_issue(
                "Yashirin UUID qatori topilmadi — sarlavha matniga qarab "
                "moslashtirish ishlatildi."
            ))
        for _, title in unmatched[:MAX_UNMATCHED_WARNINGS]:
            warnings.append(_issue(
                f"«{title}» sarlavhasi jadval ustunlari bilan aniq mos kelmadi — "
                f"bu ustun o'tkazib yuborildi.",
                column_title=title,
            ))
        if len(unmatched) > MAX_UNMATCHED_WARNINGS:
            warnings.append(_issue(
                f"... va yana {len(unmatched) - MAX_UNMATCHED_WARNINGS} ta ustun "
                f"moslashtirilmadi."
            ))

    if not column_map:
        raise ValueError(
            "Fayldan birorta ham to'ldiriladigan ustunni aniqlab bo'lmadi. "
            "Ustun sarlavhalari bazadagi jadval bilan mos kelmayapti. "
            "Iltimos, tizimdan shablon yuklab oling va shu formatda to'ldiring."
        )

    # Himoya: payloadga faqat shu statement ning import ustunlari tushsin
    column_map = {
        col: column_id
        for col, column_id in column_map.items()
        if column_id in index.importable_ids
    }

    # ── 5. Qiymatlarni o'qish ──
    if is_plant_based_statement(statement):
        return _parse_plant_based(
            ws=ws,
            statement=statement,
            index=index,
            column_map=column_map,
            service_columns=service_columns,
            warnings=warnings,
            errors=errors,
            lang=lang,
            data_start_row=data_start_row,
        )

    return _parse_flat(
        ws=ws,
        index=index,
        column_map=column_map,
        service_columns=service_columns,
        warnings=warnings,
        errors=errors,
        data_start_row=data_start_row,
    )


def _parse_flat(ws, index, column_map, service_columns, warnings, errors, data_start_row):
    """
    Oddiy (flat) report parse.

    Bitta hisobot = bitta tashkilot = har bir ustun uchun bitta qiymat.
    Shuning uchun bir nechta ma'lumot qatori bo'lsa (masalan, ko'p
    tashkilotli export fayl), birinchi to'ldirilgan qiymat olinadi va
    foydalanuvchi ogohlantiriladi.
    """
    if ws.max_row < data_start_row:
        raise ValueError(
            f"Faylda ma'lumot qatori topilmadi (kamida {data_start_row}-qator kerak)."
        )

    values_by_column = {}
    first_row_used = None
    skipped_rows = 0

    for row_cells in ws.iter_rows(min_row=data_start_row):
        items = _extract_row_items(row_cells, column_map)
        if not items:
            continue

        row_number = row_cells[0].row
        new_values = [it for it in items if it["column"] not in values_by_column]
        if new_values:
            if first_row_used is None:
                first_row_used = row_number
            for item in new_values:
                values_by_column[item["column"]] = item["value"]
        if len(new_values) < len(items):
            skipped_rows += 1

    if skipped_rows:
        organization = _cell_text(
            next(ws.iter_rows(min_row=first_row_used, max_row=first_row_used)),
            service_columns.get("organization"),
        ) if first_row_used else ""
        detail = f" ({organization})" if organization else ""
        warnings.append(_issue(
            f"Faylda bir nechta ma'lumot qatori bor. Hisobot bitta tashkilot "
            f"uchun to'ldirilgani sababli {first_row_used}-qator{detail} "
            f"qiymatlari olindi, qolgan {skipped_rows} ta qator o'tkazib yuborildi.",
            row=first_row_used,
        ))

    all_items = [
        {"column": column_id, "value": value}
        for column_id, value in values_by_column.items()
    ]

    if not all_items and not errors:
        raise ValueError("Faylda hech qanday qiymat topilmadi.")

    status = "success" if not errors else ("partial" if all_items else "error")
    return {
        "status": status,
        "is_plant_based": False,
        "items": all_items,
        "warnings": warnings,
        "errors": errors,
    }


def _parse_plant_based(ws, statement, index, column_map, service_columns,
                       warnings, errors, lang, data_start_row):
    """
    Plantlik report parse.

    O'simlik avval ID bo'yicha (shablon), topilmasa nomi bo'yicha
    (export fayl) aniqlanadi.
    """
    plants = list(Plant.objects.filter(statement=statement, children__isnull=True))
    plants_by_id = {str(p.id): p for p in plants}

    plants_by_name = {}
    for plant in plants:
        # nom variantlari to'plam sifatida — name_uz == name bo'lsa,
        # bitta o'simlik ikki marta qo'shilib "bir nechta topildi"
        # bo'lib qolmasligi uchun
        names = {
            normalize_title(getattr(plant, field, None))
            for field in ("name_uz", "name_ru", "name")
        }
        for name in names:
            if name:
                plants_by_name.setdefault(name, []).append(plant)

    # Shablonda A ustuni — Plant ID. Export faylda esa A ustuni "№",
    # shuning uchun xizmat ustuni sifatida tanilgan bo'lsa ishlatmaymiz.
    service_indexes = set(service_columns.values())
    plant_id_col = service_columns.get("plant_id")
    if plant_id_col is None and 1 not in service_indexes:
        plant_id_col = 1
    plant_name_col = service_columns.get("plant_name")

    plants_payload = []
    values_by_plant = {}
    skipped_rows = 0
    total_rows = 0

    for row_cells in ws.iter_rows(min_row=data_start_row):
        if not row_cells:
            continue
        row_number = row_cells[0].row

        items = _extract_row_items(row_cells, column_map)
        if not items:
            continue  # bo'sh yoki "Jami" kabi qator — jim o'tkazamiz

        raw_id = _cell_text(row_cells, plant_id_col)
        raw_name = _cell_text(row_cells, plant_name_col)
        plant = plants_by_id.get(raw_id)

        if plant is None and raw_name:
            matches = plants_by_name.get(normalize_title(raw_name), [])
            if len(matches) == 1:
                plant = matches[0]
            elif len(matches) > 1:
                errors.append(_issue(
                    f"«{raw_name}» nomli bir nechta o'simlik bor — qaysi biri "
                    f"ekanini aniqlab bo'lmadi. Shablon fayldan foydalaning.",
                    row=row_number,
                    column_title="O'simlik nomi",
                ))
                continue

        if plant is None:
            if not raw_id and not raw_name:
                # O'simlik ko'rsatilmagan qator — "Jami" yoki izoh qatori
                total_rows += 1
                continue
            errors.append(_issue(
                f"O'simlik topilmadi yoki bu jadvalga tegishli emas: "
                f"'{raw_name or raw_id}'",
                row=row_number,
                column_title="O'simlik",
            ))
            continue

        plant_id = str(plant.id)
        if plant_id not in values_by_plant:
            values_by_plant[plant_id] = {}
            plant_name = getattr(plant, f"name_{lang}", plant.name) or plant.name
            plants_payload.append({
                "plant": plant_id,
                "plant_name": plant_name,
                "items": [],
            })

        stored = values_by_plant[plant_id]
        new_values = [it for it in items if it["column"] not in stored]
        for item in new_values:
            stored[item["column"]] = item["value"]
        if len(new_values) < len(items):
            skipped_rows += 1

    # Ikki ko'rinishda beramiz:
    #   items  — tekis ro'yxat, har bir qiymat o'z o'simligi bilan
    #            ({column, plant, plant_name, value})
    #   plants — o'simlik bo'yicha guruhlangan (Excel qatorlari kabi)
    all_items = []
    for entry in plants_payload:
        entry["items"] = [
            {"column": column_id, "value": value}
            for column_id, value in values_by_plant[entry["plant"]].items()
        ]
        all_items.extend(
            {
                "column": item["column"],
                "plant": entry["plant"],
                "plant_name": entry["plant_name"],
                "value": item["value"],
            }
            for item in entry["items"]
        )

    if skipped_rows:
        warnings.append(_issue(
            f"Bir xil o'simlik bir necha marta uchradi ({skipped_rows} ta qator) — "
            f"har bir o'simlik uchun birinchi to'ldirilgan qiymat olindi."
        ))

    if total_rows:
        warnings.append(_issue(
            f"{total_rows} ta qatorda o'simlik ko'rsatilmagan («Jami» yoki izoh "
            f"qatori) — ular o'tkazib yuborildi."
        ))

    if not plants_payload and not errors:
        raise ValueError("Faylda hech qanday o'simlik uchun qiymat topilmadi.")

    status = "success" if not errors else ("partial" if plants_payload else "error")
    return {
        "status": status,
        "is_plant_based": True,
        "items": all_items,
        "plants": plants_payload,
        "warnings": warnings,
        "errors": errors,
    }
