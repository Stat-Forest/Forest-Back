from django.utils import timezone
from calendar import monthrange
from celery import shared_task
from apps.reports.models import StatementColumn


@shared_task
def update_tushum_statement_columns_task():
    today = timezone.now().date()
    current_year = today.year
    current_month = today.month

    # Uzbek oy nomlari
    months_uz = [
        "yanvar", "fevral", "mart", "aprel", "may", "iyun",
        "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr"
    ]
    month_name_uz = months_uz[current_month - 1]

    # Rus oy nomlari
    months_ru = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    month_name_ru = months_ru[current_month - 1]

    # Oyning oxirgi kuni
    last_day = monthrange(current_year, current_month)[1]

    # Sanaga qarab oraliqni aniqlash
    day = today.day
    if day <= 8:
        end_day = 8
    elif day <= 16:
        end_day = 16
    elif day <= 23:
        end_day = 23
    else:
        end_day = last_day

    # Yangi title qiymatlari
    title_uz_new = (
        f"{current_year}-yil 1-yanvardan "
        f"{current_year}-yil {end_day}-{month_name_uz}gacha tushgan tushum "
        "O‘rmonlarni rivojlantirish jamg‘armasiga o‘tkazilgan tushum haqida HISOBOT"
    )

    title_ru_new = (
        f"О поступлениях за период с 1 января {current_year} года по "
        f"{end_day} {month_name_ru} {current_year} года "
        "и перечисленных в Фонд развития лесов"
    )

    # Eski yozuvlarni regex orqali topish
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"^\d{4}-yil 1-yanvardan \d{4}-yil .+gacha tushgan tushum O‘rmonlarni rivojlantirish jamg‘armasiga o‘tkazilgan tushum haqida HISOBOT$"
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
