from apps.reports.models import Statement


class StatementStatistics(Statement):
    """Statement statistikasi uchun proxy model"""

    class Meta:
        proxy = True
        verbose_name = "Statement statistikasi"
        verbose_name_plural = "Statement statistikalari"