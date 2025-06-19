from uuid import UUID


def process_plant_values(report, statement_column, plant_value_list):
    from apps.reports.models import Plant, ReportItem

    parent_totals = {}
    total_duh = 0.0

    # Plantlar bazadan olish
    plant_ids = [UUID(i['plant_id']) for i in plant_value_list]
    plant_map = Plant.objects.in_bulk(plant_ids)

    # 1. Child plantlarni yaratish + parent yig‘ish
    for item in plant_value_list:
        plant_id = UUID(item["plant_id"])
        value = float(item["value"])
        plant = plant_map.get(plant_id)

        ReportItem.objects.create(
            report=report,
            statement_column=statement_column,
            value=value,
            plant=plant
        )

        if plant and plant.parent_id:
            parent_totals[plant.parent_id] = parent_totals.get(plant.parent_id, 0.0) + value

    # 2. Parent plantlar uchun ReportItem yaratish va DUH yig‘ish
    if parent_totals:
        parent_map = Plant.objects.in_bulk(parent_totals.keys())
        for parent_id, total in parent_totals.items():
            parent_plant = parent_map.get(parent_id)
            if parent_plant:
                ReportItem.objects.create(
                    report=report,
                    statement_column=statement_column,
                    value=total,
                    plant=parent_plant
                )
                total_duh += total

    # 3. Xo‘jalik DUX uchun ReportItem yaratish
    if total_duh:
        duh_plant = Plant.objects.filter(name="Хўжалик ДЎХ").first()
        if duh_plant:
            ReportItem.objects.create(
                report=report,
                statement_column=statement_column,
                value=total_duh,
                plant=duh_plant
            )
