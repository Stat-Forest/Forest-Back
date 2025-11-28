from apps.reports.report_calculate.forest_cadastre.land_account import calculate_leased_land
from apps.reports.report_calculate.forest_cadastre.land_acquisition import calculate_land

calculators = {
    "Yer o‘zlashtirish": calculate_land,
    "Освоение земель": calculate_land,
    "Ijaraga berilgan yerlar hisobi": calculate_leased_land,
    "Учет арендованных земель": calculate_leased_land
}