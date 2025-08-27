from apps.reports.report_calculate.forest_additional.create_additional_forest import calculate_additional
from apps.reports.report_calculate.forest_additional.create_haymaking import calculate_haymaking
from apps.reports.report_calculate.forest_additional.create_pasture import calculate_pasture
from apps.reports.report_calculate.forest_additional.create_beekeeping import calculate_beekeeping


calculators = {
    "Mexanizatsiya hisobi": calculate_additional,
    "Pichan o`rish": calculate_haymaking,
    "Yaylov hisoboti": calculate_pasture,
    "Chorvachilik": calculate_beekeeping
}