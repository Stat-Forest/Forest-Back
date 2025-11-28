from apps.reports.report_calculate.personal_resource.report_of_employee import calculate_hodimlar_hisobi
from apps.reports.report_calculate.personal_resource.report_of_employee_analysis import calculate_employee_analysis


calculators = {
    "Xodimlar hisobi": calculate_hodimlar_hisobi,
    "Учёт сотрудников": calculate_hodimlar_hisobi,
    "Xodimlar hisobi taxlili": calculate_employee_analysis,
    "Анализ учета кадров": calculate_employee_analysis
}