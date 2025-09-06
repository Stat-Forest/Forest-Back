import re
from datetime import datetime
from celery import shared_task
from apps.reports.models import StatementColumn


@shared_task
def update_monthly_statement_columns():
    """
    Oylik ustunlardagi (01.MM.YYYY holatiga) sanalarni avtomatik yangilaydi.
    """
    now = datetime.now()
    current_date_str = f"01.{now.month:02d}.{now.year}"

    patterns = [
        {
            "uz": re.compile(r"Oʻrmon xoʻjaliklarida mavjud avtomashinalar \(01\.\d{2}\.\d{4} holatiga\)"),
            "ru": re.compile(r"Информация о наличии автомобилей в лесных хозяйствах \(по состоянию на 01\.\d{2}\.\d{4}\)"),
            "uz_new": f"Oʻrmon xoʻjaliklarida mavjud avtomashinalar ({current_date_str} holatiga)",
            "ru_new": f"Информация о наличии автомобилей в лесных хозяйствах (по состоянию на {current_date_str})",
        },
        {
            "uz": re.compile(r"Oʻrmon xoʻjaliklarida mavjud oʻziyurar texnikalar \(01\.\d{2}\.\d{4} holatiga\)"),
            "ru": re.compile(r"Информация о наличии самоходной техники в лесных хозяйствах \(по состоянию на 01\.\d{2}\.\d{4}\)"),
            "uz_new": f"Oʻrmon xoʻjaliklarida mavjud oʻziyurar texnikalar ({current_date_str} holatiga)",
            "ru_new": f"Информация о наличии самоходной техники в лесных хозяйствах (по состоянию на {current_date_str})",
        },
        {
            "uz": re.compile(r"Oʻrmon xoʻjaliklarida mavjud qishloq xoʻjaligi agregatlari \(01\.\d{2}\.\d{4} holatiga\)"),
            "ru": re.compile(r"Информация о наличии сельскохозяйственных агрегатов в лесных хозяйствах \(по состоянию на 01\.\d{2}\.\d{4}\)"),
            "uz_new": f"Oʻrmon xoʻjaliklarida mavjud qishloq xoʻjaligi agregatlari ({current_date_str} holatiga)",
            "ru_new": f"Информация о наличии сельскохозяйственных агрегатов в лесных хозяйствах (по состоянию на {current_date_str})",
        },
        {
            "uz": re.compile(r"Oʻrmon xoʻjaliklarida mavjud yengil xizmat avtomashinalari \(01\.\d{2}\.\d{4} holatiga\)"),
            "ru": re.compile(r"Информация о наличии служебных легковых автомобилей в лесных хозяйствах \(по состоянию на 01\.\d{2}\.\d{4}\)"),
            "uz_new": f"Oʻrmon xoʻjaliklarida mavjud yengil xizmat avtomashinalari ({current_date_str} holatiga)",
            "ru_new": f"Информация о наличии служебных легковых автомобилей в лесных хозяйствах (по состоянию на {current_date_str})",
        },

        # ====== Yangi patternlar qo‘shildi ======

        {
            "uz": re.compile(r"\d{2}\.\d{2}\.\d{4} yil holatiga mavjud"),
            "ru": re.compile(r"Состояние на \d{2}\.\d{2}\.\d{4}"),
            "uz_new": f"{current_date_str} yil holatiga mavjud",
            "ru_new": f"Состояние на {current_date_str}",
        },
        {
            "uz": re.compile(r"\d{2}\.\d{2}\.\d{4} yil holatiga xo‘jalik tomonidan asalari oilasi tashkil etish"),
            "ru": re.compile(r"Создание пчелиных семей со стороны хозяйств по состоянию на \d{2}\.\d{2}\.\d{4}"),
            "uz_new": f"{current_date_str} yil holatiga xo‘jalik tomonidan asalari oilasi tashkil etish",
            "ru_new": f"Создание пчелиных семей со стороны хозяйств по состоянию на {current_date_str}",
        },
        {
            "uz": re.compile(r"\d{2}\.\d{2}\.\d{4} yil holatiga xususiy sektor tomonidan asalari oilasi tashkil etish"),
            "ru": re.compile(r"Создание пчелиных семей со стороны частного сектора по состоянию на \d{2}\.\d{2}\.\d{4}"),
            "uz_new": f"{current_date_str} yil holatiga xususiy sektor tomonidan asalari oilasi tashkil etish",
            "ru_new": f"Создание пчелиных семей со стороны частного сектора по состоянию на {current_date_str}",
        },
        {
            "uz": re.compile(r"\d{2}\.\d{2}\.\d{4} yil holatiga jami tashkil etilgan asalari oilasi soni"),
            "ru": re.compile(r"Общее количество созданных пчелиных семей по состоянию на \d{2}\.\d{2}\.\d{4}"),
            "uz_new": f"{current_date_str} yil holatiga jami tashkil etilgan asalari oilasi soni",
            "ru_new": f"Общее количество созданных пчелиных семей по состоянию на {current_date_str}",
        },
        {
            "uz": re.compile(r"Xo‘jaliklar tomonidan tashkil etildi \d{2}\.\d{2}\.\d{4} yil holatiga"),
            "ru": re.compile(r"Создано со стороны хозяйств по состоянию на \d{2}\.\d{2}\.\d{4}"),
            "uz_new": f"Xo‘jaliklar tomonidan tashkil etildi {current_date_str} yil holatiga",
            "ru_new": f"Создано со стороны хозяйств по состоянию на {current_date_str}",
        },
        {
            "uz": re.compile(r"Xususiy sektor tomonidan tashkil etildi \d{2}\.\d{2}\.\d{4} yil holatiga"),
            "ru": re.compile(r"Создано со стороны частного сектора по состоянию на \d{2}\.\d{2}\.\d{4}"),
            "uz_new": f"Xususiy sektor tomonidan tashkil etildi {current_date_str} yil holatiga",
            "ru_new": f"Создано со стороны частного сектора по состоянию на {current_date_str}",
        },
        {
            "uz": re.compile(r"Jami tashkil etilgan parranda \d{2}\.\d{2}\.\d{4} yil holatiga"),
            "ru": re.compile(r"Общее количество созданной птицы по состоянию на \d{2}\.\d{2}\.\d{4}"),
            "uz_new": f"Jami tashkil etilgan parranda {current_date_str} yil holatiga",
            "ru_new": f"Общее количество созданной птицы по состоянию на {current_date_str}",
        },
        {
            "uz": re.compile(r"\d{2}\.\d{2}\.\d{4} yil holatiga mavjud asalari oilasi soni"),
            "ru": re.compile(r"Состояние на \d{2}\.\d{2}\.\d{4} — количество пчелиных семей"),
            "uz_new": f"{current_date_str} yil holatiga mavjud asalari oilasi soni",
            "ru_new": f"Состояние на {current_date_str} — количество пчелиных семей",
        },
    ]

    for pattern in patterns:
        columns = StatementColumn.objects.filter(
            title_uz__regex=pattern["uz"].pattern
        )
        for col in columns:
            new_uz = pattern["uz"].sub(pattern["uz_new"], col.title_uz)
            new_ru = pattern["ru"].sub(pattern["ru_new"], col.title_ru)

            if col.title_uz != new_uz or col.title_ru != new_ru:
                col.title_uz = new_uz
                col.title_ru = new_ru
                col.save(update_fields=["title_uz", "title_ru"])
