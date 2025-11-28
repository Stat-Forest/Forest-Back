from django.core.management.base import BaseCommand
from apps.reports.models import Report
from apps.reports.services.report_calculate_expressions import calculate_by_expressions
from apps.reports.services.general_report import aggregate_national_report


class Command(BaseCommand):
    help = "Recalculate all republic-level (is_republic=True) general reports"

    def handle(self, *args, **options):
        republic_reports = Report.objects.filter(is_republic=True)
        if not republic_reports.exists():
            self.stdout.write(self.style.WARNING("❌ No republic-level reports found."))
            return

        total = republic_reports.count()
        success = 0

        for report in republic_reports:
            try:
                self.stdout.write(f"🔁 Recalculating report: {report.id} - {report.statement}")
                # 1️⃣ Qayta hisoblash (expressions or custom logic)
                calculate_by_expressions(report)

                # 2️⃣ Agar sizda maxsus aggregator bo‘lsa
                aggregate_national_report(report)

                success += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"⚠️ Error recalculating report {report.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ Recalculated {success} out of {total} republic-level reports."))
