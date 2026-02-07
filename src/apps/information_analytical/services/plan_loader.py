from collections import defaultdict
from apps.reports.models import PlanItem, PlantPlanItem


def load_plan_maps(org_ids, statement_ids):
    """
    Returns:
      plan_map[(org_id, statement_id)][ordering] = value
      plant_plan_map[(org_id, statement_id)][plant_id][ordering] = value
    """
    plan_map = {}
    plant_plan_map = {}
    # ====== ODDIY PLAN ======
    plan_items = (
        PlanItem.objects
        .filter(
            plan__organization_id__in=org_ids,
            plan__statement_id__in=statement_ids
        )
        .select_related("column", "plan")
    )

    plan_map = defaultdict(dict)

    for pi in plan_items:
        key = (pi.plan.organization_id, pi.plan.statement_id)
        plan_map[key][pi.column.ordering] = str(pi.plan_value)

    # ====== PLANT PLAN ======
    plant_items = (
        PlantPlanItem.objects
        .filter(
            plant_plan__plan__organization_id__in=org_ids,
            plant_plan__plan__statement_id__in=statement_ids
        )
        .select_related(
            "column",
            "plant_plan",
            "plant_plan__plant",
            "plant_plan__plan"
        )
    )

    plant_plan_map = defaultdict(lambda: defaultdict(dict))

    for ppi in plant_items:
        key = (
            ppi.plant_plan.plan.organization_id,
            ppi.plant_plan.plan.statement_id
        )

        plant_id = ppi.plant_plan.plant_id
        plant_plan_map[key][plant_id][ppi.column.ordering] = str(ppi.plan_value)

    return plan_map, plant_plan_map
