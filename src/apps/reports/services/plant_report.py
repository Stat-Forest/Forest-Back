from django.db import models

from apps.reports.models import StatementColumn, Report, ReportItem, ColumnPlant
from apps.reports.services.get_leaf_columns import get_leaf_columns_under_ilova_root


def get_or_create_report_and_columns(deadline, organization, ilova_title_uz: str):

    report, created = Report.objects.get_or_create(
        deadline=deadline,
        organization=organization,
        statement=deadline.statement,
        defaults={"status": Report.StatusChoices.SAVED},
    )

    try:
        ilova_root = StatementColumn.objects.get(
            statement=deadline.statement,
            title_uz__iexact=ilova_title_uz,
            parent__isnull=True
        )
    except StatementColumn.DoesNotExist:
        return report, []

    if not created:
        existing_items = ReportItem.objects.filter(
            report=report,
            statement_column__in=StatementColumn.objects.filter(statement=deadline.statement)
        ).select_related("statement_column", "plant")

        result = {}
        for item in existing_items:
            col_id = str(item.statement_column_id)
            if col_id not in result:
                result[col_id] = {
                    "statement_column_id": col_id,
                    "statement_column_name": item.statement_column.title_uz,
                    "plant_values": []
                }
            result[col_id]["plant_values"].append({
                "plant_id": str(item.plant.id),
                "plant_name": item.plant.name,
                "value": item.value
            })
        return report, list(result.values())

    # get all leaf columns under ilova root
    leaf_columns = get_leaf_columns_under_ilova_root(ilova_root).prefetch_related(
        models.Prefetch(
            'column_plants',
            queryset=ColumnPlant.objects.select_related('plant').order_by('ordering')
        )
    )

    items_to_create = []
    result = []

    for column in leaf_columns:
        column_plants = column.column_plants.select_related("plant").all()
        if not column_plants:
            continue

        plant_values = []
        for cp in column_plants:
            items_to_create.append(ReportItem(
                report=report,
                statement_column=column,
                plant=cp.plant,
                value=None
            ))
            plant_values.append({
                "plant_id": str(cp.plant.id),
                "plant_name": cp.plant.name,
                "value": None
            })

        result.append({
            "statement_column_id": str(column.id),
            "statement_column_name": column.title_uz,
            "plant_values": plant_values
        })

    ReportItem.objects.bulk_create(items_to_create)

    return report, result
