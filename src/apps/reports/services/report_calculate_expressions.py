from apps.reports.services.manual_repots.plant_reports import calculate_plant_by_expressions
from apps.reports.services.manual_repots.simple_reports import calculate_normal_by_expressions


def calculate_by_expressions(report):
    # if report.is_plant_based:
        # return calculate_plant_by_expressions(report)
    return calculate_normal_by_expressions(report)
