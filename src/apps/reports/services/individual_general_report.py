from collections import defaultdict
from decimal import Decimal
from django.db import transaction

from apps.utils.services.is_that_number import is_number


def get_year_from_deadline(deadline):
    """
    Deadline.submit_at dan YYYY ni ajratib olish
    """
    if not deadline.submit_at:
        raise ValueError("Deadline.submit_at is empty")
    year_str = str(deadline.submit_at).strip().split("-")[0]
    return int(year_str)


def is_seed_statement(statement):
    """
    Urug' xarakati Reja ni aniq (explicit) identifikatsiya qilish.
    Global plan logikasi faqat shu statement uchun qo'llanadi.
    """
    # Explicit statement-level check: prefer code, fallback to name match.
    code = getattr(statement, "code", None)
    name = (getattr(statement, "name", None) or "").strip().lower()

    # Whitelist known identifiers for seed movement plan
    SEED_CODES = {"seed_movement_plan", "seed_movement", "urug_xarakati_reja"}
    SEED_NAMES = {"urug' xarakati reja", "urug xarakati reja"}

    if code and code in SEED_CODES:
        return True
    if name in SEED_NAMES:
        return True
    return False


def is_heavy_neighborhood_statement(statement):
    """
    Og'ir mahalla ni aniq (explicit) identifikatsiya qilish.
    Global plan logikasi faqat shu statement uchun (agar qo'llansa) cheklanadi.
    """
    # Explicit statement-level check: prefer code, fallback to name match.
    code = getattr(statement, "code", None)
    name = (getattr(statement, "name", None) or "").strip().lower()

    HEAVY_CODES = {"heavy_neighborhood", "ogir_mahalla"}
    HEAVY_NAMES = {"og'ir mahalla", "ogir mahalla"}

    if code and code in HEAVY_CODES:
        return True
    if name in HEAVY_NAMES:
        return True
    return False


@transaction.atomic
def aggregate_individual_report(source_report):
    from apps.reports.models import (
        Report, ReportItem, ReportItemInner,
        PlanItem, StatementColumn
    )

    # 1️⃣ Eski individual general reportni o‘chiramiz
    Report.objects.filter(
        organization=source_report.organization,
        statement=source_report.statement,
        deadline=source_report.deadline,
        is_individual_general=True
    ).delete()

    # 2️⃣ Yangi individual general report yaratamiz
    region = source_report.organization.region if source_report.organization else source_report.region
    republic = source_report.organization.republic if source_report.organization else source_report.republic

    individual_report = Report.objects.create(
        organization=source_report.organization,
        statement=source_report.statement,
        deadline=source_report.deadline,
        status=Report.StatusChoices.SAVED,
        is_general=False,
        is_individual_general=True,
        is_report=False,
        region=region,
        republic=republic,
    )

    # 3️⃣ Source reportdan qiymatlarni yig‘amiz (preload EVERYTHING once)
    # Columns for the statement
    columns = list(
        StatementColumn.objects
        .filter(statement=source_report.statement)
        .only("id", "ordering")
    )
    columns_by_id = {c.id: c for c in columns}
    columns_by_ordering = {c.ordering: c for c in columns}

    # Map report_item.id -> statement_column_id
    source_items = list(
        ReportItem.objects
        .filter(report=source_report)
        .only("id", "statement_column_id")
    )
    col_id_by_item_id = {it.id: it.statement_column_id for it in source_items}

    # Pull all inners once and build column_values_map without touching ORM in loops
    source_inners = list(
        ReportItemInner.objects
        .filter(report_item__report=source_report)
        .only("id", "report_item_id", "value")
    )
    column_values_map = defaultdict(list)
    for inner in source_inners:
        col_id = col_id_by_item_id.get(inner.report_item_id)
        if col_id:
            column_values_map[col_id].append(inner.value)

    # Statement turlari
    seed_statement = is_seed_statement(source_report.statement)
    heavy_statement = is_heavy_neighborhood_statement(source_report.statement)

    # Seed statement uchun FOIZ ustuni majburiy
    if seed_statement:
        foiz_col = columns_by_ordering.get("1.1.2.3")
        if foiz_col and foiz_col.id not in column_values_map:
            column_values_map[foiz_col.id] = []

    # Og'ir mahalla uchun: REJA (1.1.4) va FOIZ (1.1.6) ustunlarini majburiy qo'shamiz
    if heavy_statement:
        reja_col = columns_by_ordering.get("1.1.4")
        if reja_col and reja_col.id not in column_values_map:
            column_values_map[reja_col.id] = []

        foiz_col = columns_by_ordering.get("1.1.6")
        if foiz_col and foiz_col.id not in column_values_map:
            column_values_map[foiz_col.id] = []

    # 4️⃣ ReportItem larni yaratamiz
    new_items = [
        ReportItem(report=individual_report, statement_column_id=cid)
        for cid in column_values_map.keys()
    ]
    ReportItem.objects.bulk_create(new_items)

    # Preload created items and rely only on *_id fields to avoid FK dereferencing
    created_items = list(ReportItem.objects.filter(report=individual_report).only("id", "statement_column_id"))
    item_map = {i.statement_column_id: i for i in created_items}

    # Reuse already preloaded statement columns for ordering
    ordering_by_col_id = {c.id: c.ordering for c in columns}

    # Preload PlanItem values once for relevant columns (by current statement, org, year)
    plan_year = get_year_from_deadline(source_report.deadline)
    relevant_col_ids = list(column_values_map.keys())
    plan_values_by_col_id = {}
    if relevant_col_ids:
        plan_qs = (
            PlanItem.objects
            .filter(
                plan__statement=source_report.statement,
                plan__organization=source_report.organization,
                plan__year=plan_year,
                column_id__in=relevant_col_ids,
            )
            .values_list("column_id", "plan_value")
        )
        plan_values_by_col_id = {col_id: (val or Decimal("0")) for col_id, val in plan_qs}

    new_inners = []

    # 5️⃣ Inners qiymatlarini tayyorlaymiz
    for column_id, values in column_values_map.items():
        report_item = item_map[column_id]
        value = "0"
        # Use preloaded ordering map instead of touching report_item.statement_column
        ordering = ordering_by_col_id.get(report_item.statement_column_id, "")

        # 🌱 Urug' xarakati Reja
        if seed_statement:
            if ordering == "1.1.2.1":  # REJA
                plan_value = plan_values_by_col_id.get(column_id, Decimal("0"))
                value = str(plan_value or Decimal("0"))
            elif ordering == "1.1.2.3":  # FOIZ
                value = "0"
            else:  # AMALDA
                nums = [Decimal(str(v)) for v in values if is_number(v)]
                value = str(sum(nums)) if nums else "0"

        # 🏘 Og‘ir mahalla
        elif heavy_statement:
            if ordering == "1.1.4":  # REJA (plan from PlanItem, like seed statement)
                plan_value = plan_values_by_col_id.get(column_id, Decimal("0"))
                value = str(plan_value or Decimal("0"))
            elif ordering == "1.1.6":  # FOIZ only calculated later
                value = "0"
            else:  # AMALDA
                nums = [Decimal(str(v)) for v in values if is_number(v)]
                value = str(sum(nums)) if nums else "0"

        # 🧱 Oddiy statement
        else:
            nums = [Decimal(str(v)) for v in values if is_number(v)]
            value = str(sum(nums)) if nums else "0"

        new_inners.append(
            ReportItemInner(report_item=report_item, value=value)
        )

    ReportItemInner.objects.bulk_create(new_inners)

    # 6️⃣ Calculator chaqirish (SOURCE OF TRUTH)
    if seed_statement:
        from apps.reports.report_calculate.forest_create.seed_movement_plan import (
            calculate_seed_movement_plan,
        )
        calculate_seed_movement_plan(individual_report)

    elif heavy_statement:
        from apps.reports.report_calculate.forest_create.heavy_neighborhood import (
            calculate_heavy_neighborhood,
        )
        calculate_heavy_neighborhood(individual_report)

    return individual_report
