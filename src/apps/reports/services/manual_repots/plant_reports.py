from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from apps.reports.models import ReportItem, ReportItemInner, StatementColumn, Plant


def normalize(val) -> Decimal:
    try:
        if val is None or val == "":
            return Decimal("0")
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def calculate_plant_by_expressions(report):
    expr_text = report.statement.calculate_expression
    if not expr_text:
        return

    # === ReportItemlarni yuklab olish
    report_items = (
        report.report_items
        .select_related("statement_column")
        .prefetch_related("inners__plant")
    )

    report_item_map = {
        item.statement_column.ordering: item
        for item in report_items
    }

    statement_column_map = {
        col.ordering: col
        for col in StatementColumn.objects.filter(statement=report.statement)
    }

    # ✅ Faqat shu statementga tegishli o‘simliklar
    plants = Plant.objects.filter(
        plant_columns__column__statement=report.statement
    ).distinct()
    plant_ids = [str(p.id) for p in plants]

    # ✅ Inner cache
    report_inners_cache: dict[str, dict[str, ReportItemInner]] = {}
    for ordering, item in report_item_map.items():
        report_inners_cache[ordering] = {
            str(inner.plant_id): inner
            for inner in item.inners.all() if inner.plant_id
        }

    # === plantlik column qiymatini olish
    def column(ordering: str, plant_id):
        plant_id = str(plant_id)
        inners = report_inners_cache.get(ordering, {})
        inner = inners.get(plant_id)
        return normalize(inner.value) if inner else Decimal("0")

    # === natijani DBga yozish
    def assign(ordering: str, values_map: dict[str, Decimal]):
        statement_col = statement_column_map.get(ordering)
        if not statement_col:
            print(f"⚠ Column not found for ordering: {ordering}")
            return

        item = report_item_map.get(ordering)
        if not item:
            item, _ = ReportItem.objects.get_or_create(
                report=report,
                statement_column=statement_col
            )
            report_item_map[ordering] = item
            report_inners_cache[ordering] = {}

        existing = report_inners_cache[ordering]
        to_update, to_create = [], []

        for plant_id, val in values_map.items():
            val = val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            val_str = str(val)

            if plant_id in existing:
                existing[plant_id].value = val_str
                to_update.append(existing[plant_id])
            else:
                new = ReportItemInner(
                    report_item=item,
                    plant_id=plant_id,
                    value=val_str
                )
                existing[plant_id] = new
                to_create.append(new)

        if to_update:
            ReportItemInner.objects.bulk_update(to_update, ["value"])
        if to_create:
            ReportItemInner.objects.bulk_create(to_create)

    # === Eval-safe context
    safe_globals = {
        "__builtins__": {},
        "Decimal": Decimal,
    }

    # === Expressionlarni bajarish
    for line in expr_text.splitlines():
        line = line.strip()
        if "=" not in line:
            continue

        expression, target = map(str.strip, line.split("="))
        result_map = {}

        for plant_id in plant_ids:

            # ✅ FIX: plant_id closure-ni muzlatib qo'yamiz
            def column_fn(ordering, pid=plant_id):
                return column(ordering, pid)

            try:
                result = eval(
                    expression,
                    safe_globals,
                    {"column": column_fn}
                )
            except Exception as e:
                print(f"❌ Eval error for {plant_id}: {e}")
                result = Decimal("0")

            result_map[plant_id] = normalize(result)

        # Target ordering maydonini tozalash
        target_ordering = (
            target.replace("column(", "")
            .replace(")", "")
            .replace("'", "")
            .replace('"', "")
            .strip()
        )

        assign(target_ordering, result_map)
