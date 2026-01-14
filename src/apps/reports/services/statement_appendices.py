from typing import Dict, List
from collections import defaultdict

from apps.utils.translation import get_translated_field
from apps.reports.models import Statement, StatementColumn


def get_statement_appendices(statement: Statement) -> List[StatementColumn]:
    return list(
        StatementColumn.objects
        .filter(statement=statement, parent__isnull=True)
        .order_by("ordering")
    )


def _build_parent_map(statement: Statement) -> Dict[str, str]:
    """Return map child_id -> parent_id for all columns of the statement."""
    cols = StatementColumn.objects.filter(statement=statement).only("id", "parent_id")
    return {str(c.id): (str(c.parent_id) if c.parent_id else None) for c in cols}


def _top_level_parent_id(col_id: str, parent_map: Dict[str, str]) -> str:
    current = col_id
    seen = set()
    while True:
        if current in seen:
            # Defensive against cycles
            return current
        seen.add(current)
        parent = parent_map.get(current)
        if not parent:
            return current
        current = parent


def get_leaf_columns_for_appendix(statement: Statement, appendix: StatementColumn) -> List[StatementColumn]:
    """
    Return ONLY leaf columns that belong to the given appendix subtree.
    Leaf means children__isnull=True.
    No tree fields available, so we compute by walking parents in Python.
    """
    parent_map = _build_parent_map(statement)

    leaves = list(
        StatementColumn.objects
        .filter(statement=statement, children__isnull=True)
        .order_by("ordering")
        .distinct()
    )

    app_id = str(appendix.id)
    result: List[StatementColumn] = []
    for leaf in leaves:
        top_parent = _top_level_parent_id(str(leaf.id), parent_map)
        if top_parent == app_id:
            result.append(leaf)
    return result



def build_appendices_payload(statement: Statement, lang: str) -> dict:
    """
    OPTIMIZED:
    - StatementColumn faqat 1 marta DB’dan olinadi
    - Hech qanday duplicate query yo‘q
    - Tree va leaf aniqlash RAM’da qilinadi
    """

    # 🔹 1. BARCHA COLUMNLARNI 1 MARTA OLAMIZ
    columns = list(
        StatementColumn.objects
        .filter(statement=statement)
        .order_by("ordering")
    )

    # 🔹 2. MAP’LAR
    column_by_id = {c.id: c for c in columns}
    children_map = defaultdict(list)

    for c in columns:
        if c.parent_id:
            children_map[c.parent_id].append(c)

    # 🔹 3. APPENDIXLAR (TOP-LEVEL PARENTLAR)
    # (ya’ni parent=None bo‘lganlar)
    appendices = [
        c for c in columns
        if c.parent_id is None
    ]

    payload = {
        "statement_id": str(statement.id),
        "appendices": [],
    }

    # 🔹 4. HAR BIR APPENDIX UCHUN LEAF’LARNI RAM’DA ANIQLAYMIZ
    for app in appendices:
        app_block = {
            "id": str(app.id),
            "ordering": app.ordering or "0",
            "name": get_translated_field(app, "title", lang),
            "columns": [],
        }

        # DFS orqali shu appendix ostidagi leaf’lar
        stack = children_map.get(app.id, []).copy()

        while stack:
            col = stack.pop()

            children = children_map.get(col.id)
            if not children:
                # 🔥 LEAF COLUMN
                app_block["columns"].append({
                    "id": str(col.id),
                    "ordering": col.ordering or "0",
                    "name": get_translated_field(col, "title", lang),
                    "value": None,
                })
            else:
                stack.extend(children)

        payload["appendices"].append(app_block)

    return payload

