from apps.reports.report_calculate.finance_accounting.fund import calculate_jamgarma
from apps.reports.report_calculate.finance_accounting.income import calculate_income_summary

calculators = {
    "Jamg'arma": calculate_jamgarma,
    "Фонд": calculate_jamgarma,
    "Daromad": calculate_income_summary,
    "Доход": calculate_income_summary
}