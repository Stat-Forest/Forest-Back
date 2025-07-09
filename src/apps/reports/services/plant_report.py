from apps.reports.models import Report, ReportItem, StatementColumn


def get_or_create_report_and_columns(deadline, organization, ilova_title_uz: str):
    """
    Faqat `ilova_title_uz` (masalan, "Ko‘chat-ilovasi") ostidagi leaf columnlar uchun
    ColumnPlant orqali plant asosida ReportItem larni yaratadi yoki mavjudlarini qaytaradi.
    """
    report, created = Report.objects.get_or_create(
        deadline=deadline,
        organization=organization,
        statement=deadline.statement,
        defaults={"status": Report.StatusChoices.SAVED},
    )

    if not created:
        existing_items = report.report_items.select_related("statement_column", "plant")
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

    try:
        ilova_root = StatementColumn.objects.get(
            statement=deadline.statement,
            title_uz__iexact=ilova_title_uz,
            parent__isnull=True
        )
    except StatementColumn.DoesNotExist:
        return report, []

    all_columns = StatementColumn.objects.filter(
        statement=deadline.statement
    ).select_related("parent")

    leaf_columns = [
        col for col in all_columns
        if col.parent and col.parent.parent_id == ilova_root.id and not col.children.exists()
    ]

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
