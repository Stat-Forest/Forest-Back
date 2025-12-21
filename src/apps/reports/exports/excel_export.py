import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, Set

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from django.conf import settings


def _ordering_key(ordering: str) -> tuple:
    """
    '1.2.10' -> (1,2,10)
    '2.A.1' -> (2,'A',1)
    """
    parts = []
    for p in (ordering or "").strip().split("."):
        if p.isdigit():
            parts.append(int(p))
        else:
            parts.append(p)
    return tuple(parts)


def _pick_best_value(inners: list) -> str:
    """
    inners = [{"value": "5"}, {"value": "6"}] bo‘lishi mumkin.
    - Agar 1 ta bo‘lsa: o‘sha
    - Agar numeric ko‘p bo‘lsa: sum
    - Aks holda: birinchi non-empty value
    """
    if not inners:
        return ""

    values = []
    for it in inners:
        v = it.get("value")
        if v is None:
            v = ""
        values.append(str(v).strip())

    if len(values) == 1:
        return values[0]

    # numeric sum attempt
    def to_float(s: str):
        try:
            s2 = s.replace(" ", "").replace(",", ".")
            if s2 == "":
                return None
            return float(s2)
        except Exception:
            return None

    nums = [to_float(v) for v in values]
    if all(n is not None for n in nums):
        sm = sum(nums)  # type: ignore[arg-type]
        # 5.0 bo‘lsa 5 qilib chiqaramiz
        if abs(sm - int(sm)) < 1e-9:
            return str(int(sm))
        return str(sm)

    # fallback: first non-empty
    for v in values:
        if v != "":
            return v
    return ""


def export_universal_report_to_excel_v2(
    reports: List[Dict[str, Any]],
    *,
    filename_prefix: str = "report_export",
    lang: str = "uz",
    statement_id: Optional[str] = None,
) -> Tuple[str, str]:
    """
    ReportListSerializer.data dan kelgan list bo‘yicha Excel export.

    ✅ Header: StatementColumn parent/children bo‘yicha, MERGE bilan
    ✅ Header tree: faqat serializerda ishtirok etgan columnlar + ancestorlar
    ✅ is_organization columnlar headerga kiritilmaydi
    ✅ Row: har bir report = 1 qator (organization_name)
    """

    from apps.reports.models import StatementColumn  # local import

    # -----------------------
    # 0) Output path
    # -----------------------
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{now_str}.xlsx"
    export_dir = getattr(settings, "EXPORT_ROOT", os.path.join(settings.BASE_DIR, "exports"))
    os.makedirs(export_dir, exist_ok=True)
    file_path = os.path.join(export_dir, filename)

    # -----------------------
    # 1) Collect needed column ids from serializer
    # -----------------------
    needed_ids: Set[str] = set()
    for report in reports:
        for container in (report.get("report_items") or []):
            for col in (container.get("statement_columns") or []):
                cid = col.get("statement_column_id")
                if cid:
                    needed_ids.add(str(cid))

    if not needed_ids:
        # hech bo‘lmasa header uchun statement_id kerak
        wb = Workbook()
        ws = wb.active
        ws.title = "Reports"
        ws.append(["№", "Tashkilot nomi"])
        wb.save(file_path)
        return file_path, filename

    # statement_id topilmasa infer
    if not statement_id:
        any_id = next(iter(needed_ids))
        stmt = (
            StatementColumn.objects.filter(id=any_id)
            .values_list("statement_id", flat=True)
            .first()
        )
        statement_id = str(stmt) if stmt else None

    if not statement_id:
        raise ValueError("statement_id aniqlanmadi (StatementColumn.statement_id topilmadi).")

    # -----------------------
    # 2) Load all statement columns as instances (safe for missing fields)
    # -----------------------
    all_cols = list(
        StatementColumn.objects.filter(statement_id=statement_id)
        .select_related("parent")
        .only("id", "parent_id", "ordering", "title_uz", "title_ru")  # minimal
    )

    # Build id -> col
    id_map: Dict[str, Any] = {str(c.id): c for c in all_cols}

    # Helper: check is_organization, is_user_input safely
    def is_org(c) -> bool:
        return bool(getattr(c, "is_organization", False))

    # Export ids = needed_ids minus is_organization ones (agar serializerda kelib qolsa ham)
    export_ids: Set[str] = set()
    for cid in needed_ids:
        c = id_map.get(cid)
        if not c:
            continue
        if is_org(c):
            continue
        export_ids.add(cid)

    if not export_ids:
        # agar hammasi is_organization bo‘lib qolgan bo‘lsa, fallback: needed_ids
        export_ids = set(needed_ids)

    # -----------------------
    # 3) Include ancestors to build correct header tree
    # -----------------------
    included_ids: Set[str] = set(export_ids)

    for cid in list(export_ids):
        cur = id_map.get(cid)
        while cur and getattr(cur, "parent_id", None):
            pid = str(cur.parent_id)
            if pid not in id_map:
                break
            included_ids.add(pid)
            cur = id_map.get(pid)

    # Build children map only for included_ids, exclude is_organization children too
    children: Dict[Optional[str], List[Any]] = {}
    for cid in included_ids:
        c = id_map.get(cid)
        if not c:
            continue
        if is_org(c):
            continue
        pid = str(c.parent_id) if getattr(c, "parent_id", None) else None
        # parent included bo‘lmasa ham root sifatida chiqadi
        children.setdefault(pid, []).append(c)

    # Sort children by ordering
    for pid, lst in children.items():
        lst.sort(key=lambda x: _ordering_key(getattr(x, "ordering", "") or ""))

    # Roots: parent_id None yoki parent included emas
    roots = []
    for c in children.get(None, []):
        roots.append(c)

    # Yana: ba’zi node parent_id bor, lekin parent excluded bo‘lsa — root bo‘lishi kerak
    for cid in included_ids:
        c = id_map.get(cid)
        if not c or is_org(c):
            continue
        pid = getattr(c, "parent_id", None)
        if pid and (str(pid) not in included_ids):
            children.setdefault(None, []).append(c)

    # root listni qayta sort (yuqoridagidan keyin)
    children[None] = sorted(children.get(None, []), key=lambda x: _ordering_key(getattr(x, "ordering", "") or ""))

    # -----------------------
    # 4) Compute leaves (only export_ids that are leaf inside filtered tree)
    # -----------------------
    def dfs_leaves(node) -> List[Any]:
        nid = str(node.id)
        ch = children.get(nid, [])
        if not ch:
            # leaf bo‘lishi uchun u export_ids’da bo‘lsin
            return [node] if nid in export_ids else []
        res: List[Any] = []
        for sub in ch:
            res.extend(dfs_leaves(sub))
        return res

    leaves: List[Any] = []
    for r in children.get(None, []):
        leaves.extend(dfs_leaves(r))

    # Agar export_ids bor-u lekin tree’da leaf topilmasa (edge-case), fallback: export_ids ordering bo‘yicha
    if not leaves:
        leaves = [id_map[cid] for cid in export_ids if cid in id_map]
        leaves.sort(key=lambda x: _ordering_key(getattr(x, "ordering", "") or ""))

    leaf_ids = [str(c.id) for c in leaves]

    # -----------------------
    # 5) Header depth calc
    # -----------------------
    def depth(node) -> int:
        nid = str(node.id)
        ch = children.get(nid, [])
        if not ch:
            return 1
        return 1 + max(depth(sub) for sub in ch)

    max_depth = 1
    for r in children.get(None, []):
        max_depth = max(max_depth, depth(r))

    # -----------------------
    # 6) Prepare workbook + header grid
    # -----------------------
    wb = Workbook()
    ws = wb.active
    ws.title = "Reports"

    total_cols = 2 + len(leaf_ids)  # № + Tashkilot + leaf columns
    header_grid: List[List[str]] = [["" for _ in range(total_cols)] for _ in range(max_depth)]

    header_grid[0][0] = "№"
    header_grid[0][1] = "Tashkilot nomi" if lang == "uz" else "Наименование организации"

    def title_of(col) -> str:
        uz = getattr(col, "title_uz", "") or ""
        ru = getattr(col, "title_ru", "") or ""
        if lang == "ru":
            return ru or uz or str(col)
        return uz or ru or str(col)

    # span cache: number of leaf columns under node
    span_cache: Dict[str, int] = {}

    def span(node) -> int:
        nid = str(node.id)
        if nid in span_cache:
            return span_cache[nid]
        ch = children.get(nid, [])
        if not ch:
            # span 1 faqat leaf bo‘lsa (export leaf)
            span_cache[nid] = 1 if nid in leaf_ids else 0
            return span_cache[nid]
        s = 0
        for sub in ch:
            s += span(sub)
        span_cache[nid] = s
        return s

    merges: List[Tuple[int, int, int, int]] = []  # 1-based

    # place recursion
    def place(node, level: int, col_idx0: int) -> int:
        """
        col_idx0: 0-based index in grid
        returns next free col index after this node's span
        """
        nid = str(node.id)
        sp = span(node)
        if sp <= 0:
            return col_idx0

        header_grid[level][col_idx0] = title_of(node)

        ch = children.get(nid, [])
        if not ch:
            # vertical merge down to max_depth
            if level < max_depth - 1:
                merges.append((level + 1, col_idx0 + 1, max_depth, col_idx0 + 1))
            return col_idx0 + 1

        # horizontal merge across span
        if sp > 1:
            merges.append((level + 1, col_idx0 + 1, level + 1, col_idx0 + sp))

        cur = col_idx0
        for sub in ch:
            cur = place(sub, level + 1, cur)
        return col_idx0 + sp

    # Start placing roots at col 2 (0-based)
    cur_c = 2
    for r in children.get(None, []):
        cur_c = place(r, 0, cur_c)

    # write header rows
    for row in header_grid:
        ws.append(row)

    # merge fixed columns vertically
    merges.append((1, 1, max_depth, 1))
    merges.append((1, 2, max_depth, 2))

    # apply merges
    for r1, c1, r2, c2 in merges:
        if r2 > r1 or c2 > c1:
            ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)

    # header style
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    header_font = Font(bold=True)
    for row in ws.iter_rows(min_row=1, max_row=max_depth, min_col=1, max_col=total_cols):
        for cell in row:
            cell.alignment = header_alignment
            cell.font = header_font

    # freeze header
    ws.freeze_panes = ws.cell(row=max_depth + 1, column=3)

    # -----------------------
    # 7) Build per-report values map (col_id -> value)
    # -----------------------
    # NOTE: bu yerda ordering emas, BEVOSITA col_id ishlatyapmiz => 100% mos tushadi
    for idx, report in enumerate(reports, start=1):
        org_name = report.get("organization_name", "") or ""
        row = [idx, org_name]

        col_value_map: Dict[str, str] = {}
        for container in (report.get("report_items") or []):
            for col in (container.get("statement_columns") or []):
                cid = str(col.get("statement_column_id") or "")
                if not cid or cid not in leaf_ids:
                    continue
                inners = col.get("inners") or []
                col_value_map[cid] = _pick_best_value(inners)

        for cid in leaf_ids:
            row.append(col_value_map.get(cid, ""))

        ws.append(row)

    # -----------------------
    # 8) Auto-size columns (fast & safe)
    # -----------------------
    max_width = 60
    for col in range(1, ws.max_column + 1):
        letter = get_column_letter(col)
        best = 10
        # 300 qator bilan limit (performance)
        for r in range(1, min(ws.max_row, 300) + 1):
            v = ws.cell(row=r, column=col).value
            if v is None:
                continue
            best = max(best, len(str(v)))
        ws.column_dimensions[letter].width = min(best + 2, max_width)

    wb.save(file_path)
    return file_path, filename
