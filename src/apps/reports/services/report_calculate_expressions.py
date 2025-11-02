from decimal import Decimal, ROUND_HALF_UP
from apps.reports.models import ReportItem, ReportItemInner, StatementColumn
from apps.utils.translation import get_translated_field, get_lang_code
from collections import defaultdict


def calculate_by_expressions(report):
    expr_text = report.statement.calculate_expression
    if not expr_text:
        return

    lang = get_lang_code("uz")

    report_items = (
        report.report_items
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    report_item_map = {item.statement_column.ordering: item for item in report_items}
    statement_column_map = {
        col.ordering: col for col in StatementColumn.objects.filter(statement=report.statement)
    }

    # Avvaldan barcha inners ni cache qilib olamiz
    report_inners_cache: dict[str, list[ReportItemInner]] = {}
    for ordering, item in report_item_map.items():
        report_inners_cache[ordering] = list(item.inners.all())

    def get_inners(ordering):
        return report_inners_cache.get(ordering, [])

    def column(ordering: str, idx: int) -> Decimal:
        inners = get_inners(ordering)
        if idx >= len(inners):
            return Decimal("0")
        try:
            return Decimal(inners[idx].value or "0")
        except Exception:
            return Decimal("0")

    # Asosiy assign
    def assign(ordering: str, values: list[Decimal]):
        statement_col = statement_column_map.get(ordering)
        if not statement_col:
            print(f"⚠ Column not found: {ordering}")
            return

        item = report_item_map.get(ordering)
        if not item:
            item, _ = ReportItem.objects.get_or_create(
                report=report,
                statement_column=statement_col
            )
            report_item_map[ordering] = item
            report_inners_cache[ordering] = []
        inners = report_inners_cache[ordering]
        existing_len = len(inners)

        is_org_col = statement_col.is_organization
        title_uz = (statement_col.title_uz or "").lower().strip()
        if is_org_col and "tashkilot" in title_uz:
            if inners:
                inners[0].value = get_translated_field(report.organization, "name", lang)
                ReportItemInner.objects.bulk_update([inners[0]], ["value"])
            return

        to_update = []
        to_create = []

        for i, val in enumerate(values):
            val = val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            val = str(val)

            if i < existing_len:
                inners[i].value = val
                to_update.append(inners[i])
            else:
                new_inner = ReportItemInner(report_item=item, value=val)
                to_create.append(new_inner)

        if to_update:
            ReportItemInner.objects.bulk_update(to_update, ["value"])
        if to_create:
            ReportItemInner.objects.bulk_create(to_create)

        # Cache yangilaymiz
        report_inners_cache[ordering] = inners[:len(values)] + to_create

    # === Formula bajarish ===
    for line in expr_text.splitlines():
        line = line.strip()
        if "=" not in line:
            continue

        expression, target = line.split("=")
        expression = expression.strip()
        target = target.strip()

        parts = expression.split("column(")
        source_orderings = []
        for p in parts[1:]:
            o = p.split(")")[0].replace('"', '').replace("'", "").strip()
            source_orderings.append(o)

        max_len = max(len(get_inners(o)) for o in source_orderings)

        results = []
        for i in range(max_len):
            try:
                res = eval(
                    expression,
                    {"__builtins__": {}, "Decimal": Decimal},
                    {"column": lambda ordering: column(ordering, i)}
                )
            except Exception:
                res = Decimal("0")
            results.append(res)

        target_ordering = (
            target.replace("column(", "")
                  .replace(")", "")
                  .replace('"', "")
                  .replace("'", "")
                  .strip()
        )

        assign(target_ordering, results)
