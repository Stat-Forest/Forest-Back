from apps.reports.models import Report


class ReportStatistics(Report):
    class Meta:
        proxy = True
        app_label = 'report_admin_stat'
        verbose_name = "Hisobotlar statistikasi"
        verbose_name_plural = "Hisobotlar statistikasi"


