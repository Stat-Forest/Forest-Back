from celery import shared_task
from django.utils import timezone
from apps.reports.models import StatementColumn


@shared_task
def update_year_in_statement_columns():
    current_year = timezone.now().strftime("%Y")

    # ======== 1) Hisobot ========
    title_uz_report = f"{current_year} yil uchun xodimlar to‘g‘risidagi hisobat"
    title_ru_report = f"Отчёт о сотрудниках за {current_year} год"

    report_qs = StatementColumn.objects.filter(
        title_uz__regex=r"^\d{4} yil uchun xodimlar to‘g‘risidagi hisobat$"
    )
    for column in report_qs:
        if column.title_uz != title_uz_report:
            column.title_uz = title_uz_report
            column.title_ru = title_ru_report
            column.save(update_fields=["title_uz", "title_ru"])

    # ======== 2) Statistika ========
    title_uz_stats = f"{current_year} yil uchun xodimlar statistikasi to‘g‘risidagi ma’lumot"
    title_ru_stats = f"Информация о статистике сотрудников за {current_year} год"

    stats_qs = StatementColumn.objects.filter(
        title_uz__regex=r"^\d{4} yil uchun xodimlar statistikasi to‘g‘risidagi ma’lumot$"
    )
    for column in stats_qs:
        if column.title_uz != title_uz_stats:
            column.title_uz = title_uz_stats
            column.title_ru = title_ru_stats
            column.save(update_fields=["title_uz", "title_ru"])

    # ======== 3) Info (daromadlar) ========
    title_uz_info = f"{current_year} yil davomida topilgan daromadlar haqida MA'LUMOT"
    title_ru_info = f"ИНФОРМАЦИЯ о доходах, полученных в {current_year} году"

    info_qs = StatementColumn.objects.filter(
        title_uz__regex=r"^\d{4} yil davomida topilgan daromadlar haqida MA'LUMOT$"
    )
    for column in info_qs:
        if column.title_uz != title_uz_info:
            column.title_uz = title_uz_info
            column.title_ru = title_ru_info
            column.save(update_fields=["title_uz", "title_ru"])

    # ======== 4) Tushum info ========
    title_uz_tushum = f"{current_year} yil holatiga daromad tushumi to‘g‘risida ma’lumot"
    title_ru_tushum = f"ИНФОРМАЦИЯ о доходах по состоянию на {current_year} год"

    tushum_qs = StatementColumn.objects.filter(
        title_uz__regex=r"^\d{4} yil holatiga daromad tushumi to‘g‘risida ma’lumot$"
    )
    for column in tushum_qs:
        if column.title_uz != title_uz_tushum:
            column.title_uz = title_uz_tushum
            column.title_ru = title_ru_tushum
            column.save(update_fields=["title_uz", "title_ru"])

    # ======== 5) Svod info ========
    title_uz_svod = f"{current_year} yil davomida topilgan daromadlar haqida MA'LUMOT"
    title_ru_svod = f"ИНФОРМАЦИЯ О ДОХОДАХ, ПОЛУЧЕННЫХ В ТЕЧЕНИЕ {current_year} ГОДА"

    svod_qs = StatementColumn.objects.filter(
        title_uz__regex=r"^\d{4} yil davomida topilgan daromadlar haqida MA'LUMOT$"
    )
    for column in svod_qs:
        if column.title_uz != title_uz_svod:
            column.title_uz = title_uz_svod
            column.title_ru = title_ru_svod
            column.save(update_fields=["title_uz", "title_ru"])

    # === 1) Ijarachilar bo‘yicha ma’lumot ===
    title_uz_ijarachi = f"{current_year} yilda xar bir ijarachi bo‘yicha ma’lumot"
    title_ru_ijarachi = f"Информация по каждому арендатору за {current_year} год"

    ijarachi_qs = StatementColumn.objects.filter(
        statement__name='Ijaraga berilgan yerlar hisobi',
        title_uz__regex=r"^\d{4} yilda xar bir ijarachi bo‘yicha ma’lumot$"
    )
    for column in ijarachi_qs:
        if column.title_uz != title_uz_ijarachi:
            column.title_uz = title_uz_ijarachi
            column.title_ru = title_ru_ijarachi
            column.save(update_fields=["title_uz", "title_ru"])

    # === 2) O‘rmon fondi yerlari maydoni ===
    title_uz_fondi = f"{current_year} yilda foydalanishga kiritiladigan o‘rmon fondi yerlari maydoni to‘g‘risida ma’lumot"
    title_ru_fondi = f"Информация о площади земель лесного фонда, вводимых в эксплуатацию в {current_year} году"

    fondi_qs = StatementColumn.objects.filter(
        statement_name='Yer o‘zlashtirish',
        title_uz__regex=r"^\d{4} yilda foydalanishga kiritiladigan o‘rmon fondi yerlari maydoni to‘g‘risida ma’lumot$"
    )
    for column in fondi_qs:
        if column.title_uz != title_uz_fondi:
            column.title_uz = title_uz_fondi
            column.title_ru = title_ru_fondi
            column.save(update_fields=["title_uz", "title_ru"])

    from django.utils import timezone
    current_year = int(timezone.now().strftime("%Y"))
    next_year = current_year + 1

    # === 2) 2 yillik blok (masalan: 2025–2026 yillar) ===
    title_uz_period = f"{current_year}–{next_year} yillar"
    title_ru_period = f"{current_year}–{next_year} годы"

    period_qs = StatementColumn.objects.filter(
        statement__name='Ijaraga berilgan yerlar hisobi',
        title_uz__regex=r"^\d{4}–\d{4} yillar$"
    )
    for column in period_qs:
        if column.title_uz != title_uz_period:
            column.title_uz = title_uz_period
            column.title_ru = title_ru_period
            column.save(update_fields=["title_uz", "title_ru"])


    title_uz_export = f"{current_year} yildagi eksport"
    title_ru_export = f"Экспорт за {current_year} год"

    export_qs = StatementColumn.objects.filter(
        statement__name='Ijaraga berilgan yerlar hisobi',
        title_uz__regex=r"^\d{4} yildagi eksport$"
    )
    for column in export_qs:
        if column.title_uz != title_uz_export:
            column.title_uz = title_uz_export
            column.title_ru = title_ru_export
            column.save(update_fields=["title_uz", "title_ru"])




    # ========== ⬇️ Forest Column Celery of Oybek  ==========

    # === Ilova 1: "2025 yildan yirik hajmli..." ===
    new_title_uz_1 = (
        f"O'rmon xo'jaligi agentligi tizimidagi o'rmon xo'jaliklari tomonidan "
        f"{current_year} yildan yirik hajmli yopiq ko'chatlarni yetishtirish to'g'risida "
        "tezkor ma'lumot."
    )
    new_title_ru_1 = (
        f"Срочная информация о выращивании крупногабаритных закрытых саженцев "
        f"лесничествами в системе Агентства лесного хозяйства с {current_year} года."
    )

    col_1_qs = StatementColumn.objects.filter(
        title_uz__regex=r"\d{4} yildan yirik hajmli yopiq ko'chatlarni yetishtirish to'g'risida tezkor ma'lumot\.$"
    )
    for column in col_1_qs:
        if column.title_uz != new_title_uz_1:
            column.title_uz = new_title_uz_1
            column.title_ru = new_title_ru_1
            column.save(update_fields=["title_uz", "title_ru"])

    # === Ilova 3: "2025 yilda tayyorlangan o‘rmon urug‘lari..." ===
    new_title_uz_3 = (
        f"O'rmon xo'jaligida {current_year} yilda tayyorlangan o'rmon daraxt va buta urug'larining "
        "harakati to'g'risida"
    )
    new_title_ru_3 = (
        f"О движении семян лесных деревьев и кустарников, подготовленных в лесном хозяйстве в {current_year} году"
    )

    col_3_qs = StatementColumn.objects.filter(
        title_uz__regex=r"\d{4} yilda tayyorlangan o'rmon daraxt va buta urug'larining harakati to'g'risida$"
    )
    for column in col_3_qs:
        if column.title_uz != new_title_uz_3:
            column.title_uz = new_title_uz_3
            column.title_ru = new_title_ru_3
            column.save(update_fields=["title_uz", "title_ru"])

        # === Ilova: "Qalamchalar tayyorlash bo‘yicha tezkor ma‘lumot" ===
    new_title_uz_qalamcha = (
        f"O‘rmon xo‘jaliklari tomonidan {current_year} yil bahor mavsumlarida "
        f"qalamchalar tayyorlash bo‘yicha tezkor ma‘lumot."
    )
    new_title_ru_qalamcha = (
        f"Срочная информация о подготовке черенков лесничествами в весенние сезоны {current_year} года."
    )

    qalamcha_qs = StatementColumn.objects.filter(
        title_uz__regex=r"O‘rmon xo‘jaliklari tomonidan \d{4} yil bahor mavsumlarida qalamchalar tayyorlash bo‘yicha tezkor ma‘lumot\."
    )
    for column in qalamcha_qs:
        if column.title_uz != new_title_uz_qalamcha:
            column.title_uz = new_title_uz_qalamcha
            column.title_ru = new_title_ru_qalamcha
            column.save(update_fields=["title_uz", "title_ru"])

        # === Ilova: Boshoqli don ekinlari ===
    uz = f"Agentlik tizimidagi xo'jaliklarda {current_year} yilda boshoqli don ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot"
    ru = f"Информация о посеве зерновых культур и производстве продукции в хозяйствах системы Агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Agentlik tizimidagi xo'jaliklarda \d{4} yilda boshoqli don ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Sabzavot ekinlari ===
    uz = f"Agentlik tizimidagi xo'jaliklarda {current_year} yilda sabzavot ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot"
    ru = f"Информация о посеве овощных культур и производстве продукции в хозяйствах системы Агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Agentlik tizimidagi xo'jaliklarda \d{4} yilda sabzavot ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Poliz ekinlari ===
    uz = f"Agentlik tizimidagi xo'jaliklarda {current_year} yilda poliz ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot"
    ru = f"Информация о посеве бахчевых культур и производстве продукции в хозяйствах системы Агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Agentlik tizimidagi xo'jaliklarda \d{4} yilda poliz ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Moyli ekinlar ===
    uz = f"Agentlik tizimidagi xo'jaliklarda {current_year} yilda moyli ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot"
    ru = f"Информация о посеве масличных культур и производстве продукции в хозяйствах системы Агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Agentlik tizimidagi xo'jaliklarda \d{4} yilda moyli ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Dukkakli ekinlar ===
    uz = f"Agentlik tizimidagi xo'jaliklarda {current_year} yilda dukkakli ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot"
    ru = f"Информация о посеве бобовых культур и производстве продукции в хозяйствах системы Агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Agentlik tizimidagi xo'jaliklarda \d{4} yilda dukkakli ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Ozuqa ekinlari ===
    uz = f"Agentlik tizimidagi xo'jaliklarda {current_year} yilda ozuqa ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot"
    ru = f"Информация о посеве кормовых культур и производстве продукции в хозяйствах системы Агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Agentlik tizimidagi xo'jaliklarda \d{4} yilda ozuqa ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Mevali bog‘ va tokzorlar ===
    uz = f"Agentlik tizimidagi xo'jaliklarda {current_year} yilda mevali bog'lar va tokzorlar ekish va hosil yetishtirish to'g'risida ma'lumot"
    ru = f"Информация о посеве и урожайности садов и виноградников в хозяйствах системы Агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Agentlik tizimidagi xo'jaliklarda \d{4} yilda mevali bog'lar va tokzorlar ekish va hosil yetishtirish to'g'risida ma'lumot"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Yong‘oqmevali mahsulotlar ===
    uz = f"Agentlik tizimidagi xo'jaliklarda {current_year} yilda yong'oqmevali mahsulotlar yetishtirish to'g'risida ma'lumot"
    ru = f"Информация о производстве орехоплодных культур в хозяйствах системы Агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Agentlik tizimidagi xo'jaliklarda \d{4} yilda yong'oqmevali mahsulotlar yetishtirish to'g'risida ma'lumot"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

        # === 2017-yildan boshlab qo‘shilgan bog‘lar ===
    uz = f"2017-{current_year} yildan qo'shilgan bog'lar"
    ru = f"Сады, добавленные с 2017 по {current_year} год"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"2017-\d{4} yildan qo'shilgan bog'lar"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # ===================== MEXANIZATSIYA =============================

    # === Neftbaza ilovasi ===
    neftbaza_uz = f"Oʻrmon xoʻjaliklarida {current_year} yil 1-yanvargacha olingan YOQM miqdori toʻgʻrisida maʼlumot"
    neftbaza_ru = f"Информация о количестве полученных ГСМ в лесных хозяйствах до 1 января {current_year} года"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Oʻrmon xoʻjaliklarida \d{4} yil 1-yanvargacha olingan YOQM miqdori toʻgʻrisida maʼlumot"
    )
    for col in qs:
        if col.title_uz != neftbaza_uz:
            col.title_uz = neftbaza_uz
            col.title_ru = neftbaza_ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Yoqilg‘i limit ilovasi ===
    yoqilgi_uz = f"Oʻrmon xoʻjaliklarida {current_year} yilda yoqilgʻi-moylash materiallari sarfi toʻgʻrisida maʼlumot"
    yoqilgi_ru = f"Информация о расходе горюче-смазочных материалов в лесных хозяйствах в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Oʻrmon xoʻjaliklarida \d{4} yilda yoqilgʻi-moylash materiallari sarfi toʻgʻrisida maʼlumot"
    )
    for col in qs:
        if col.title_uz != yoqilgi_uz:
            col.title_uz = yoqilgi_uz
            col.title_ru = yoqilgi_ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Metallolom ilovasi ===
    metallolom_uz = f"{current_year} yilda metallolom topshirilishi va realizatsiya qilinishi toʻgʻrisida maʼlumot"
    metallolom_ru = f"Информация о сдаче и реализации металлолома в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"\d{4} yilda metallolom topshirilishi va realizatsiya qilinishi toʻgʻrisida maʼlumot"
    )
    for col in qs:
        if col.title_uz != metallolom_uz:
            col.title_uz = metallolom_uz
            col.title_ru = metallolom_ru
            col.save(update_fields=["title_uz", "title_ru"])


    # ==========================
    # === Pichan prognoz ===
    pichan_uz = f"{current_year} yil prognoz ko‘rsatkichlari, ming so‘m (reja)"
    pichan_ru = f"Прогнозные показатели на {current_year} год, тыс. сум ( план)"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"\d{4} yil prognoz ko‘rsatkichlari, ming so‘m \(reja\)"
    )
    for col in qs:
        if col.title_uz != pichan_uz:
            col.title_uz = pichan_uz
            col.title_ru = pichan_ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Pichan hisoboti ===
    uz = f"O‘rmon xo‘jaligi agentligi tizimidagi xo‘jaliklarda o‘rmon fondi yerlarida pichan o‘rish uchun berilgan yerlar hisoboti bo‘yicha {current_year} yil holatiga maʼmulot"
    ru = f"Информация по состоянию на {current_year} год о сенокосных угодьях, предоставленных в лесном фонде хозяйствам в системе Агентства лесного хозяйства"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"pichan o‘rish uchun berilgan yerlar hisoboti bo‘yicha \d{4} yil holatiga maʼmulot"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Yaylov prognoz ===
    uz = f"{current_year} yil prognoz ko‘rsatkichlari, ming so‘m (reja)"
    ru = f"Прогнозные показатели на {current_year} год, тыс. сум ( план)"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"\d{4} yil prognoz ko‘rsatkichlari, ming so‘m \(reja\)"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Yaylov hisoboti ===
    uz = f"O‘rmon xo‘jaligi agentligi tizimidagi xo‘jaliklarda o‘rmon fondi yaylov hududlariga chorva mollarini joylashtirish bo‘yicha {current_year} yil holatiga maʼmulot"
    ru = f"Информация по размещению скота на пастбищных участках лесного фонда в хозяйствах системы Агентства лесного хозяйства по состоянию на {current_year} год"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"yaylov hududlariga chorva mollarini joylashtirish bo‘yicha \d{4} yil holatiga maʼmulot"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Yirik shohli mollar ===
    uz = f"Agentlik tizimidagi o‘rmon xo‘jaliklarida {current_year} yilda Yirik shohli mollarni rivojlantirish bo‘yicha MA’LUMOT"
    ru = f"Информация о развитии крупного рогатого скота в лесных хозяйствах системы агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Yirik shohli mollarni rivojlantirish bo‘yicha MA’LUMOT"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

# === Yirik shohli mollar ===
    uz = f"Agentlik tizimidagi o‘rmon xo‘jaliklarida {current_year} yilda Yirik shohli mollarni rivojlantirish bo‘yicha MA’LUMOT"
    ru = f"Информация о развитии крупного рогатого скота в лесных хозяйствах системы агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Yirik shohli mollarni rivojlantirish bo‘yicha MA’LUMOT"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Yilqichilik ===
    uz = f"Agentlik tizimidagi o‘rmon xo‘jaliklarida {current_year} yilda Yilqichilikni rivojlantirish bo‘yicha MA’LUMOT"
    ru = f"Информация о развитии коневодства в лесных хозяйствах системы агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Yilqichilikni rivojlantirish bo‘yicha MA’LUMOT"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Mayda shohli mollar ===
    uz = f"Agentlik tizimidagi o‘rmon xo‘jaliklarida {current_year} yilda Mayda shohli mollarni rivojlantirish bo‘yicha MA’LUMOT"
    ru = f"Информация о развитии мелкого рогатого скота в лесных хозяйствах системы агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"Mayda shohli mollarni rivojlantirish bo‘yicha MA’LUMOT"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Parrandachilik ===
    uz = f"Agentlik tizimidagi o‘rmon xo‘jaliklarida {current_year} yilda parrandachilik bo‘yicha MA’LUMOT"
    ru = f"Информация о птицеводстве в лесных хозяйствах системы агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"parrandachilik bo‘yicha MA’LUMOT"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Asalarichilik ===
    uz = f"Agentlik tizimidagi o‘rmon xo‘jaliklarida {current_year} yilda asalarichilik bo‘yicha MA’LUMOT"
    ru = f"Информация о пчеловодстве в лесных хозяйствах системы агентства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"asalarichilik bo‘yicha MA’LUMOT"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Yangi asalari oilasi ===
    uz = f"{current_year} yilda yangidan asalari oilasi tashkil etish"
    ru = f"Создание новых пчелиных семей в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"yilda yangidan asalari oilasi tashkil etish"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])

    # === Baliqchilik ===
    uz = f"O‘rmon xo‘jaligi agentligi huzuridagi xo‘jaliklardagi {current_year} yilda baliq mahsulotlarini yetishtirilishi bo‘yicha MA’LUMOT"
    ru = f"Информация о производстве рыбной продукции в хозяйствах при агентстве лесного хозяйства в {current_year} году"
    qs = StatementColumn.objects.filter(
        title_uz__regex=r"baliq mahsulotlarini yetishtirilishi bo‘yicha MA’LUMOT"
    )
    for col in qs:
        if col.title_uz != uz:
            col.title_uz = uz
            col.title_ru = ru
            col.save(update_fields=["title_uz", "title_ru"])