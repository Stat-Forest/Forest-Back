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
    _issue,
    get_plan_columns,
    is_plant_based_statement,
    normalize_title,
    split_title_path,
    strip_ordinal,
)
from apps.reports.services.report_import.plan_validation import validate_plan_values

HEADER_ROW = 1
# ID_ROW endi statik emas — ko'p qatorli sarlavhada UUID qatori
# sarlavha blokidan keyin turadi. _find_uuid_row() orqali topiladi.

# Sarlavhalar shuncha qatordan ichida qidiriladi (export fayllarida
# sarlavha 2-qatordan boshlanadi va 4-5 qavat bo'lishi mumkin).
MAX_HEADER_SCAN_ROWS = 12

# Payload cheksiz o'smasligi uchun ogohlantirishlar chegarasi
MAX_UNMATCHED_WARNINGS = 10

# Ma'lumot ustuni EMAS — xizmat ustunlari (№, tashkilot, o'simlik nomi)
PLANT_ID_HEADERS = {"plant id", "plant id (o'zgartirmang)", "o'simlik id"}
PLANT_NAME_HEADERS = {"o'simlik nomi", "название растения", "o'simlik", "daromad manbalari", "источники дохода"}
ORGANIZATION_HEADERS = {"tashkilot nomi", "название организации"}
ROW_NUMBER_HEADERS = {"№", "n", "t/r", "№ п/п"}
SERVICE_HEADERS = (
    PLANT_ID_HEADERS | PLANT_NAME_HEADERS | ORGANIZATION_HEADERS | ROW_NUMBER_HEADERS
)


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


def _find_uuid_row(ws, index, max_scan_rows=None):
    """
    Yashirin UUID qatorini dynamik topadi.

    Ko'p qatorli sarlavhali shablonda UUID qatori sarlavha blokidan
    KEYIN joylashadi (endi 2-qator emas). Shuning uchun barcha
    qatorlarni (1 dan max_scan_rows gacha) ko'rib chiqamiz va UUID
    formatidagi qiymatlar (ulardan kamida bittasi importable) bor
    qatorni qaytaramiz.
    """
    if max_scan_rows is None:
        max_scan_rows = min(ws.max_row, MAX_HEADER_SCAN_ROWS)

    for row in range(1, max_scan_rows + 1):
        uuid_count = 0
        importable_count = 0
        for cell in ws[row]:
            raw = cell.value
            if raw is None or str(raw).strip() == "":
                continue
            text = str(raw).strip()
            # UUID formati: 8-4-4-4-12 (kamida bitta "-" bor va to'g'ri uzunlik)
            if "-" in text and len(text) == 36:
                uuid_count += 1
                if text in index.importable_ids:
                    importable_count += 1
        # Kamida 1 ta importable UUID bo'lsa — bu UUID qatori
        if importable_count >= 1:
            return row

    return None


def _match_columns_by_uuid_row(ws, index, uuid_row=None):
    """
    Berilgan qatordagi yashirin UUID'lardan {excel_column_index: column_uuid} quradi.
    Faqat import qilinadigan ustunlar qabul qilinadi.

    `uuid_row` berilmasa, `_find_uuid_row` orqali topiladi.
    """
    if uuid_row is None:
        uuid_row = _find_uuid_row(ws, index)
    if uuid_row is None:
        return {}, [], None

    column_map = {}
    foreign = []
    for cell in ws[uuid_row]:
        raw = cell.value
        if raw is None or str(raw).strip() == "":
            continue
        uuid_str = str(raw).strip()
        if uuid_str in index.importable_ids:
            column_map[cell.column] = uuid_str
        elif "-" in uuid_str:  # UUID ko'rinishida, lekin import qilinmaydi
            foreign.append((cell.column, uuid_str))
    return column_map, foreign, uuid_row


def _find_service_columns_in_template(ws, index, merged_values, header_end_row=None):
    """
    Shablon fayldagi xizmat ustunlari (Plant ID, O'simlik nomi, №, Tashkilot).

    Ko'p qatorli sarlavhada xizmat ustunlari faqat 1-qatorda emas,
    barcha sarlavha qatorlarida bo'lishi mumkin. Shuning uchun barcha
    sarlavha qatorlarini skanerlaymiz.
    """
    if header_end_row is None:
        header_end_row = HEADER_ROW

    service_columns = {}
    for row in range(HEADER_ROW, header_end_row + 1):
        for col in range(1, ws.max_column + 1):
            text = normalize_title(
                merged_values.get((row, col), ws.cell(row=row, column=col).value)
            )
            if text in PLANT_ID_HEADERS:
                service_columns.setdefault("plant_id", col)
            elif text in PLANT_NAME_HEADERS:
                service_columns.setdefault("plant_name", col)
            elif text in ORGANIZATION_HEADERS:
                service_columns.setdefault("organization", col)
            elif text in ROW_NUMBER_HEADERS:
                service_columns.setdefault("row_number", col)
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

def parse_import_excel(file_obj, statement, sheet_name=None, lang="uz",
                        organization=None, year=None, season=None):
    """
    Yuklangan Excel faylni o'qib, frontend uchun payload qaytaradi.

    Export fayli har bir ilova uchun alohida varaq (sheet) chiqaradi,
    shuning uchun `sheet_name` berilmasa BARCHA varaqlar o'qiladi va
    natijalar birlashtiriladi.

    Args:
        file_obj: InMemoryUploadedFile yoki file-like object
        statement: Statement model instance
        sheet_name: O'qiladigan sheet nomi (None bo'lsa — barcha varaqlar)
        lang: Til kodi ("uz" yoki "ru")
        organization: Organization instance/UUID — berilsa, faylda topilgan
            Reja ustunlari qiymati shu tashkilotning tasdiqlangan Plan/
            PlanItem qiymati bilan solishtiriladi (`plan_validation.py`).
        year: int — Reja qidiriladigan yil (`organization` bilan birga kerak).
        season: str|None — Plan.SeasonChoices qiymati (mavsumga bog'liq
            statement'lar uchun).

    Returns:
        dict — response payload (status, items/plants, warnings, errors)

    Raises:
        ValueError — fayl formati noto'g'ri yoki o'qib bo'lmasa
        PlanMismatchError (ValueError farzandi) — faylda topilgan Reja
            qiymati tasdiqlangan reja bilan mos kelmasa
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
        sheets = [wb[sheet_name]]
    else:
        sheets = list(wb.worksheets)

    # ── 3. Import qilinadigan ustunlar ──
    index = StatementColumnIndex(statement, lang=lang)
    if not index.importable:
        raise ValueError(
            "Bu statement uchun import qilinadigan ustunlar topilmadi "
            "(barcha oxirgi ustunlar reja yoki avto-hisob sifatida belgilangan)."
        )

    # Reja ustunlari uchun alohida index — faylda topilsa (bo'lim_admin
    # tasdiqlagan reja bilan solishtirish uchun), lekin javobga hech
    # qachon qo'shilmaydi.
    plan_index = StatementColumnIndex(
        statement, lang=lang, columns_queryset=get_plan_columns(statement)
    )

    is_plant_based = is_plant_based_statement(statement)

    results = []
    plan_founds = []
    failures = []
    for ws in sheets:
        try:
            result, plan_found = _parse_sheet(
                ws, statement, index, plan_index, lang, is_plant_based
            )
            results.append(result)
            plan_founds.append(plan_found)
        except ValueError as exc:
            # Bitta varaqda ma'lumot bo'lmasligi mumkin (masalan bo'sh ilova) —
            # butun importni to'xtatmaymiz
            failures.append(str(exc))

    if not results:
        raise ValueError(failures[0] if failures else "Faylda hech qanday qiymat topilmadi.")

    if organization is not None and year is not None:
        flat_found, plant_found = _merge_plan_found(plan_founds)
        validate_plan_values(
            statement=statement,
            organization=organization,
            year=year,
            season=season,
            index_label=plan_index.label_by_id,
            flat_found=flat_found,
            plant_found=plant_found,
        )

    return _merge_sheet_results(results, is_plant_based)


def _merge_plan_found(plan_founds):
    """
    Har bir varaqda topilgan Reja qiymatlarini birlashtiradi (bir ustun
    bir necha varaqda uchrasa — birinchi topilgan qiymat qoladi, xuddi
    Amalda `_merge_sheet_results` kabi).
    """
    flat = {}
    by_plant = {}
    for pf in plan_founds:
        for column_id, value_row in pf["flat"].items():
            flat.setdefault(column_id, value_row)
        for plant_id, cols in pf["by_plant"].items():
            dest = by_plant.setdefault(plant_id, {})
            for column_id, value_row in cols.items():
                dest.setdefault(column_id, value_row)
    return flat, by_plant


def _parse_sheet(ws, statement, index, plan_index, lang, is_plant_based):
    """Bitta varaqni o'qiydi (ilova = varaq)."""
    warnings = []
    errors = []

    last_scan_row = min(ws.max_row, MAX_HEADER_SCAN_ROWS)
    merged_values = _merged_header_values(ws, last_scan_row)
    # Sarlavha bloki reja ustunlarini topish uchun ham kerak — Amalda
    # ustunlar yashirin UUID qatori orqali topilgan bo'lsa ham, reja
    # ustunlari hech qachon UUID qatoriga tushmagani uchun har doim
    # sarlavha matni bo'yicha qidiriladi.
    header_rows = _header_rows(ws, index, merged_values, last_scan_row)

    # ── 4. Ustunlarni moslashtirish ──
    # 4a. Shablon: yashirin UUID qatorini dynamik topish (eng ishonchli yo'l)
    column_map, foreign_uuids, found_uuid_row = _match_columns_by_uuid_row(ws, index)

    if column_map:
        data_start_row = found_uuid_row + 1
        # Sarlavha UUID qatoridan OLDIN tugaydi
        header_end_row = found_uuid_row - 1 if found_uuid_row else HEADER_ROW
        service_columns = _find_service_columns_in_template(
            ws, index, merged_values, header_end_row=header_end_row
        )
        if foreign_uuids:
            warnings.append(_issue(
                f"{len(foreign_uuids)} ta ustun import qilinmaydi "
                f"(reja, avto-hisob yoki boshqa jadval ustuni) — o'tkazib yuborildi."
            ))
    else:
        # 4b. Fallback: sarlavha matni bo'yicha (export yoki qo'lda tuzilgan fayl)
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

    # ── 4c. Reja ustunlarini aniqlash (faqat validatsiya uchun — javobga
    # hech qachon qo'shilmaydi). Sarlavha bloki topilmagan bo'lsa (ID
    # qatori orqali Amalda topilgan-u, lekin sarlavha aniqlanmagan holat
    # ehtimoldan yiroq) — reja tekshiruvi shunchaki o'tkazib yuboriladi.
    plan_column_map = {}
    if plan_index.importable and header_rows:
        plan_column_map, _plan_service_cols, _plan_unmatched = _match_columns_by_title(
            ws, plan_index, merged_values, header_rows
        )

    # ── 5. Qiymatlarni o'qish ──
    if is_plant_based:
        result, plan_found_by_plant = _parse_plant_based(
            ws=ws,
            statement=statement,
            index=index,
            column_map=column_map,
            service_columns=service_columns,
            warnings=warnings,
            errors=errors,
            lang=lang,
            data_start_row=data_start_row,
            plan_column_map=plan_column_map,
        )
        return result, {"flat": {}, "by_plant": plan_found_by_plant}

    result, plan_found_flat = _parse_flat(
        ws=ws,
        index=index,
        column_map=column_map,
        service_columns=service_columns,
        warnings=warnings,
        errors=errors,
        data_start_row=data_start_row,
        plan_column_map=plan_column_map,
    )
    return result, {"flat": plan_found_flat, "by_plant": {}}


def _merge_sheet_results(results, is_plant_based):
    """
    Har bir ilova alohida varaqda bo'lgani uchun, varaqlar natijasini
    bitta payloadga birlashtiramiz. Bir ustun bir necha varaqda uchrasa,
    birinchi topilgan qiymat qoladi.
    """
    warnings = []
    errors = []
    seen_warnings = set()

    for result in results:
        for warning in result.get("warnings", []):
            key = (warning.get("row"), warning.get("column_title"), warning.get("message"))
            if key in seen_warnings:
                continue
            seen_warnings.add(key)
            warnings.append(warning)
        errors.extend(result.get("errors", []))

    if not is_plant_based:
        all_items = []
        all_rows = []
        for result in results:
            all_items.extend(result.get("items", []))
            all_rows.extend(result.get("rows", []))

        status = "success" if not errors else ("partial" if all_items else "error")
        return {
            "status": status,
            "is_plant_based": False,
            "items": all_items,
            "rows": all_rows,
            "warnings": warnings,
            "errors": errors,
        }

    plants_order = []
    plant_names = {}
    values_by_plant = {}

    for result in results:
        for entry in result.get("plants", []):
            pid = entry["plant"]
            if pid not in values_by_plant:
                values_by_plant[pid] = {}
                plant_names[pid] = entry.get("plant_name") or ""
                plants_order.append(pid)
            for item in entry.get("items", []):
                values_by_plant[pid].setdefault(item["column"], item["value"])

    plants = []
    items = []
    for pid in plants_order:
        plant_items = [
            {"column": cid, "value": val}
            for cid, val in values_by_plant[pid].items()
        ]
        plants.append({
            "plant": pid,
            "plant_name": plant_names[pid],
            "items": plant_items,
        })
        items.extend(
            {
                "column": it["column"],
                "plant": pid,
                "plant_name": plant_names[pid],
                "value": it["value"],
            }
            for it in plant_items
        )

    status = "success" if not errors else ("partial" if plants else "error")
    return {
        "status": status,
        "is_plant_based": True,
        "items": items,
        "plants": plants,
        "warnings": warnings,
        "errors": errors,
    }


def _parse_flat(ws, index, column_map, service_columns, warnings, errors, data_start_row,
                 plan_column_map=None):
    """
    Oddiy (flat) report parse.

    Har bir ma'lumot qatorini alohida entry sifatida o'qiydi.
    Foydalanuvchi bir nechta qator kiritishi mumkin (masalan, har bir
    qator — alohida tashkilot yoki alohida yozuv).

    Response formati:
        items: [{column, value, row, organization}, ...]  — barcha qatorlardan
        rows:  [{row, organization, items: [{column, value}]}, ...]  — qator bo'yicha guruhlangan

    Returns:
        (result_dict, plan_found) — `plan_found` {column_id: (value, row)}
        faylda topilgan Reja ustuni qiymatlari (javobga qo'shilmaydi,
        faqat `plan_validation.validate_plan_values` uchun).
    """
    if ws.max_row < data_start_row:
        raise ValueError(
            f"Faylda ma'lumot qatori topilmadi (kamida {data_start_row}-qator kerak)."
        )

    all_items = []
    rows = []
    plan_found = {}

    for row_cells in ws.iter_rows(min_row=data_start_row):
        items = _extract_row_items(row_cells, column_map)
        plan_items = _extract_row_items(row_cells, plan_column_map) if plan_column_map else []
        if not items and not plan_items:
            continue

        row_number = row_cells[0].row

        for pit in plan_items:
            plan_found.setdefault(pit["column"], (pit["value"], row_number))

        if not items:
            continue

        # Tashkilot nomini aniqlash
        organization = _cell_text(
            row_cells,
            service_columns.get("organization"),
        )

        row_entry = {
            "row": row_number,
            "organization": organization,
            "items": items,
        }
        rows.append(row_entry)

        # Flat items — har bir element qator va tashkilot ma'lumoti bilan
        for item in items:
            all_items.append({
                "column": item["column"],
                "value": item["value"],
                "row": row_number,
                "organization": organization,
            })

    if not all_items and not errors:
        raise ValueError("Faylda hech qanday qiymat topilmadi.")

    status = "success" if not errors else ("partial" if all_items else "error")
    result = {
        "status": status,
        "is_plant_based": False,
        "items": all_items,
        "rows": rows,
        "warnings": warnings,
        "errors": errors,
    }
    return result, plan_found


def _parse_plant_based(ws, statement, index, column_map, service_columns,
                       warnings, errors, lang, data_start_row, plan_column_map=None):
    """
    Plantlik report parse.

    O'simlik avval ID bo'yicha (shablon), topilmasa nomi bo'yicha
    (export fayl) aniqlanadi.

    Returns:
        (result_dict, plan_found) — `plan_found` {plant_id: {column_id: (value, row)}}.
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
    plan_found = {}
    skipped_rows = 0
    total_rows = 0

    for row_cells in ws.iter_rows(min_row=data_start_row):
        if not row_cells:
            continue
        row_number = row_cells[0].row

        items = _extract_row_items(row_cells, column_map)
        plan_items = _extract_row_items(row_cells, plan_column_map) if plan_column_map else []
        if not items and not plan_items:
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

        if plan_items:
            plan_stored = plan_found.setdefault(plant_id, {})
            for pit in plan_items:
                plan_stored.setdefault(pit["column"], (pit["value"], row_number))

        if not items:
            continue

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
    result = {
        "status": status,
        "is_plant_based": True,
        "items": all_items,
        "plants": plants_payload,
        "warnings": warnings,
        "errors": errors,
    }
    return result, plan_found
