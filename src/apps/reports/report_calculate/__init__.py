from apps.reports.report_calculate.personal_resource import calculators as personal_resource_calculators
from apps.reports.report_calculate.finance_accounting import calculators as finance_resource_calculators
from apps.reports.report_calculate.additional_use_forests import calculators as additional_forest_calculators


ALL_CALCULATORS = {
    **personal_resource_calculators,
    **finance_resource_calculators,
    **additional_forest_calculators
}