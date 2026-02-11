from collections import defaultdict
from decimal import Decimal
from django.db import transaction

from apps.utils.services.is_that_number import is_number


# ============================================================
# STRICT STATEMENT MATCH (ONLY 2 NAMES)
# ============================================================

SEED_NAME_UZ = "Urug' xarakati Reja"
HEAVY_NAME_UZ = "Og'ir mahalla"


def is_seed_statement(statement):
    name_uz = (getattr(statement, "name_uz", "") or "").strip()
    return name_uz == SEED_NAME_UZ


def is_heavy_neighborhood_statement(statement):
    name_uz = (getattr(statement, "name_uz", "") or "").strip()
    return name_uz == HEAVY_NAME_UZ


# ============================================================
# MAIN AGGREGATION
# ============================================================

@transaction.atomic
def aggregate_individual_report(source_report):
    from apps.reports.models import (
        Report,
        ReportItem,
        ReportItemInner,
        PlanItem,
        StatementColumn,
    )

    # --------------------------------------------------------
    # Reset previous individual report
    # --------------------------------------------------------
    Report.objects.filter(
        organization=source_report.organization,
        statement=source_report.statement,
        deadline=source_report.deadline,
        is_individual_general=True,
    ).delete()

    region = source_report.organization.region
    republic = source_report.organization.republic

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

    # --------------------------------------------------------
    # Preload statement columns
    # --------------------------------------------------------
    columns = list(
        StatementColumn.objects
        .filter(statement=source_report.statement)
        .only("id", "ordering")
    )

    ordering_by_col_id = {c.id: c.ordering for c in columns}
    columns_by_ordering = {c.ordering: c for c in columns}

    # --------------------------------------------------------
    # Pull source inners once
    # --------------------------------------------------------
    source_items = list(
        ReportItem.objects
        .filter(report=source_report)
        .only("id", "statement_column_id")
    )

    col_id_by_item_id = {i.id: i.statement_column_id for i in source_items}

    source_inners = list(
        ReportItemInner.objects
        .filter(report_item__report=source_report)
        .only("report_item_id", "value")
    )

    column_values_map = defaultdict(list)
    for inner in source_inners:
        col_id = col_id_by_item_id.get(inner.report_item_id)
        if col_id:
            column_values_map[col_id].append(inner.value)

    # --------------------------------------------------------
    # Statement types (ONLY 2 STATEMENTS)
    # --------------------------------------------------------
    seed_statement = is_seed_statement(source_report.statement)
    heavy_statement = is_heavy_neighborhood_statement(source_report.statement)

    # Ensure FOIZ/REJA required columns exist (ONLY for these statements)
    if seed_statement:
        foiz = columns_by_ordering.get("1.1.2.3")
        if foiz and foiz.id not in column_values_map:
            column_values_map[foiz.id] = []

    if heavy_statement:
        reja = columns_by_ordering.get("1.1.4")
        foiz = columns_by_ordering.get("1.1.6")
        if reja and reja.id not in column_values_map:
            column_values_map[reja.id] = []
        if foiz and foiz.id not in column_values_map:
            column_values_map[foiz.id] = []

    # --------------------------------------------------------
    # Create ReportItems
    # --------------------------------------------------------
    ReportItem.objects.bulk_create([
        ReportItem(report=individual_report, statement_column_id=cid)
        for cid in column_values_map.keys()
    ])

    created_items = list(
        ReportItem.objects.filter(report=individual_report)
        .only("id", "statement_column_id")
    )
    item_map = {i.statement_column_id: i for i in created_items}

    # --------------------------------------------------------
    # Load plan values:
    # IMPORTANT FIX:
    # For SEED + HEAVY => take LATEST Plan.year (NOT deadline year!)
    # --------------------------------------------------------
    relevant_col_ids = list(column_values_map.keys())

    plan_values_by_col_id = {}

    if relevant_col_ids:
        if seed_statement or heavy_statement:
            # ✅ take latest plan per column (postgres distinct-on pattern)
            # this fixes: deadline=2025 but plan.year=2026
            plan_qs = (
                PlanItem.objects
                .filter(
                    plan__statement=source_report.statement,
                    plan__organization=source_report.organization,
                    column_id__in=relevant_col_ids,
                )
                .order_by("column_id", "-plan__year")
                .distinct("column_id")
                .values_list("column_id", "plan_value")
            )
            plan_values_by_col_id = {
                col_id: (val or Decimal("0"))
                for col_id, val in plan_qs
            }
        else:
            # ❗ other statements: keep old behavior (deadline year based)
            # (we do NOT change anything for others)
            year = int(str(source_report.deadline.submit_at).split("-")[0])
            plan_qs = (
                PlanItem.objects
                .filter(
                    plan__statement=source_report.statement,
                    plan__organization=source_report.organization,
                    plan__year=year,
                    column_id__in=relevant_col_ids,
                )
                .values_list("column_id", "plan_value")
            )
            plan_values_by_col_id = {
                col_id: (val or Decimal("0"))
                for col_id, val in plan_qs
            }

    # --------------------------------------------------------
    # Build inners
    # --------------------------------------------------------
    new_inners = []

    for column_id, values in column_values_map.items():
        ordering = ordering_by_col_id.get(column_id, "")
        value = "0"

        # ====================================================
        # 🌱 Urug' xarakati Reja ONLY
        # ====================================================
        if seed_statement:
            if ordering == "1.1.2.1":  # REJA (must come from plan)
                value = str(plan_values_by_col_id.get(column_id, Decimal("0")))
            elif ordering == "1.1.2.3":  # FOIZ
                value = "0"
            else:  # AMALDA
                nums = [Decimal(str(v)) for v in values if is_number(v)]
                value = str(sum(nums)) if nums else "0"

        # ====================================================
        # 🏘 Og'ir mahalla ONLY
        # ====================================================
        elif heavy_statement:
            if ordering == "1.1.4":  # REJA (from plan)
                value = str(plan_values_by_col_id.get(column_id, Decimal("0")))
            elif ordering == "1.1.6":  # FOIZ
                value = "0"
            else:
                nums = [Decimal(str(v)) for v in values if is_number(v)]
                value = str(sum(nums)) if nums else "0"

        # ====================================================
        # 🧱 ALL OTHER STATEMENTS (UNCHANGED)
        # ====================================================
        else:
            nums = [Decimal(str(v)) for v in values if is_number(v)]
            value = str(sum(nums)) if nums else "0"

        new_inners.append(
            ReportItemInner(
                report_item=item_map[column_id],
                value=value,
            )
        )

    ReportItemInner.objects.bulk_create(new_inners)

    # --------------------------------------------------------
    # Final calculators (only for these statements)
    # --------------------------------------------------------
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
