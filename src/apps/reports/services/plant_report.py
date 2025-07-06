from apps.reports.models import Report, ReportItem, StatementColumn
from apps.utils.services.find_statement_column import get_root_column


def get_or_create_report_and_columns(deadline, organization):
    report, created = Report.objects.get_or_create(
        deadline=deadline,
        organization=organization,
        statement=deadline.statement,
        defaults={"status": Report.StatusChoices.SAVED},
    )

    result = []

    if not created:
        report_items = report.report_items.select_related("statement_column", "plant")
        column_map = {}
        for item in report_items:
            col_id = str(item.statement_column_id)
            if col_id not in column_map:
                column_map[col_id] = {
                    "statement_column_id": col_id,
                    "statement_column_name": item.statement_column.title_uz,
                    "plant_values": []
                }
            column_map[col_id]["plant_values"].append({
                "plant_id": str(item.plant.id),
                "plant_name": item.plant.name,
                "value": item.value
            })
        return report, list(column_map.values())

    items_to_create = []
    statement_columns = StatementColumn.objects.filter(statement=deadline.statement)

    for column in statement_columns:
        root = get_root_column(column)
        if root.title_uz.strip().lower() not in {"ko‘chat", "nihol", "ko‘chat ва ниҳол"}:
            continue

        column_plants = column.column_plants.select_related("plant").all()
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
