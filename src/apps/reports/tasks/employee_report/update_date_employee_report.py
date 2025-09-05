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

    # 3) Info (daromadlar)
    title_uz_info = f"{current_year} yil davomida topilgan daromadlar haqida MA'LUMOT"
    title_ru_info = f"ИНФОРМАЦИЯ о доходах, полученных в {current_year} году"

    # 4) Tushum info
    title_uz_tushum = f"{current_year} yil holatiga daromad tushumi to‘g‘risida ma’lumot"
    title_ru_tushum = f"ИНФОРМАЦИЯ о доходах по состоянию на {current_year} год"

    # 5) Svod info
    title_uz_svod = f"{current_year} yil davomida topilgan daromadlar haqida MA'LUMOT"
    title_ru_svod = f"ИНФОРМАЦИЯ О ДОХОДАХ, ПОЛУЧЕННЫХ В ТЕЧЕНИЕ {current_year} ГОДА"

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

    # === Info (daromadlar) ===
    info_qs = StatementColumn.objects.filter(
        title_uz__regex=r"^\d{4} yil davomida topilgan daromadlar haqida MA'LUMOT$"
    )
    for column in info_qs:
        if column.title_uz != title_uz_info:
            column.title_uz = title_uz_info
            column.title_ru = title_ru_info
            column.save(update_fields=["title_uz", "title_ru"])

    # === Tushum info ===
    tushum_qs = StatementColumn.objects.filter(
        title_uz__regex=r"^\d{4} yil holatiga daromad tushumi to‘g‘risida ma’lumot$"
    )
    for column in tushum_qs:
        if column.title_uz != title_uz_tushum:
            column.title_uz = title_uz_tushum
            column.title_ru = title_ru_tushum
            column.save(update_fields=["title_uz", "title_ru"])

    # === Svod info ===
    svod_qs = StatementColumn.objects.filter(
        title_uz__regex=r"^\d{4} yil davomida topilgan daromadlar haqida MA'LUMOT$"
    )
    for column in svod_qs:
        if column.title_uz != title_uz_svod:
            column.title_uz = title_uz_svod
            column.title_ru = title_ru_svod
            column.save(update_fields=["title_uz", "title_ru"])
