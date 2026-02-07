# apps/information_analytical/services/monitoring_engine.py

from decimal import Decimal

from apps.information_analytical.mapping import MAPPING_RULES, FORMULA_BLOCKS
from apps.information_analytical.serializers.forest_monitoring import set_by_path
from apps.information_analytical.serializers.report_values import to_decimal


def safe_percent(am, reja):
    am_d = to_decimal(am)
    reja_d = to_decimal(reja)
    if not am_d or not reja_d or reja_d == 0:
        return ""
    return (am_d / reja_d) * Decimal("100")


def safe_diff(reja, am):
    reja_d = to_decimal(reja)
    am_d = to_decimal(am)
    if reja_d is None or am_d is None:
        return ""
    return reja_d - am_d


def apply_mapping_to_target(*, target_value_map, sources_value_maps):
    """
    target_value_map: dict[ordering -> value]  (Axborot statement)
    sources_value_maps: dict[source_statement_id -> dict[ordering -> value]]
    """
    # direct fills
    for rule in MAPPING_RULES:
        src_statement_id = rule["source_statement_id"]  # view ichida qo‘shib beramiz
        src_ordering = rule["source"]
        tgt_ordering = rule["target"]

        src_map = sources_value_maps.get(src_statement_id, {})
        target_value_map[tgt_ordering] = src_map.get(src_ordering, "")

    # formulas
    for reja_o, am_o, pct_o, diff_o in FORMULA_BLOCKS:
        reja = target_value_map.get(reja_o, "")
        am = target_value_map.get(am_o, "")

        target_value_map[pct_o] = safe_percent(am, reja)
        target_value_map[diff_o] = safe_diff(reja, am)

    return target_value_map


def materialize_result_from_value_map(*, skeleton, leaf_paths, value_map):
    """
    skeleton: nested dict (titles)
    leaf_paths: ordering -> path_titles
    Optimized version
    """
    # Shallow copy ishlatish
    import copy
    result = copy.deepcopy(skeleton)

    # Faqat bo'sh bo'lmagan qiymatlarni qo'shish
    for ordering, path in leaf_paths.items():
        val = value_map.get(ordering)
        if val is not None and val != "":
            set_by_path(result, path, val)

    return result
