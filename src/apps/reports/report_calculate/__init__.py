from apps.reports.report_calculate.personal_resource import calculators as personal_resource_calculators
from apps.reports.report_calculate.finance_accounting import calculators as finance_resource_calculators
from apps.reports.report_calculate.additional_use_forests import calculators as additional_forest_calculators
from apps.reports.report_calculate.forest_cadastre import calculators as cadastre_forest_calculators
from apps.reports.report_calculate.forest_create import calculators as large_volume_forest_calculators
from apps.reports.report_calculate.forest_additional import calculators as additional_use_forest_second


ALL_CALCULATORS = {
    **personal_resource_calculators,
    **finance_resource_calculators,
    **additional_forest_calculators,
    **cadastre_forest_calculators,
    **large_volume_forest_calculators,
    **additional_use_forest_second
}