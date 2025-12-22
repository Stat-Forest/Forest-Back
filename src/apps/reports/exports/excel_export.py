import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, Set

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from django.conf import settings


def apply_border_to_range(ws, min_row, max_row, min_col, max_col, border):
    for r in range(min_row, max_row + 1):
        for c in range(min_col, max_col + 1):
            ws.cell(row=r, column=c).border = border


def _ordering_key(ordering: str) -> tuple:
    return tuple(int(p) if p.isdigit() else p for p in (ordering or "").split("."))


def _pick_best_value(inners: list) -> str:
    if not inners:
        return ""

    values = [str((it.get("value") or "")).strip() for it in inners]

    if len(values) == 1:
        return values[0]

    def to_float(s):
        try:
            return float(s.replace(" ", "").replace(",", "."))
        except Exception:
            return None

    nums = [to_float(v) for v in values]
    if all(n is not None for n in nums):
        total = sum(nums)
        return str(int(total)) if total.is_integer() else str(total)

    return next((v for v in values if v), "")


def export_universal_report_to_excel_v2(
    reports: List[Dict[str, Any]],
    *,
    filename_prefix: str = "report_export",
    lang: str = "uz",
    statement_id: Optional[str] = None,
) -> Tuple[str, str]:
    from apps.reports.models import StatementColumn

    now = datetime.now()
    filename = f"{filename_prefix}_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"
    export_dir = getattr(settings, "EXPORT_ROOT", os.path.join(settings.BASE_DIR, "exports"))
    os.makedirs(export_dir, exist_ok=True)
    file_path = os.path.join(export_dir, filename)

    wb = Workbook()
    ws = wb.active
    ws.title = "Reports"

    # =============================
    # 🔹 Export time (TOP LEFT)
    # =============================
    export_text = f"Export qilingan vaqt: {now.strftime('%Y-%m-%d %H:%M:%S')}"

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=2)
    cell = ws.cell(row=1, column=1)

    cell.value = export_text
    cell.font = Font(bold=True, italic=True)
    cell.alignment = Alignment(horizontal="left", vertical="center")
    cell.border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )

    HEADER_START_ROW = 2  # header shu qatordan boshlanadi

    # =============================
    # Collect column IDs
    # =============================
    needed_ids: Set[str] = {
        str(col["statement_column_id"])
        for report in reports
        for item in report.get("report_items") or []
        for col in item.get("statement_columns") or []
        if col.get("statement_column_id")
    }

    if not needed_ids:
        ws.append(["№", "Tashkilot nomi"])
        wb.save(file_path)
        return file_path, filename

    if not statement_id:
        statement_id = str(
            StatementColumn.objects.filter(id=next(iter(needed_ids)))
            .values_list("statement_id", flat=True)
            .first()
        )

    all_cols = list(
        StatementColumn.objects.filter(statement_id=statement_id)
        .select_related("parent")
        .only("id", "parent_id", "ordering", "title_uz", "title_ru", "is_organization")
    )
    id_map = {str(c.id): c for c in all_cols}

    def is_org(c): return getattr(c, "is_organization", False)

    export_ids = {cid for cid in needed_ids if cid in id_map and not is_org(id_map[cid])}
    included_ids = set(export_ids)

    for cid in list(export_ids):
        cur = id_map.get(cid)
        while cur and cur.parent_id:
            included_ids.add(str(cur.parent_id))
            cur = id_map.get(str(cur.parent_id))

    children: Dict[Optional[str], List[Any]] = {}
    for cid in included_ids:
        c = id_map.get(cid)
        if not c or is_org(c):
            continue
        children.setdefault(str(c.parent_id) if c.parent_id else None, []).append(c)

    for k in children:
        children[k].sort(key=lambda x: _ordering_key(x.ordering or ""))

    def dfs(node):
        ch = children.get(str(node.id), [])
        if not ch:
            return [node] if str(node.id) in export_ids else []
        return [x for c in ch for x in dfs(c)]

    leaves = [x for r in children.get(None, []) for x in dfs(r)]
    leaf_ids = [str(c.id) for c in leaves]

    def depth(n):
        ch = children.get(str(n.id), [])
        return 1 if not ch else 1 + max(depth(c) for c in ch)

    max_depth = max((depth(r) for r in children.get(None, [])), default=1)
    total_cols = 2 + len(leaf_ids)

    header_grid = [["" for _ in range(total_cols)] for _ in range(max_depth)]
    header_grid[0][0] = "№"
    header_grid[0][1] = "Tashkilot nomi"

    def title_of(c):
        return c.title_ru if lang == "ru" else c.title_uz

    span_cache = {}

    def span(n):
        if n.id in span_cache:
            return span_cache[n.id]
        ch = children.get(str(n.id), [])
        span_cache[n.id] = 1 if not ch else sum(span(c) for c in ch)
        return span_cache[n.id]

    merges = []

    def place(node, level, col):
        header_grid[level][col] = title_of(node)
        sp = span(node)
        ch = children.get(str(node.id), [])
        if not ch:
            if level < max_depth - 1:
                merges.append((HEADER_START_ROW + level, col + 1, HEADER_START_ROW + max_depth - 1, col + 1))
            return col + 1
        merges.append((HEADER_START_ROW + level, col + 1, HEADER_START_ROW + level, col + sp))
        cur = col
        for c in ch:
            cur = place(c, level + 1, cur)
        return col + sp

    col_cursor = 2
    for r in children.get(None, []):
        col_cursor = place(r, 0, col_cursor)

    # =============================
    # Write headers
    # =============================
    for row in header_grid:
        ws.append(row)

    # ✅ SHU YERGA QO‘SHASIZ:
    ws.merge_cells(
        start_row=HEADER_START_ROW,
        start_column=1,
        end_row=HEADER_START_ROW + max_depth - 1,
        end_column=1,
    )
    ws.merge_cells(
        start_row=HEADER_START_ROW,
        start_column=2,
        end_row=HEADER_START_ROW + max_depth - 1,
        end_column=2,
    )

    # =============================
    # Header style
    # =============================
    thin_border = Border(
        left=Side(style='thin', color='000000'),
        right=Side(style='thin', color='000000'),
        top=Side(style='thin', color='000000'),
        bottom=Side(style='thin', color='000000'),
    )

    header_fill = PatternFill("solid", fgColor="D9E1F2")

    # Qo‘llash: har bir header katakchasiga
    for row in ws.iter_rows(
            min_row=HEADER_START_ROW,
            max_row=HEADER_START_ROW + max_depth - 1,
            min_col=1,
            max_col=total_cols
    ):
        for cell in row:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.fill = header_fill
            cell.border = thin_border

    for r1, c1, r2, c2 in merges:
        ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)

    apply_border_to_range(
        ws,
        HEADER_START_ROW,
        HEADER_START_ROW + max_depth - 1,
        1,
        total_cols,
        thin_border
    )

    ws.freeze_panes = ws.cell(row=HEADER_START_ROW + max_depth, column=3)

    # =============================
    # Data rows
    # =============================
    data_start_row = ws.max_row + 1

    for i, report in enumerate(reports, start=1):
        row_values = [i, report.get("organization_name", "")]
        values = {}
        for item in report.get("report_items") or []:
            for col in item.get("statement_columns") or []:
                cid = str(col.get("statement_column_id"))
                if cid in leaf_ids:
                    values[cid] = _pick_best_value(col.get("inners") or [])
        row_values += [values.get(cid, "") for cid in leaf_ids]

        ws.append(row_values)

    # Apply borders to data cells
    data_end_row = ws.max_row
    for row in ws.iter_rows(min_row=data_start_row, max_row=data_end_row, min_col=1, max_col=total_cols):
        for cell in row:
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # =============================
    # Compact column width
    # =============================
    for col in range(1, ws.max_column + 1):
        letter = get_column_letter(col)

        # Agar bu 1-ustun bo‘lsa (ya'ni "№")
        if col == 1:
            ws.column_dimensions[letter].width = 5  # qat'iy kichik qilib qo'yamiz
            continue

        # Qolganlar uchun avto-width
        ws.column_dimensions[letter].width = min(
            max(8, min(max(len(str(ws.cell(r, col).value or "")) for r in range(1, ws.max_row + 1)) + 1, 28)),
            28
        )
    wb.save(file_path)
    return file_path, filename
