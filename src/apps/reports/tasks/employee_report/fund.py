from celery import shared_task
from django.utils import timezone
from apps.reports.models import StatementColumn


@shared_task
def update_tushum_statement_columns_task():
    today = timezone.now().date()
    current_year = today.year

    # Uzbek oy nomlari
    months_uz = [
        "yanvar", "fevral", "mart", "aprel", "may", "iyun",
        "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr"
    ]
    month_name_uz = months_uz[today.month - 1]

    # Rus oy nomlari
    months_ru = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    month_name_ru = months_ru[today.month - 1]

    # Oy ichidagi hafta raqami
    first_day = today.replace(day=1)
    week_number = ((today - first_day).days // 7) + 1

    # Yangi title qiymatlari
    title_uz_new = (
        f"{current_year}-yil 1-yanvardan {current_year}-yil {month_name_uz} "
        f"{week_number}-haftaligigacha tushgan tushum "
        "O‘rmonlarni rivojlantirish jamg‘armasiga o‘tkazilgan tushum haqida HISOBOT"
    )

    title_ru_new = (
        f"О поступлениях за период с 1 января {current_year} года по "
        f"{today.day} {month_name_ru} {current_year} года "
        f"( {week_number}-я неделя месяца ) и перечисленных в Фонд развития лесов"
    )

    # Eski yozuvlarni regex orqali topish
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"^\d{4}-yil 1-yanvardan \d{4}-yil .+ haftaligigacha tushgan tushum O‘rmonlarni rivojlantirish jamg‘armasiga o‘tkazilgan tushum haqida HISOBOT$"
    )

    # Yangilash
    updated_count = 0
    for column in qs:
        if column.title_uz != title_uz_new:
            column.title_uz = title_uz_new
            column.title_ru = title_ru_new
            column.save(update_fields=["title_uz", "title_ru"])
            updated_count += 1

    return f"{updated_count} ta yozuv yangilandi"
