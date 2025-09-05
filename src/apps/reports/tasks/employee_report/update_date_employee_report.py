from celery import shared_task
from django.utils import timezone
from apps.reports.models import StatementColumn


@shared_task
def update_year_in_statement_columns():
    current_year = timezone.now().strftime("%Y")

    # 1) Hisobot
    title_uz_report = f"{current_year} yil uchun xodimlar to‘g‘risidagi hisobat"
    title_ru_report = f"Отчёт о сотрудниках за {current_year} год"

    # 2) Statistika
    title_uz_stats = f"{current_year} yil uchun xodimlar statistikasi to‘g‘risidagi ma’lumot"
    title_ru_stats = f"Информация о статистике сотрудников за {current_year} год"

    # === Hisobotni yangilash ===
    report_qs = StatementColumn.objects.filter(
        title_uz__regex=r"^\d{4} yil uchun xodimlar to‘g‘risidagi hisobat$"
    )
    for column in report_qs:
        if column.title_uz != title_uz_report:
            column.title_uz = title_uz_report
            column.title_ru = title_ru_report
            column.save(update_fields=["title_uz", "title_ru"])

    # === Statistika ma’lumotini yangilash ===
    stats_qs = StatementColumn.objects.filter(
        title_uz__regex=r"^\d{4} yil uchun xodimlar statistikasi to‘g‘risidagi ma’lumot$"
    )
    for column in stats_qs:
        if column.title_uz != title_uz_stats:
            column.title_uz = title_uz_stats
            column.title_ru = title_ru_stats
            column.save(update_fields=["title_uz", "title_ru"])
