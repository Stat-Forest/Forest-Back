from typing import Dict, List

from apps.reports.models import Statement, StatementColumn
from apps.utils.translation import get_translated_field


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
    appendices = get_statement_appendices(statement)
    payload = {
        "statement_id": str(statement.id),
        "appendices": []
    }

    for app in appendices:
        app_block = {
            "id": str(app.id),
            "ordering": app.ordering or "0",
            "name": get_translated_field(app, "title", lang),
            "columns": []
        }
        for leaf in get_leaf_columns_for_appendix(statement, app):
            app_block["columns"].append({
                "id": str(leaf.id),
                "ordering": leaf.ordering or "0",
                "name": get_translated_field(leaf, "title", lang),
                "value": None,
            })
        payload["appendices"].append(app_block)

    return payload
