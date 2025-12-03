from apps.reports.report_calculate import ALL_CALCULATORS

def calculate_general_report(report):
    statement_name = str(report.statement.name_uz).strip()

    func = ALL_CALCULATORS.get(statement_name)
    if not func:
        print(f"❌ Calculator not found for statement: {statement_name}")
        return

    try:
        print(f"🧮 Calculating general report: {statement_name}")
        func(report)
    except Exception as e:
        print(f"❌ Error during general report calculation: {e}")
