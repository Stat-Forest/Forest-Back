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
    """Aggregate multiple inners to a single cell value.

    Rules:
    - If no values -> empty string.
    - If any numeric-like values exist -> sum all numeric-like values (ignore non-numeric).
    - Else -> return the first non-empty textual value.
    """
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
    numeric_parts = [n for n in nums if n is not None]
    if numeric_parts:
        total = sum(numeric_parts)
        return str(int(total)) if float(total).is_integer() else str(total)

    return next((v for v in values if v), "")


def export_universal_report_to_excel_v2(
    reports: List[Dict[str, Any]],
    *,
    filename_prefix: str = "report_export",
    lang: str = "uz",
    statement_id: Optional[str] = None,
    aggregated_mode: bool = False,
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

    # Detect whether any report contains plant-based inners
    def _has_plant(report_dict: Dict[str, Any]) -> bool:
        for item in report_dict.get("report_items") or []:
            for col in item.get("statement_columns") or []:
                for inn in col.get("inners") or []:
                    if inn.get("plant_id"):
                        return True
        return False

    any_plant = any(_has_plant(r) for r in reports)
    fixed_cols = 3 if any_plant else 2
    total_cols = fixed_cols + len(leaf_ids)

    header_grid = [["" for _ in range(total_cols)] for _ in range(max_depth)]
    header_grid[0][0] = "№"
    header_grid[0][1] = "Tashkilot nomi"
    if any_plant:
        header_grid[0][2] = "O'simlik nomi" if lang == "uz" else "Название растения"

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

    col_cursor = fixed_cols
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
    if any_plant:
        ws.merge_cells(
            start_row=HEADER_START_ROW,
            start_column=3,
            end_row=HEADER_START_ROW + max_depth - 1,
            end_column=3,
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

    ws.freeze_panes = ws.cell(row=HEADER_START_ROW + max_depth, column=fixed_cols + 1)

    # =============================
    # Data rows
    # =============================
    data_start_row = ws.max_row + 1

    # Aggregated summary mode (regional/national Jami list screen):
    # - One row per report as-is
    # - Use provided hierarchical row_number if available
    # - No exploding of inners, no extra "Tashkilot Jami" rows
    if aggregated_mode and not any_plant:
        for report in reports:
            rep_items = report.get("report_items") or []
            if not rep_items:
                continue
            # The serializer returns a single dict inside report_items with organization_id
            org_block = rep_items[0] if rep_items else {}
            org_id_tag = org_block.get("organization_id")  # "general", "republic", "individual" or UUID

            org_name = report.get("organization_name", "")
            row_no = report.get("row_number") or ""  # hierarchical index like 1, 1.1, 2, ...

            is_general_rep = bool(report.get("is_general") or org_id_tag == "general")
            is_republic_rep = bool(report.get("is_republic") or org_id_tag == "republic")
            is_individual_general_rep = bool(report.get("is_individual_general") or org_id_tag == "individual")

            # 1) For Viloyat/Respublika Jami rows: one row with aggregated values
            if is_general_rep or is_republic_rep:
                values = {}
                for item in rep_items:
                    for col in item.get("statement_columns") or []:
                        cid = str(col.get("statement_column_id"))
                        if cid in leaf_ids:
                            values[cid] = _pick_best_value(col.get("inners") or [])
                row_values = [row_no, org_name] + [values.get(cid, "") for cid in leaf_ids]
                ws.append(row_values)
                continue

            # 2) For normal organizations: expand multiple inners into dynamic rows (like normal mode)
            #    but DO NOT append an extra "Tashkilot Jami" row in aggregated mode.
            per_col_inners: Dict[str, list] = {cid: [] for cid in leaf_ids}
            for item in rep_items:
                for col in item.get("statement_columns") or []:
                    cid = str(col.get("statement_column_id"))
                    if cid in per_col_inners:
                        per_col_inners[cid] = list(col.get("inners") or [])

            # Determine max row count across leaf columns
            row_count = 0
            for cid in leaf_ids:
                row_count = max(row_count, len(per_col_inners.get(cid, [])))

            # Emit a row per inner index; use the same hierarchical row_no in the first column for all rows
            for r_idx in range(row_count or 0):
                row_values = [row_no, org_name]
                for cid in leaf_ids:
                    inners = per_col_inners.get(cid, [])
                    val = ""
                    if r_idx < len(inners):
                        val = str((inners[r_idx] or {}).get("value") or "")
                    row_values.append(val)
                ws.append(row_values)

        # Style borders/alignment for aggregated rows
        data_end_row = ws.max_row
        for row in ws.iter_rows(min_row=data_start_row, max_row=data_end_row, min_col=1, max_col=total_cols):
            for cell in row:
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        # Column widths and save as usual
        for col in range(1, ws.max_column + 1):
            letter = get_column_letter(col)
            if col == 1:
                ws.column_dimensions[letter].width = 8
                continue
            ws.column_dimensions[letter].width = min(
                max(8, min(max(len(str(ws.cell(r, col).value or "")) for r in range(1, ws.max_row + 1)) + 1, 28)),
                28
            )
        wb.save(file_path)
        return file_path, filename

    # Build a helper map: organization_id (UUID string) -> individual general report dict
    ind_general_by_org: Dict[str, Dict[str, Any]] = {}
    for rep in reports:
        # Each rep has report_items: a list with one dict having organization_id
        rep_items = rep.get("report_items") or []
        if not rep_items:
            continue
        org_id_tag = (rep_items[0] or {}).get("organization_id")
        if org_id_tag == "individual":
            org_uuid = str(rep.get("organization")) if rep.get("organization") else None
            if org_uuid:
                ind_general_by_org[org_uuid] = rep

    # A separate counter for displayed organizations (excluding individual general)
    display_index = 0

    for report in reports:
        rep_items = report.get("report_items") or []
        if not rep_items:
            continue

        org_uuid = str(report.get("organization")) if report.get("organization") else None
        org_name = report.get("organization_name", "")
        org_id_tag = (rep_items[0] or {}).get("organization_id")

        # Skip individual general rows in output; they are used only for totals
        if org_id_tag == "individual":
            continue

        # Increment display index for base (non-individual-general) rows only
        display_index += 1

        if not any_plant:
            # Non-plant mode: expand multiple inners into dynamic rows
            # Gather per leaf column the list of inners
            per_col_inners: Dict[str, list] = {cid: [] for cid in leaf_ids}
            for item in rep_items:
                for col in item.get("statement_columns") or []:
                    cid = str(col.get("statement_column_id"))
                    if cid in per_col_inners:
                        per_col_inners[cid] = list(col.get("inners") or [])

            # Determine max row count across leaf columns
            row_count = 0
            for cid in leaf_ids:
                row_count = max(row_count, len(per_col_inners.get(cid, [])))

            # Write each inner index as a separate Excel row
            for r_idx in range(row_count or 0):
                row_values = [display_index, org_name]
                for cid in leaf_ids:
                    inners = per_col_inners.get(cid, [])
                    val = ""
                    if r_idx < len(inners):
                        val = str((inners[r_idx] or {}).get("value") or "")
                    row_values.append(val)
                ws.append(row_values)

            # Append organization total row (Tashkilot Jami)
            jami_label = "Tashkilot Jami" if lang == "uz" else "Итого по организации"
            total_row = [display_index, jami_label]

            # Prefer totals from individual general report of this organization
            ind_rep = ind_general_by_org.get(org_uuid)
            totals_by_col: Dict[str, str] = {}
            if ind_rep:
                ind_items = ind_rep.get("report_items") or []
                for ind_item in ind_items:
                    for col in ind_item.get("statement_columns") or []:
                        cid = str(col.get("statement_column_id"))
                        if cid in leaf_ids:
                            inners = [inn for inn in (col.get("inners") or []) if not inn.get("plant_id")]
                            totals_by_col[cid] = _pick_best_value(inners)

            # Fallback: sum numeric values from the dynamic rows if no ind total
            for cid in leaf_ids:
                v = totals_by_col.get(cid)
                if v not in (None, ""):
                    total_row.append(v)
                    continue
                # sum from rows
                col_total = 0.0
                seen = False
                # iterate previously added dynamic rows for this organization
                if row_count > 0:
                    for offset in range(row_count):
                        # The dynamic rows were appended in order; compute the row index
                        # We don't need to read back; we already have per_col_inners
                        inners = per_col_inners.get(cid, [])
                        if offset < len(inners):
                            val = str((inners[offset] or {}).get("value") or "")
                            try:
                                col_total += float(val.replace(" ", "").replace(",", "."))
                                seen = True
                            except Exception:
                                # ignore non-numeric
                                pass
                total_row.append(str(int(col_total)) if seen and float(col_total).is_integer() else (str(col_total) if seen else ""))

            ws.append(total_row)
            continue

        # Plant-mode: emit rows per plant and one Jami row
        plant_names: Dict[str, str] = {}
        per_plant: Dict[str, Dict[str, str]] = {}

        def _accumulate(current: Optional[str], new_val: Any) -> str:
            new_s = str(new_val) if new_val is not None else ""
            if current in (None, ""):
                return new_s
            try:
                a = float(str(current).replace(" ", "").replace(",", "."))
                b = float(str(new_s).replace(" ", "").replace(",", "."))
                s = a + b
                return str(int(s)) if s.is_integer() else str(s)
            except Exception:
                return new_s or current

        for item in rep_items:
            for col in item.get("statement_columns") or []:
                cid = str(col.get("statement_column_id"))
                if cid not in leaf_ids:
                    continue
                for inn in (col.get("inners") or []):
                    pid = inn.get("plant_id")
                    if pid:
                        plant_names[pid] = inn.get("plant_name") or plant_names.get(pid) or ""
                        prev = per_plant.setdefault(pid, {}).get(cid)
                        per_plant[pid][cid] = _accumulate(prev, inn.get("value"))

        # Write one row per plant
        for pid, pname in plant_names.items():
            row = [display_index, org_name, pname]
            vals = per_plant.get(pid, {})
            row += [vals.get(cid, "") for cid in leaf_ids]
            ws.append(row)

        # Build organization-level totals from individual general report if available
        jami_label = "Tashkilot Jami" if lang == "uz" else "Итого по организации"
        jami_row = [display_index, jami_label, ""]  # col3 empty per requirements

        totals_by_col: Dict[str, str] = {}
        ind_rep = ind_general_by_org.get(org_uuid)
        if ind_rep:
            for ind_item in (ind_rep.get("report_items") or []):
                for col in ind_item.get("statement_columns") or []:
                    cid = str(col.get("statement_column_id"))
                    if cid in leaf_ids:
                        inners = [inn for inn in (col.get("inners") or []) if not inn.get("plant_id")]
                        totals_by_col[cid] = _pick_best_value(inners)

        if totals_by_col:
            jami_row += [totals_by_col.get(cid, "") for cid in leaf_ids]
        else:
            # Fallback: sum across plants
            summed = []
            for cid in leaf_ids:
                total = 0.0
                seen = False
                for pid in plant_names.keys():
                    v = per_plant.get(pid, {}).get(cid)
                    if v in (None, ""):
                        continue
                    try:
                        total += float(str(v).replace(" ", "").replace(",", "."))
                        seen = True
                    except Exception:
                        pass
                summed.append(str(int(total)) if seen and float(total).is_integer() else (str(total) if seen else ""))
            jami_row += summed

        # Only write Jami if there were any plants or totals
        if plant_names or any(v not in (None, "") for v in jami_row[3:]):
            ws.append(jami_row)

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
