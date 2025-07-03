from django.core.management import BaseCommand

from apps.reports.models import StatementColumn, Statement
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    def handle(self, *args, **options):
        def create_column(statement, parent, title, title_ru, ordering, is_organization=False, status_plan=None):
            return StatementColumn.objects.create(
                statement=statement,
                parent=parent,
                title=title,
                title_ru=title_ru,
                ordering=ordering,
                is_organization=is_organization,
                status_plan=status_plan
            )

        forest_statement = Statement.objects.get(
            name_uz="O'rmonlardan qo'shimcha foydalanish",
            name_ru="Дополнительное использование лесов",
            period=PeriodChoices.YILLIK
        )
        statement_husbandry = Statement.objects.create(
            parent=forest_statement,
            name_uz="Chorvachilik",
            name_ru="Животноводство"
        )

        # ========== Й.Ш.М ilovasi ==========
        y_sh_m_ilova = create_column(statement_husbandry, None, "Yirik shohli mollar ilovasi", "Приложение: КРС", "1")

        y_sh_m_title = create_column(
            statement_husbandry,
            y_sh_m_ilova,
            "Agentlik tizimidagi o‘rmon xo‘jaliklarida 2025 yilda Yirik shohli mollarni rivojlantirish bo‘yicha MA’LUMOT",
            "Информация о развитии крупного рогатого скота в лесных хозяйствах системы агентства в 2025 году",
            "1.1"
        )

        create_column(statement_husbandry, y_sh_m_title, "Xo‘jaliklar nomi", "Наименование хозяйства", "1.1.1", is_organization=True)
        year_moment = create_column(statement_husbandry, y_sh_m_title, "01.01.2025 yil holatiga", "Состояние на 01.01.2025", "1.1.2")
        general_number = create_column(statement_husbandry, year_moment, "Jami bosh soni", "Общее количество голов", "1.1.2.1")
        create_column(statement_husbandry, general_number, "Amalda", "Факт", "1.1.2.1.1")
        create_column(statement_husbandry, year_moment, "Shundan: sigirlar", "Из них: коровы", "1.1.2.2")

        get_buzoq = create_column(statement_husbandry, y_sh_m_title, "2025 yilda buzoq olish", "Получение телят в 2025 году", "1.1.3")
        create_column(statement_husbandry, get_buzoq, "Reja", "План", "1.1.3.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, get_buzoq, "Amalda", "Факт", "1.1.3.2")

        new_column = create_column(statement_husbandry, y_sh_m_title, "Yangidan tashkil qilish, bosh", "Создание новых, голов", "1.1.4")
        create_column(statement_husbandry, new_column, "Reja", "План", "1.1.4.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, new_column, "Amalda", "Факт", "1.1.4.2")

        meat_column = create_column(statement_husbandry, y_sh_m_title, "Go‘shtga so‘yildi", "Зарезано на мясо", "1.1.5")
        create_column(statement_husbandry, meat_column, "Bosh soni", "Количество голов", "1.1.5.1")
        create_column(statement_husbandry, meat_column, "CN", "ЦН", "1.1.5.2")

        create_column(statement_husbandry, y_sh_m_title, "Sotilgan", "Продано", "1.1.6")
        create_column(statement_husbandry, y_sh_m_title, "Talofat va nobud bo‘lgan", "Погибло и утрачено", "1.1.7")
        create_column(statement_husbandry, y_sh_m_title, "Jami chiqim, bosh", "Общий расход, голов", "1.1.8")

        next_year_moment = create_column(statement_husbandry, y_sh_m_title, "01.04.2025 yil holatiga", "Состояние на 01.04.2025", "1.1.9")
        second_general_number = create_column(statement_husbandry, next_year_moment, "Jami bosh soni", "Общее количество голов", "1.1.9.1")
        create_column(statement_husbandry, second_general_number, "Reja", "План", "1.1.9.1.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, second_general_number, "Amalda", "Факт", "1.1.9.1.2")
        create_column(statement_husbandry, next_year_moment, "Shundan: sigirlar", "Из них: коровы", "1.1.9.2")

        # ========== Yilqichilik ilovasi ==========
        yilqichilik_app = create_column(statement_husbandry, None, "Yilqichilik ilovasi", "Приложение: Коневодство",
                                        "1")
        yilqichilik_title = create_column(
            statement_husbandry,
            yilqichilik_app,
            "Agentlik tizimidagi o‘rmon xo‘jaliklarida 2025 yilda Yilqichilikni rivojlantirish bo‘yicha MA’LUMOT",
            "Информация о развитии коневодства в лесных хозяйствах системы агентства в 2025 году",
            "1.1"
        )

        create_column(statement_husbandry, yilqichilik_title, "Xo‘jaliklar nomi", "Наименование хозяйства", "1.1.1",
                      is_organization=True)
        yil_start = create_column(statement_husbandry, yilqichilik_title, "01.01.2025 yil holatiga mavjud",
                                  "Состояние на 01.01.2025", "1.1.2")
        start_general = create_column(statement_husbandry, yil_start, "Jami bosh soni", "Общее количество голов",
                                      "1.1.2.1")
        create_column(statement_husbandry, start_general, "Amalda", "Факт", "1.1.2.1.1")
        create_column(statement_husbandry, yil_start, "Shundan: biyalar", "Из них: кобылы", "1.1.2.2")

        foal = create_column(statement_husbandry, yilqichilik_title, "1025 yilda qulun olish",
                             "Получение жеребят в 2025 году", "1.1.3")
        create_column(statement_husbandry, foal, "Reja", "План", "1.1.3.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, foal, "Amalda", "Факт", "1.1.3.2")

        yangi = create_column(statement_husbandry, yilqichilik_title, "Yangidan tashkil qilish", "Создание новых",
                              "1.1.4")
        create_column(statement_husbandry, yangi, "Reja", "План", "1.1.4.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, yangi, "Amalda", "Факт", "1.1.4.2")

        gosht = create_column(statement_husbandry, yilqichilik_title, "Go‘shtga so‘yildi", "Зарезано на мясо", "1.1.5")
        create_column(statement_husbandry, gosht, "Bosh soni", "Количество голов", "1.1.5.1")
        create_column(statement_husbandry, gosht, "CN", "ЦН", "1.1.5.2")

        create_column(statement_husbandry, yilqichilik_title, "Sotilgan", "Продано", "1.1.6")
        create_column(statement_husbandry, yilqichilik_title, "Talofat va nobud bo‘lgan", "Погибло и утрачено", "1.1.7")
        create_column(statement_husbandry, yilqichilik_title, "Jami chiqim, bosh", "Общий расход, голов", "1.1.8")

        yil_end = create_column(statement_husbandry, yilqichilik_title, "01.04.2025 yil holatiga mavjud",
                                "Состояние на 01.04.2025", "1.1.9")
        end_general = create_column(statement_husbandry, yil_end, "Jami bosh soni", "Общее количество голов", "1.1.9.1")
        create_column(statement_husbandry, end_general, "Reja", "План", "1.1.9.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, end_general, "Amalda", "Факт", "1.1.9.1.2")
        create_column(statement_husbandry, yil_end, "Shundan: biyalar", "Из них: кобылы", "1.1.9.2")

        # ========== Mayda shohli mollar ilovasi ==========
        m_sh_m_app = create_column(statement_husbandry, None, "Mayda shohli mollar ilovasi", "Приложение: МРС", "1")
        m_sh_m_title = create_column(
            statement_husbandry,
            m_sh_m_app,
            "Agentlik tizimidagi o‘rmon xo‘jaliklarida 2025 yilda Mayda shohli mollarni rivojlantirish bo‘yicha MA’LUMOT",
            "Информация о развитии мелкого рогатого скота в лесных хозяйствах системы агентства в 2025 году",
            "1.1"
        )

        create_column(statement_husbandry, m_sh_m_title, "Xo‘jaliklar nomi", "Наименование хозяйства", "1.1.1",
                      is_organization=True)

        start_block = create_column(statement_husbandry, m_sh_m_title, "01.01.2025 yil holatiga",
                                    "Состояние на 01.01.2025", "1.1.2")
        total_count_start = create_column(statement_husbandry, start_block, "Jami bosh soni", "Общее количество голов",
                                          "1.1.2.1")
        create_column(statement_husbandry, total_count_start, "Amalda", "Факт", "1.1.2.1.1")
        sub_sovliq = create_column(statement_husbandry, start_block, "Shundan: sovliqlar", "Из них: овцематки",
                                   "1.1.2.2")
        create_column(statement_husbandry, sub_sovliq, "Amalda", "Факт", "1.1.2.2.1")

        kuzulok_block = create_column(statement_husbandry, m_sh_m_title, "2025 yilda qo‘ziquloq olish",
                                      "Получение ягнят в 2025 году", "1.1.3")
        create_column(statement_husbandry, kuzulok_block, "Reja", "План", "1.1.3.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, kuzulok_block, "Amalda", "Факт", "1.1.3.2")

        tashkil_block = create_column(statement_husbandry, m_sh_m_title, "2025 yilda yangidan tashkil etish, dona",
                                      "Создание новых в 2025 году, ед.", "1.1.4")
        create_column(statement_husbandry, tashkil_block, "Reja", "План", "1.1.4.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, tashkil_block, "Amalda", "Факт", "1.1.4.2")

        gosht_block = create_column(statement_husbandry, m_sh_m_title, "Go‘shtga so‘yildi", "Зарезано на мясо", "1.1.5")
        create_column(statement_husbandry, gosht_block, "Bosh", "Голов", "1.1.5.1")

        create_column(statement_husbandry, m_sh_m_title, "Go‘sht ishlab chiqarish (CN)", "Производство мяса (ЦН)",
                      "1.1.6")
        create_column(statement_husbandry, m_sh_m_title, "Issiq ovqatga so‘yish", "Забой на горячее питание", "1.1.7")
        create_column(statement_husbandry, m_sh_m_title, "Sotilgan", "Продано", "1.1.8")
        create_column(statement_husbandry, m_sh_m_title, "Kamomad", "Убыль", "1.1.9")
        create_column(statement_husbandry, m_sh_m_title, "Talofat va nobud bo‘lgan", "Погибло и утрачено", "1.1.10")
        create_column(statement_husbandry, m_sh_m_title, "Jami chiqim, bosh", "Общий расход, голов", "1.1.11")

        hojalik_block = create_column(statement_husbandry, m_sh_m_title, "Xo‘jaliklar tomonidan _____ yil holatiga",
                                      "По состоянию на _____ год со стороны хозяйств", "1.1.12")
        total_hojalik = create_column(statement_husbandry, hojalik_block, "Jami bosh soni", "Общее количество голов",
                                      "1.1.12.1")
        create_column(statement_husbandry, total_hojalik, "Reja", "План", "1.1.12.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_hojalik, "Amalda", "Факт", "1.1.12.1.2")
        sovliq_hojalik = create_column(statement_husbandry, hojalik_block, "Shundan: sovliqlar", "Из них: овцематки",
                                       "1.1.12.2")
        create_column(statement_husbandry, sovliq_hojalik, "Amalda", "Факт", "1.1.12.2.1")

        sektor_block = create_column(statement_husbandry, m_sh_m_title,
                                     "Xususiy sektorlarni jalb qilgan holda _____ yil holatiga",
                                     "По состоянию на _____ год с привлечением частного сектора", "1.1.13")
        total_sektor = create_column(statement_husbandry, sektor_block, "Jami bosh soni", "Общее количество голов",
                                     "1.1.13.1")
        create_column(statement_husbandry, total_sektor, "Reja", "План", "1.1.13.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_sektor, "Amalda", "Факт", "1.1.13.1.2")
        sovliq_sektor = create_column(statement_husbandry, sektor_block, "Shundan: sovliqlar", "Из них: овцематки",
                                      "1.1.13.2")
        create_column(statement_husbandry, sovliq_sektor, "Amalda", "Факт", "1.1.13.2.1")

        jami_chorva = create_column(statement_husbandry, m_sh_m_title, "Jami chorva ________ yil holatiga",
                                    "Общее поголовье по состоянию на ________ год", "1.1.14")
        jami_total = create_column(statement_husbandry, jami_chorva, "Jami bosh soni", "Общее количество голов",
                                   "1.1.14.1")
        create_column(statement_husbandry, jami_total, "Reja", "План", "1.1.14.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, jami_total, "Amalda", "Факт", "1.1.14.1.2")
        sovliq_total = create_column(statement_husbandry, jami_chorva, "Shundan: sovliqlar", "Из них: овцематки",
                                     "1.1.14.2")
        create_column(statement_husbandry, sovliq_total, "Amalda", "Факт", "1.1.14.2.1")

        # ========== Parrandachilik ilovasi ==========
        parranda_app = create_column(statement_husbandry, None, "Parrandachilik ilovasi", "Приложение: Птицеводство",
                                     "1")
        parranda_title = create_column(
            statement_husbandry,
            parranda_app,
            "Agentlik tizimidagi o‘rmon xo‘jaliklarida 2025 yilda parrandachilik bo‘yicha MA’LUMOT",
            "Информация о птицеводстве в лесных хозяйствах системы агентства в 2025 году",
            "1.1"
        )

        create_column(statement_husbandry, parranda_title, "Xo‘jaliklar nomi", "Наименование хозяйства", "1.1.1",
                      is_organization=True)

        year_parranda = create_column(statement_husbandry, parranda_title, "01.01.2025 yil holatiga mavjud",
                                      "Состояние на 01.01.2025", "1.1.2")
        jami_parranda = create_column(statement_husbandry, year_parranda, "Jami parranda", "Общее количество птицы",
                                      "1.1.2.1")
        create_column(statement_husbandry, jami_parranda, "Amalda", "Факт", "1.1.2.1.1")
        shundan_parranda = create_column(statement_husbandry, year_parranda, "Shundan", "Из них", "1.1.2.2")
        create_column(statement_husbandry, shundan_parranda, "Kurka soni", "Количество индеек", "1.1.2.2.1")
        create_column(statement_husbandry, shundan_parranda, "Jami tovuq va xo‘roz soni",
                      "Общее количество кур и петухов", "1.1.2.2.2")
        create_column(statement_husbandry, shundan_parranda, "Tuxum beradigan tovuq soni", "Количество несушек",
                      "1.1.2.2.3")

        new_tashkil_column = create_column(statement_husbandry, parranda_title, "Yangi tashkil etiladi",
                                           "Будет создано заново", "1.1.3")
        first_kurka = create_column(statement_husbandry, new_tashkil_column, "Kurka", "Индейка", "1.1.3.1")
        create_column(statement_husbandry, first_kurka, "Reja", "План", "1.1.3.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, first_kurka, "Amalda", "Факт", "1.1.3.1.2")
        first_chicken = create_column(statement_husbandry, new_tashkil_column, "Tovuq", "Курица", "1.1.3.2")
        create_column(statement_husbandry, first_chicken, "Reja", "План", "1.1.3.2.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, first_chicken, "Amalda", "Факт", "1.1.3.2.2")

        meat_25 = create_column(statement_husbandry, parranda_title, "Go‘shtga so‘yildi (25%)",
                                "Зарезано на мясо (25%)", "1.1.4")
        second_kurka = create_column(statement_husbandry, meat_25, "Kurka", "Индейка", "1.1.4.1")
        create_column(statement_husbandry, second_kurka, "Reja", "План", "1.1.4.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, second_kurka, "Amalda", "Факт", "1.1.4.1.2")
        second_chicken = create_column(statement_husbandry, meat_25, "Tovuq", "Курица", "1.1.4.2")
        create_column(statement_husbandry, second_chicken, "Reja", "План", "1.1.4.2.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, second_chicken, "Amalda", "Факт", "1.1.4.2.2")

        gosht_kg = create_column(
            statement_husbandry,
            parranda_title,
            "Go‘sht ishlab chiqarish tovuqlarda (1.1 kg), kurkalarda (2.8 kg)",
            "Производство мяса: курица (1.1 кг), индейка (2.8 кг)",
            "1.1.5"
        )
        kurka_kg = create_column(statement_husbandry, gosht_kg, "Kurka", "Индейка", "1.1.5.1")
        create_column(statement_husbandry, kurka_kg, "Reja", "План", "1.1.5.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, kurka_kg, "Amalda", "Факт", "1.1.5.1.2")
        tovuq_kg = create_column(statement_husbandry, gosht_kg, "Tovuq", "Курица", "1.1.5.2")
        create_column(statement_husbandry, tovuq_kg, "Reja", "План", "1.1.5.2.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, tovuq_kg, "Amalda", "Факт", "1.1.5.2.2")

        egg_block = create_column(statement_husbandry, parranda_title,
                                  "Tuxum ishlab chiqarish (1 ta tovuq 110 ta tuxum) ming dona",
                                  "Производство яиц (110 штук от одной курицы), тыс. шт.", "1.1.6")
        kurka_egg = create_column(statement_husbandry, egg_block, "Kurka", "Индейка", "1.1.6.1")
        create_column(statement_husbandry, kurka_egg, "Reja", "План", "1.1.6.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, kurka_egg, "Amalda", "Факт", "1.1.6.1.2")
        tovuq_egg = create_column(statement_husbandry, egg_block, "Tovuq", "Курица", "1.1.6.2")
        create_column(statement_husbandry, tovuq_egg, "Reja", "План", "1.1.6.2.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, tovuq_egg, "Amalda", "Факт", "1.1.6.2.2")

        create_column(statement_husbandry, parranda_title, "Jami chiqim, bosh", "Общий расход, голов", "1.1.7")

        hojalik_parranda = create_column(statement_husbandry, parranda_title,
                                         "Xo‘jaliklar tomonidan tashkil etildi 01.04.2025 yil holatiga",
                                         "Создано со стороны хозяйств по состоянию на 01.04.2025", "1.1.8")
        total_hojalik = create_column(statement_husbandry, hojalik_parranda, "Jami parranda", "Общее количество птицы",
                                      "1.1.8.1")
        create_column(statement_husbandry, total_hojalik, "Reja", "План", "1.1.8.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_hojalik, "Amalda", "Факт", "1.1.8.1.2")
        shundan_hojalik = create_column(statement_husbandry, hojalik_parranda, "Shundan", "Из них", "1.1.8.2")
        create_column(statement_husbandry, shundan_hojalik, "Kurka soni", "Количество индеек", "1.1.8.2.1")
        create_column(statement_husbandry, shundan_hojalik, "Jami tovuq va xo‘roz soni",
                      "Общее количество кур и петухов", "1.1.8.2.2")
        create_column(statement_husbandry, shundan_hojalik, "Tuxum beradigan tovuq soni", "Количество несушек",
                      "1.1.8.2.3")

        sektor_parranda = create_column(statement_husbandry, parranda_title,
                                        "Xususiy sektor tomonidan tashkil etildi 01.04.2025 yil holatiga",
                                        "Создано со стороны частного сектора по состоянию на 01.04.2025", "1.1.9")
        total_sektor = create_column(statement_husbandry, sektor_parranda, "Jami parranda", "Общее количество птицы",
                                     "1.1.9.1")
        create_column(statement_husbandry, total_sektor, "Reja", "План", "1.1.9.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_sektor, "Amalda", "Факт", "1.1.9.1.2")
        shundan_sektor = create_column(statement_husbandry, sektor_parranda, "Shundan", "Из них", "1.1.9.2")
        create_column(statement_husbandry, shundan_sektor, "Kurka soni", "Количество индеек", "1.1.9.2.1")
        create_column(statement_husbandry, shundan_sektor, "Jami tovuq va xo‘roz soni",
                      "Общее количество кур и петухов", "1.1.9.2.2")
        create_column(statement_husbandry, shundan_sektor, "Tuxum beradigan tovuq soni", "Количество несушек",
                      "1.1.9.2.3")

        jami_parranda = create_column(statement_husbandry, parranda_title,
                                      "Jami tashkil etilgan parranda 01.04.2025 yil holatiga",
                                      "Общее количество созданной птицы по состоянию на 01.04.2025", "1.1.10")
        total_jami = create_column(statement_husbandry, jami_parranda, "Jami parranda", "Общее количество птицы",
                                   "1.1.10.1")
        create_column(statement_husbandry, total_jami, "Reja", "План", "1.1.10.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_jami, "Amalda", "Факт", "1.1.10.1.2")
        shundan_jami = create_column(statement_husbandry, jami_parranda, "Shundan", "Из них", "1.1.10.2")
        create_column(statement_husbandry, shundan_jami, "Kurka soni", "Количество индеек", "1.1.10.2.1")
        create_column(statement_husbandry, shundan_jami, "Jami tovuq va xo‘roz soni", "Общее количество кур и петухов",
                      "1.1.10.2.2")
        create_column(statement_husbandry, shundan_jami, "Tuxum beradigan tovuq soni", "Количество несушек",
                      "1.1.10.2.3")

        # ========== Asalarichilik ilovasi ==========
        bees_app = create_column(statement_husbandry, None, "Asalarichilik ilovasi", "Приложение: Пчеловодство", "1")
        bees_title = create_column(
            statement_husbandry,
            bees_app,
            "Agentlik tizimidagi o‘rmon xo‘jaliklarida 2025 yilda asalarichilik bo‘yicha MA’LUMOT",
            "Информация о пчеловодстве в лесных хозяйствах системы агентства в 2025 году",
            "1.1"
        )

        create_column(statement_husbandry, bees_title, "Xo‘jaliklar nomi", "Наименование хозяйства", "1.1.1",
                      is_organization=True)
        create_column(statement_husbandry, bees_title, "01.01.2025 yil holatiga mavjud asalari oilasi soni",
                      "Состояние на 01.01.2025 — количество пчелиных семей", "1.1.2")

        asal_kg = create_column(statement_husbandry, bees_title, "Asal ishlab chiqarish, kg", "Производство меда, кг",
                                "1.1.3")
        create_column(statement_husbandry, asal_kg, "Reja", "План", "1.1.3.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, asal_kg, "Amalda", "Факт", "1.1.3.2")

        tovar_asal = create_column(statement_husbandry, bees_title, "Shundan: tovar asal ishlab chiqarish, kg",
                                   "Из них: товарный мед, кг", "1.1.4")
        create_column(statement_husbandry, tovar_asal, "Reja", "План", "1.1.4.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, tovar_asal, "Amalda", "Факт", "1.1.4.2")

        new_bee_2025 = create_column(statement_husbandry, bees_title,
                                     "2025 yilda yangidan asalari oilasi tashkil etish",
                                     "Создание новых пчелиных семей в 2025 году", "1.1.5")
        create_column(statement_husbandry, new_bee_2025, "Reja", "План", "1.1.5.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, new_bee_2025, "Amalda", "Факт", "1.1.5.2")

        hoz_bee = create_column(statement_husbandry, bees_title,
                                "01.04.2025 yil holatiga xo‘jalik tomonidan asalari oilasi tashkil etish",
                                "Создание пчелиных семей со стороны хозяйств по состоянию на 01.04.2025", "1.1.6")
        create_column(statement_husbandry, hoz_bee, "Reja", "План", "1.1.6.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, hoz_bee, "Amalda", "Факт", "1.1.6.2")

        sektor_bee = create_column(statement_husbandry, bees_title,
                                   "01.04.2025 yil holatiga xususiy sektor tomonidan asalari oilasi tashkil etish",
                                   "Создание пчелиных семей со стороны частного сектора по состоянию на 01.04.2025",
                                   "1.1.7")
        create_column(statement_husbandry, sektor_bee, "Reja", "План", "1.1.7.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, sektor_bee, "Amalda", "Факт", "1.1.7.2")

        total_bee = create_column(statement_husbandry, bees_title,
                                  "01.04.2025 yil holatiga jami tashkil etilgan asalari oilasi soni",
                                  "Общее количество созданных пчелиных семей по состоянию на 01.04.2025", "1.1.8")
        create_column(statement_husbandry, total_bee, "Reja", "План", "1.1.8.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)

        # ========== Baliqchilik ilovasi ==========
        fish_app = create_column(statement_husbandry, None, "Baliqchilik ilovasi", "Приложение: Рыбоводство", "6")
        fish_title = create_column(
            statement_husbandry,
            fish_app,
            "O‘rmon xo‘jaligi agentligi huzuridagi xo‘jaliklardagi 2025 yilda baliq mahsulotlarini yetishtirilishi bo‘yicha MA’LUMOT",
            "Информация о производстве рыбной продукции в хозяйствах при агентстве лесного хозяйства в 2025 году",
            "6.1"
        )

        create_column(statement_husbandry, fish_title, "Xo‘jaliklar nomi", "Наименование хозяйства", "1.1.1",
                      is_organization=True)
        create_column(statement_husbandry, fish_title, "Jami baliq ko‘llari maydoni (ga)",
                      "Общая площадь рыбных прудов (га)", "1.1.2")
        create_column(statement_husbandry, fish_title, "Jami yetishtirilgan mahsulot (tn)",
                      "Общий объем произведенной продукции (тн)", "1.1.3")

        wundan = create_column(statement_husbandry, fish_title, "Shundan", "Из них", "1.1.4")
        create_column(statement_husbandry, wundan, "Xo‘jalik balansidagi baliq ko‘llari maydoni (ga)",
                      "Площадь прудов на балансе хозяйства (га)", "1.1.5")
        create_column(statement_husbandry, wundan, "Yetishtirilgan mahsulot (tn)", "Произведенная продукция (тн)",
                      "1.1.6")
        create_column(statement_husbandry, wundan, "Ijarachilar hisobidagi baliq ko‘llari maydoni (ga)",
                      "Площадь прудов в аренде (га)", "1.1.7")
        create_column(statement_husbandry, wundan, "Yetishtirilgan mahsulot (tn)", "Произведенная продукция (тн)",
                      "1.1.8")

        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Chorvachilik hisobi' Statement and Columns."))
