from decimal import Decimal, ROUND_HALF_UP
from apps.reports.models import ReportItem, ReportItemInner, StatementColumn


def calculate_by_expressions(report):
    expr_text = report.statement.calculate_expression
    if not expr_text:
        return

    # ✅ Bulk select: ReportItem + StatementColumn + Inners
    report_items = (
        report.report_items
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    # ✅ Cachega mapping qilish
    report_item_map = {item.statement_column.ordering: item for item in report_items}
    statement_column_map = {
        col.ordering: col for col in StatementColumn.objects.filter(statement=report.statement)
    }

    def column(ordering: str) -> Decimal:
        item = report_item_map.get(ordering)
        if not item:
            return Decimal("0")

        inners = list(item.inners.all())
        if not inners:
            return Decimal("0")

        try:
            return Decimal(inners[0].value or "0")
        except Exception:
            return Decimal("0")

    def assign(ordering: str, value: Decimal):
        try:
            value = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            item = report_item_map.get(ordering)

            if not item:
                statement_col = statement_column_map.get(ordering)
                if not statement_col:
                    print(f"⚠️ Column not found: ordering={ordering}")
                    return

                item, _ = ReportItem.objects.get_or_create(
                    report=report,
                    statement_column=statement_col
                )
                report_item_map[ordering] = item  # cachega qo‘sh

            inners = list(item.inners.all())
            if inners:
                inners[0].value = str(value)
                inners[0].save(update_fields=["value"])
            else:
                ReportItemInner.objects.create(
                    report_item=item,
                    value=str(value)
                )

        except Exception as e:
            print(f"❌ Assign error for ordering {ordering}: {e}")

    # ✅ Formulalarni bajarish
    for line in expr_text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue

        try:
            expression, target = line.split("=")
            eval_globals = {
                "__builtins__": {},
                "column": column,
                "Decimal": Decimal,
                "round": round,
            }
            result = eval(expression.strip(), eval_globals)

            target_ordering = (
                target.strip()
                .replace("column(", "")
                .replace(")", "")
                .replace("'", "")
                .replace('"', "")
            )
            assign(target_ordering, result)
        except Exception as e:
            print(f"❌ Expression error in line: {line} — {e}")
