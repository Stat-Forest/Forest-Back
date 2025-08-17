from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    def handle(self, *args, **options):
        def create_column(statement, parent, title_uz, title_ru, ordering, is_organization=False, status_plan=None, is_user_input=True):
            return StatementColumn.objects.create(
                statement=statement,
                parent=parent,
                title=title_uz,
                title_ru=title_ru,
                ordering=ordering,
                is_organization=is_organization,
                status_plan=status_plan,
                is_user_input=is_user_input
            )

        forest_add = Statement.objects.get(
            name_uz="O'rmonlardan qo'shimcha foydalanish",
            name_ru="Дополнительное использование лесов",
            period=PeriodChoices.YILLIK
        )
        statement_mechanization = Statement.objects.create(
            parent=forest_add,
            name_uz="Mexanizatsiya hisobi",
            name_ru="Счет механизации"
        )

        # ========== Neftbaza ilovasi ==========
        neftbaza_ilova = create_column(statement_mechanization, None, "Neftbaza ilovasi", "Приложение: Нефтебаза", "1")

        neftbaza_title = create_column(
            statement_mechanization,
            neftbaza_ilova,
            "Oʻrmon xoʻjaliklarida 2025 yil 1-yanvargacha olingan YOQM miqdori toʻgʻrisida maʼlumot",
            "Информация о количестве полученных ГСМ в лесных хозяйствах до 1 января 2025 года",
            "1.1"
        )

        create_column(statement_mechanization, neftbaza_title, "Tashkilot nomi", "Наименование организации", "1.1.1",
                      is_organization=True)
        create_column(statement_mechanization, neftbaza_title, "Neftbaza nomi", "Наименование нефтебазы", "1.1.2")

        nakladnoy = create_column(statement_mechanization, neftbaza_title, "Nakladnoy", "Накладная", "1.1.3")
        create_column(statement_mechanization, nakladnoy, "Raqami", "Номер", "1.1.3.1")
        create_column(statement_mechanization, nakladnoy, "Sanasi", "Дата", "1.1.3.2")

        create_column(statement_mechanization, neftbaza_title, "Yoqilgʻi turi", "Вид топлива", "1.1.4")
        create_column(statement_mechanization, neftbaza_title, "Miqdori, kg", "Количество, кг", "1.1.5")
        create_column(statement_mechanization, neftbaza_title, "Summasi, ming soʻm", "Сумма, тыс. сум", "1.1.6")
        create_column(statement_mechanization, neftbaza_title, "Moliya manbai (byudjet/xoʻjalik hisobidan)",
                      "Источник финансирования (бюджет/хозрасчёт)", "1.1.7")

        # ========== Avto ilovasi ==========
        avto_ilova = create_column(statement_mechanization, None, "Avto ilovasi", "Приложение: Автомашины", "2")

        avto_title = create_column(
            statement_mechanization,
            avto_ilova,
            "Oʻrmon xoʻjaliklarida mavjud avtomashinalar (01.01.2025 holatiga) va ularning holati toʻgʻrisida maʼlumot",
            "Информация о наличии автомобилей в лесных хозяйствах (по состоянию на 01.01.2025) и их техническом состоянии",
            "2.1"
        )

        create_column(statement_mechanization, avto_title, "Tashkilot nomi", "Наименование организации", "2.1.1",
                      is_organization=True)
        create_column(statement_mechanization, avto_title, "Avtomobil turi", "Тип автомобиля", "2.1.2")
        create_column(statement_mechanization, avto_title, "Rusumi", "Марка", "2.1.3")
        create_column(statement_mechanization, avto_title, "Davlat raqami belgisi", "Государственный номерной знак",
                      "2.1.4")
        create_column(statement_mechanization, avto_title, "Ishlab chiqarilgan yili", "Год выпуска", "2.1.5")

        agregatlar = create_column(statement_mechanization, avto_title, "Agregatlar raqami", "Номера агрегатов",
                                   "2.1.6")
        create_column(statement_mechanization, agregatlar, "Zavod (inventar)", "Заводской (инвентарный)", "2.1.6.1")
        create_column(statement_mechanization, agregatlar, "Dvigatel", "Двигатель", "2.1.6.2")
        create_column(statement_mechanization, agregatlar, "Kuzov", "Кузов", "2.1.6.3")
        create_column(statement_mechanization, agregatlar, "Shassi (rama)", "Шасси (рама)", "2.1.6.4")

        yonilgilar = create_column(statement_mechanization, avto_title, "Yoqilgʻi turi", "Вид топлива", "2.1.7")
        create_column(statement_mechanization, yonilgilar,
                      "(Benzin, dizel yoqilgʻisi, siqilgan tabiiy gaz yoki suyuqlashtirilgan gaz)",
                      "(Бензин, дизельное топливо, сжатый природный газ или сжиженный газ)", "2.1.7.1")

        create_column(statement_mechanization, avto_title, "Texnik holati (soz/nosoz/yarqsiz)",
                      "Техническое состояние (исправен/неисправен/непригоден)", "2.1.8")
        create_column(statement_mechanization, avto_title, "Moliya manbai (xoʻjalik yoki byudjet)",
                      "Источник финансирования (хозрасчёт или бюджет)", "2.1.9")

        asosiy_qiymat = create_column(statement_mechanization, avto_title,
                                      "Asosiy vositaning qiymati (ming soʻm hisobida)",
                                      "Стоимость основного средства (в тыс. сум)", "2.1.10")
        create_column(statement_mechanization, asosiy_qiymat, "Boshlangʻich qiymati", "Первоначальная стоимость",
                      "2.1.10.1")
        create_column(statement_mechanization, asosiy_qiymat, "Eskirish qiymati", "Сумма износа", "2.1.10.2")
        create_column(statement_mechanization, asosiy_qiymat, "Qoldiq qiymati", "Остаточная стоимость", "2.1.10.3")

        # ========== K-X texnikasi ilovasi ==========
        kx_ilova = create_column(statement_mechanization, None, "Q-X texnikasi ilovasi", "Приложение: С/Х техника", "3")

        kx_title = create_column(
            statement_mechanization,
            kx_ilova,
            "Oʻrmon xoʻjaliklarida mavjud oʻziyurar texnikalar (01.01.2025 holatiga) va ularning holati toʻgʻrisida maʼlumot",
            "Информация о наличии самоходной техники в лесных хозяйствах (по состоянию на 01.01.2025) и их техническом состоянии",
            "3.1"
        )

        create_column(statement_mechanization, kx_title, "Tashkilot nomi", "Наименование организации", "3.1.1",
                      is_organization=True)
        create_column(statement_mechanization, kx_title, "Texnikaning nomi", "Наименование техники", "3.1.2")
        create_column(statement_mechanization, kx_title, "Rusumi", "Марка", "3.1.3")
        create_column(statement_mechanization, kx_title, "Davlat raqami belgisi", "Государственный номер", "3.1.4")
        create_column(statement_mechanization, kx_title, "Ishlab chiqarilgan yili", "Год выпуска", "3.1.5")

        agregat_raqam = create_column(statement_mechanization, kx_title, "Agregatlar raqami", "Номера агрегатов",
                                      "3.1.6")
        create_column(statement_mechanization, agregat_raqam, "Zavod (inventar)", "Заводской (инвентарный)", "3.1.6.1")
        create_column(statement_mechanization, agregat_raqam, "Dvigatel", "Двигатель", "3.1.6.2")
        create_column(statement_mechanization, agregat_raqam, "Kuzov", "Кузов", "3.1.6.3")
        create_column(statement_mechanization, agregat_raqam, "Shassi (rama)", "Шасси (рама)", "3.1.6.4")

        yoqilgi_turi = create_column(statement_mechanization, kx_title, "Yoqilgʻi turi", "Вид топлива", "3.1.7")
        create_column(statement_mechanization, yoqilgi_turi, "(Benzin, dizel, metan, propan)",
                      "(Бензин, дизель, метан, пропан)", "3.1.7.1")

        create_column(statement_mechanization, kx_title, "Texnik holati (soz/nosoz/yarqsiz)",
                      "Техническое состояние (исправен/неисправен/непригоден)", "3.1.8")
        create_column(statement_mechanization, kx_title, "Moliya manbai (xoʻjalik yoki byudjet)",
                      "Источник финансирования (хозрасчёт или бюджет)", "3.1.9")

        asosiy_qiymat_kx = create_column(statement_mechanization, kx_title,
                                         "Asosiy vositaning qiymati (ming soʻm hisobida)",
                                         "Стоимость основного средства (в тыс. сум)", "3.1.10")
        create_column(statement_mechanization, asosiy_qiymat_kx, "Boshlangʻich qiymati", "Первоначальная стоимость",
                      "3.1.10.1")
        create_column(statement_mechanization, asosiy_qiymat_kx, "Eskirish qiymati", "Сумма износа", "3.1.10.2")
        create_column(statement_mechanization, asosiy_qiymat_kx, "Qoldiq qiymati", "Остаточная стоимость", "3.1.10.3")

        # ========== Agregatlar ilovasi ==========
        agregat_ilova = create_column(statement_mechanization, None, "Agregatlar ilovasi", "Приложение: Агрегаты", "4")

        agregat_title = create_column(
            statement_mechanization,
            agregat_ilova,
            "Oʻrmon xoʻjaliklarida mavjud qishloq xoʻjaligi agregatlari (01.01.2025 holatiga) va ularning holati toʻgʻrisida maʼlumot",
            "Информация о наличии сельскохозяйственных агрегатов в лесных хозяйствах (по состоянию на 01.01.2025) и их техническом состоянии",
            "4.1"
        )

        create_column(statement_mechanization, agregat_title, "Tashkilot nomi", "Наименование организации", "4.1.1",
                      is_organization=True)
        create_column(statement_mechanization, agregat_title, "Texnikaning nomi", "Наименование техники", "4.1.2")
        create_column(statement_mechanization, agregat_title, "Rusumi", "Марка", "4.1.3")
        create_column(statement_mechanization, agregat_title, "Ishlab chiqarilgan yili", "Год выпуска", "4.1.4")

        agregat_numbers = create_column(statement_mechanization, agregat_title, "Agregatlar raqami", "Номера агрегатов",
                                        "4.1.5")
        create_column(statement_mechanization, agregat_numbers, "Zavod (inventar)", "Заводской (инвентарный)",
                      "4.1.5.1")
        create_column(statement_mechanization, agregat_numbers, "Texnik hujjat raqami", "Номер технического документа",
                      "4.1.5.2")

        create_column(statement_mechanization, agregat_title, "Texnik holati (soz/nosoz/yarqsiz)",
                      "Техническое состояние (исправен/неисправен/непригоден)", "4.1.6")
        create_column(statement_mechanization, agregat_title, "Moliya manbai (xoʻjalik yoki byudjet)",
                      "Источник финансирования (хозрасчёт или бюджет)", "4.1.7")

        asosiy_qiymat_agr = create_column(statement_mechanization, agregat_title,
                                          "Asosiy vositaning qiymati (ming soʻm hisobida)",
                                          "Стоимость основного средства (в тыс. сум)", "4.1.8")
        create_column(statement_mechanization, asosiy_qiymat_agr, "Boshlangʻich qiymati", "Первоначальная стоимость",
                      "4.1.8.1")
        create_column(statement_mechanization, asosiy_qiymat_agr, "Eskirish qiymati", "Сумма износа", "4.1.8.2")
        create_column(statement_mechanization, asosiy_qiymat_agr, "Qoldiq qiymati", "Остаточная стоимость", "4.1.8.3")

        # ========== Yengil avto ilovasi ==========
        yengil_avto_ilova = create_column(statement_mechanization, None, "Yengil avto ilovasi",
                                          "Приложение: Лёгковой автотранспорт", "5")

        yengil_avto_title = create_column(
            statement_mechanization,
            yengil_avto_ilova,
            "Oʻrmon xoʻjaliklarida mavjud yengil xizmat avtomashinalari (01.01.2025 holatiga) boʻyicha maʼlumot",
            "Информация о наличии служебных легковых автомобилей в лесных хозяйствах (по состоянию на 01.01.2025)",
            "5.1"
        )

        create_column(statement_mechanization, yengil_avto_title, "Tashkilot nomi", "Наименование организации", "5.1.1",
                      is_organization=True)
        create_column(statement_mechanization, yengil_avto_title, "Avtotransport rusumi", "Марка автотранспорта",
                      "5.1.2")
        create_column(statement_mechanization, yengil_avto_title, "Ishlab chiqarilgan yili", "Год выпуска", "5.1.3")
        create_column(statement_mechanization, yengil_avto_title, "Davlat raqami", "Государственный номер", "5.1.4")

        balans = create_column(statement_mechanization, yengil_avto_title, "Balans qiymati (ming soʻm)",
                               "Балансовая стоимость (в тыс. сум)", "5.1.5")
        create_column(statement_mechanization, balans, "Boshlangʻich qiymati", "Первоначальная стоимость", "5.1.5.1")
        create_column(statement_mechanization, balans, "Qoldiq qiymati", "Остаточная стоимость", "5.1.5.2")

        create_column(statement_mechanization, yengil_avto_title, "Avtotransport holati (soz yoki nosoz)",
                      "Техническое состояние автотранспорта (исправен или неисправен)", "5.1.6")
        create_column(statement_mechanization, yengil_avto_title, "Bosib oʻtgan masofa (km)", "Пробег (км)", "5.1.7")
        create_column(statement_mechanization, yengil_avto_title, "Biriktirilgan boʻlim yoki xodim (F.I.O.)",
                      "Прикреплённое подразделение или сотрудник (Ф.И.О.)", "5.1.8")

        # ========== YOQILGʻI LIMIT ilovasi ==========
        yoqilgi_limit_ilova = create_column(
            statement_mechanization, None, "Yoqilgʻi limit ilovasi", "Приложение: Лимит топлива", "6"
        )

        yoqilgi_limit_title = create_column(
            statement_mechanization,
            yoqilgi_limit_ilova,
            "Oʻrmon xoʻjaliklarida 2025 yilda yoqilgʻi-moylash materiallari sarfi toʻgʻrisida maʼlumot",
            "Информация о расходе горюче-смазочных материалов в лесных хозяйствах в 2025 году",
            "6.1"
        )

        create_column(statement_mechanization, yoqilgi_limit_title, "Tashkilot nomi", "Наименование организации",
                      "6.1.1", is_organization=True)
        create_column(statement_mechanization, yoqilgi_limit_title, "Hisobot davri", "Отчетный период", "6.1.2")

        smeta = create_column(
            statement_mechanization,
            yoqilgi_limit_title,
            "Smeta boʻyicha tasdiqlangan (ming soʻm)", "Утверждено по смете (в тыс. сум)", "6.1.3"
        )
        create_column(statement_mechanization, smeta, "Byudjet hisobidan", "За счёт бюджета", "6.1.3.1")
        create_column(statement_mechanization, smeta, "Xoʻjalik hisobidan", "За счёт хозрасчёта", "6.1.3.2")

        byudjet = create_column(statement_mechanization, yoqilgi_limit_title, "Byudjet hisobidan", "За счёт бюджета",
                                "6.1.4")
        benzin = create_column(statement_mechanization, byudjet, "Benzin", "Бензин", "6.1.4.1")
        create_column(statement_mechanization, benzin, "Tonna", "Тонн", "6.1.4.1.1")
        create_column(statement_mechanization, benzin, "Summa", "Сумма", "6.1.4.1.2")

        dizel = create_column(statement_mechanization, byudjet, "Dizel", "Дизель", "6.1.4.2")
        create_column(statement_mechanization, dizel, "Tonna", "Тонн", "6.1.4.2.1")
        create_column(statement_mechanization, dizel, "Summa", "Сумма", "6.1.4.2.2")

        metan = create_column(statement_mechanization, byudjet, "Metan gaz", "Метан газ", "6.1.4.3")
        create_column(statement_mechanization, metan, "m³", "м³", "6.1.4.3.1")
        create_column(statement_mechanization, metan, "Summa", "Сумма", "6.1.4.3.2")

        propan = create_column(statement_mechanization, byudjet, "Propan gaz", "Пропан газ", "6.1.4.4")
        create_column(statement_mechanization, propan, "m³", "м³", "6.1.4.4.1")
        create_column(statement_mechanization, propan, "Summa", "Сумма", "6.1.4.4.2")

        xojalik = create_column(statement_mechanization, yoqilgi_limit_title, "Xoʻjalik hisobidan",
                                "За счёт хозрасчёта", "6.1.5")
        benzin2 = create_column(statement_mechanization, xojalik, "Benzin", "Бензин", "6.1.5.1")
        create_column(statement_mechanization, benzin2, "Tonna", "Тонн", "6.1.5.1.1")
        create_column(statement_mechanization, benzin2, "Summa", "Сумма", "6.1.5.1.2")

        dizel2 = create_column(statement_mechanization, xojalik, "Dizel", "Дизель", "6.1.5.2")
        create_column(statement_mechanization, dizel2, "Tonna", "Тонн", "6.1.5.2.1")
        create_column(statement_mechanization, dizel2, "Summa", "Сумма", "6.1.5.2.2")

        metan2 = create_column(statement_mechanization, xojalik, "Metan gaz", "Метан газ", "6.1.5.3")
        create_column(statement_mechanization, metan2, "m³", "м³", "6.1.5.3.1")
        create_column(statement_mechanization, metan2, "Summa", "Сумма", "6.1.5.3.2")

        propan2 = create_column(statement_mechanization, xojalik, "Propan gaz", "Пропан газ", "6.1.5.4")
        create_column(statement_mechanization, propan2, "m³", "м³", "6.1.5.4.1")
        create_column(statement_mechanization, propan2, "Summa", "Сумма", "6.1.5.4.2")

        # ========== Metallolom ilovasi ==========
        metallolom_ilova = create_column(
            statement_mechanization, None, "Metallolom ilovasi", "Приложение: Металлолом", "7"
        )

        metallolom_title = create_column(
            statement_mechanization,
            metallolom_ilova,
            "2025 yilda metallolom topshirilishi va realizatsiya qilinishi toʻgʻrisida maʼlumot",
            "Информация о сдаче и реализации металлолома в 2025 году",
            "7.1"
        )

        create_column(statement_mechanization, metallolom_title, "Tashkilot nomi", "Наименование организации", "7.1.1",
                      is_organization=True)

        create_column(
            statement_mechanization,
            metallolom_title,
            "Yillik reja, tonna",
            "Годовой план, тонн",
            "7.1.2",
            is_user_input=False
        )
        create_column(statement_mechanization, metallolom_title, "Amalda", "Факт", "7.1.2",
                      is_user_input=False)
        create_column(statement_mechanization, metallolom_title, "%", "%", "7.1.2",
                      is_user_input=False)

        for i in range(1, 5):
            chorak_ordering = f"7.1.{i + 1}"
            chorak = create_column(
                statement_mechanization,
                metallolom_title,
                f"{i}-chorak",
                f"{i}-й квартал",
                chorak_ordering
            )
            create_column(statement_mechanization, chorak, "Reja", "План", f"{chorak_ordering}.1",
                          is_user_input=False)
            create_column(statement_mechanization, chorak, "Amalda", "Факт", f"{chorak_ordering}.2")
            create_column(statement_mechanization, chorak, "%", "%", f"{chorak_ordering}.3",
                          is_user_input=False)

            hujjat = create_column(
                statement_mechanization,
                chorak,
                "Metall parchalari topshirilgani toʻgʻrisida hujjat",
                "Документ о сдаче металлолома",
                f"{chorak_ordering}.4"
            )

            create_column(statement_mechanization, hujjat, "Sanasi", "Дата", f"{chorak_ordering}.4.1")
            create_column(statement_mechanization, hujjat, "Kvit. raqami", "Номер квитанции", f"{chorak_ordering}.4.2")
            create_column(statement_mechanization, hujjat, "Miqdori, tonna", "Количество, тонн",
                          f"{chorak_ordering}.4.3")

            # ========== Pichan ilovasi ==========
        pichan_statement, _ = Statement.objects.get_or_create(
            parent=forest_add,
            name_uz="Pichan o`rish",
            name_ru="Сенокошение",
            period=PeriodChoices.YILLIK
        )

        hay_app = create_column(
            pichan_statement,
            None,
            "Pichan o‘rish ilovasi",
            "Приложение: Сенокошение",
            "1"
        )

        hay_title = create_column(
            pichan_statement,
            hay_app,
            "O‘rmon xo‘jaligi agentligi tizimidagi xo‘jaliklarda o‘rmon fondi yerlarida pichan o‘rish uchun berilgan yerlar hisoboti bo‘yicha ________ yil holatiga maʼlumot",
            "Информация по состоянию на ________ год о сенокосных угодьях, предоставленных в лесном фонде хозяйствам в системе Агентства лесного хозяйства",
            "1.1"
        )

        create_column(pichan_statement, hay_title, "Tashkilot nomi", "Наименование организации", "1.1.1",
                      is_organization=True)
        create_column(pichan_statement, hay_title, "____ yil prognoz ko‘rsatkichlari, ming so‘m (reja)",
                      "Прогнозные показатели на ____ год, тыс. сум (план)", "1.1.2", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(pichan_statement, hay_title, "Jami pichan o‘rish mumkin bo‘lgan maydon (ga)",
                      "Общая площадь возможного сенокошения (га)", "1.1.3")
        create_column(pichan_statement, hay_title, "Pichan o‘riladigan yaroqli maydon (ga)",
                      "Пригодная площадь для сенокошения (га)", "1.1.4")
        create_column(pichan_statement, hay_title, "Shundan, pichan o‘riladigan maydon (ga)",
                      "Из них: площадь, на которой будет производиться сенокошение (га)", "1.1.5")
        create_column(pichan_statement, hay_title, "Foydalanuvchilar soni (dona)", "Количество пользователей (шт)",
                      "1.1.6")
        create_column(pichan_statement, hay_title, "Pichan o‘rish uchun kelib tushgan arizalar soni",
                      "Количество поступивших заявок на сенокошение", "1.1.7")
        create_column(pichan_statement, hay_title,
                      "Shundan pichan o‘rish uchun berilgan ruxsatnoma summasi (ming so‘m) (amalda)",
                      "Сумма выданных разрешений на сенокошение, тыс. сум (факт)", "1.1.8")
        create_column(pichan_statement, hay_title, "To‘langan summa (ming so‘m)", "Уплаченная сумма, тыс. сум",
                      "1.1.9")
        create_column(pichan_statement, hay_title, "Qolgan qismi (ming so‘m)", "Оставшаяся сумма, тыс. сум",
                      "1.1.10", is_user_input=False)
        create_column(pichan_statement, hay_title, "Jamg‘armalarga o‘tkazilgan mablag‘ (ming so‘m)",
                      "Средства, перечисленные в фонды, тыс. сум", "1.1.11")

        # ========== Yaylov ilovasi ==========
        yaylov_statement, _ = Statement.objects.get_or_create(
            parent=forest_add,
            name_uz="Yaylov hisoboti",
            name_ru="Пастбище",
            period=PeriodChoices.YILLIK
        )

        pasture_app = create_column(yaylov_statement, None, "Yaylov ilovasi", "Приложение: Пастбище", "1")
        pasture_title = create_column(
            yaylov_statement,
            pasture_app,
            "O‘rmon xo‘jaligi agentligi tizimidagi xo‘jaliklarda o‘rmon fondi yaylov hududlariga chorva mollarini joylashtirish boʻyicha ________ yil holatiga maʼlumot",
            "Информация по размещению скота на пастбищных участках лесного фонда в хозяйствах системы Агентства лесного хозяйства по состоянию на ________ год",
            "1.1"
        )

        create_column(yaylov_statement, pasture_title, "Tashkilot nomi", "Наименование организации", "1.1.1",
                      is_organization=True)
        create_column(yaylov_statement, pasture_title, "_____ yil prognoz ko‘rsatkichlari, ming so‘m (reja)",
                      "Прогнозные показатели на _____ год, тыс. сум (план)", "1.1.2", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(yaylov_statement, pasture_title, "Jami yaylov maydoni (ga)", "Общая площадь пастбищ (га)",
                      "1.1.3")
        create_column(yaylov_statement, pasture_title, "Mol boqishga yaroqli maydon (ga)",
                      "Пригодная площадь для выпаса скота (га)", "1.1.4")
        create_column(yaylov_statement, pasture_title, "Shundan, chorva boqilayotgan maydon (ga)",
                      "Из них: площадь, на которой пасется скот (га)", "1.1.5")
        create_column(yaylov_statement, pasture_title, "Foydalanuvchilar soni (dona)",
                      "Количество пользователей (шт)", "1.1.6")
        create_column(yaylov_statement, pasture_title,
                      "Yaylovga joylashti-rilgan chorva mollari jami soni, (bosh)",
                      "Общее поголовье скота, размещенного на пастбище, (голова)", "1.1.7", is_user_input=False)

        chorva_turi = create_column(yaylov_statement, pasture_title, "Shundan chorva mollarining turi, soni, so‘mmasi, ming so‘m",
                                    "Из них вид, количество, сумма, тыс. сум.", "1.1.8")
        create_column(yaylov_statement, chorva_turi, "Mayda shoxli mollar", "Мелкий рогатый скот", "1.1.8.1")
        create_column(yaylov_statement, chorva_turi, "Echkilar", "Козы", "1.1.8.2")
        create_column(yaylov_statement, chorva_turi, "Mayda shoxli mollar va echkilar uchun to‘lanadigan so‘m, ming so‘m",
                      "Сумы, уплачиваемые за мелкого рогатого скота и коз, тыс. сум.", "1.1.8.3")
        create_column(yaylov_statement, chorva_turi, "6 oygacha MShM (qo‘zi, uloq)",
                      "До 6 месяцев МРС (ягнята, козлята)", "1.1.8.4")
        create_column(yaylov_statement, chorva_turi, "6 oygacha qo‘zi/uloq (ming so‘m)",
                      "До 6 месяцев (ягнята/козлята), тыс. сум", "1.1.8.5")
        create_column(yaylov_statement, chorva_turi, "Yirik shoxli mollar", "Крупный рогатый скот", "1.1.8.6")
        create_column(yaylov_statement, chorva_turi, "Yilqilar, tuyalar", "Лошади, верблюды", "1.1.8.7")
        create_column(yaylov_statement, chorva_turi, "Eshaklar", "Ослики", "1.1.8.8")
        create_column(yaylov_statement, chorva_turi, "YSHM, otlar, tuyalar, eshaklar (ming so‘m)",
                      "КРС, лошади, верблюды, ослы (тыс. сум)", "1.1.8.9")
        create_column(yaylov_statement, chorva_turi, "2 yoshgacha YSHM", "До 2 лет КРС", "1.1.8.10")
        create_column(yaylov_statement, chorva_turi, "2 yoshgacha YSHM (ming so‘m)",
                      "До 2 лет КРС, тыс. сум", "1.1.8.11")

        create_column(yaylov_statement, pasture_title,
                      "Yaylov uchun tuzilgan shartnoma summasi (ming so‘m, amalda)",
                      "Сумма заключенного договора на пастбище (тыс. сум, факт)", "1.1.9", is_user_input=False)
        create_column(yaylov_statement, pasture_title, "To‘langan summa (ming so‘m)", "Уплаченная сумма (тыс. сум)",
                      "1.1.10")
        create_column(yaylov_statement, pasture_title, "Qolgan qismi (ming so‘m)", "Оставшаяся сумма (тыс. сум)",
                      "1.1.11", is_user_input=False)
        create_column(yaylov_statement, pasture_title, "Jamg‘armaga o‘tkazilgan mablag‘ (ming so‘m)",
                      "Средства, перечисленные в фонд (тыс. сум)", "1.1.12")

        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Mexanizatsiya hisobi' Statement and Columns."))
        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Pichan Urish hisobi' Statement and Columns."))
        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Yaylov hisobi' Statement and Columns."))
