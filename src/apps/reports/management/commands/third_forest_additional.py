from datetime import datetime
from django.core.management import BaseCommand

from apps.reports.models import StatementColumn, Statement
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    def handle(self, *args, **options):
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        month_str = f"{current_month:02d}"
        date_str = f"01.{month_str}.{current_year}"

        def create_column(statement, parent, title_uz, title_ru, ordering, is_organization=False, status_plan=None,
                          is_user_input=True):
            return StatementColumn.objects.create(
                statement=statement,
                parent=parent,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=ordering,
                is_organization=is_organization,
                status_plan=status_plan,
                is_user_input=is_user_input
            )

        forest_statement = Statement.objects.get(
            name_uz="O'rmonlardan qo'shimcha foydalanish",
            name_ru="Дополнительное использование лесов",
            period=PeriodChoices.YILLIK
        )
        statement_husbandry = Statement.objects.create(
            parent=forest_statement,
            name_uz="Chorvachilik",
            name_ru="Животноводство",
            period=PeriodChoices.YILLIK
        )
        statement_medicine = Statement.objects.create(
            parent=forest_statement,
            name_uz="Dorivor yetishtirish",
            name_ru="Лекарственное выращивание",
            period=PeriodChoices.OYLIK
        )

        # ========== Й.Ш.М ilovasi ==========
        y_sh_m_ilova = create_column(statement_husbandry, None, "Yirik shohli mollar ilovasi", "Приложение: КРС", "1")

        y_sh_m_title = create_column(
            statement_husbandry,
            y_sh_m_ilova,
            f"Agentlik tizimidagi o‘rmon xo‘jaliklarida {current_year} yilda Yirik shohli mollarni rivojlantirish bo‘yicha MA’LUMOT", # last month first
            f"Информация о развитии крупного рогатого скота в лесных хозяйствах системы агентства в {current_year} году",
            "1.1"
        )

        create_column(statement_husbandry, y_sh_m_title, "Tashkilot nomi", "Наименование хозяйства", "1.1.1",
                      is_organization=True)
        year_moment = create_column(statement_husbandry, y_sh_m_title, f"01.01.{current_year} yil holatiga",
                                    f"Состояние на 01.01.{current_year}", "1.1.2")
        general_number = create_column(statement_husbandry, year_moment, "Jami bosh soni", "Общее количество голов",
                                       "1.1.2.1")
        create_column(statement_husbandry, general_number, "Amalda", "Факт", "1.1.2.1.1")
        create_column(statement_husbandry, year_moment, "Shundan: sigirlar", "Из них: коровы", "1.1.2.2")

        get_buzoq = create_column(statement_husbandry, y_sh_m_title, f"{current_year} yilda buzoq olish",
                                  f"Получение телят в {current_year} году", "1.1.3")
        create_column(statement_husbandry, get_buzoq, "Reja", "План", "1.1.3.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, get_buzoq, "Amalda", "Факт", "1.1.3.2")

        new_column = create_column(statement_husbandry, y_sh_m_title, "Yangidan sotib olindi, bosh",
                                   "Вновь приобретено, голов", "1.1.4")
        create_column(statement_husbandry, new_column, "Amalda", "Факт", "1.1.4.1")

        meat_column = create_column(statement_husbandry, y_sh_m_title, "Go‘shtga so‘yildi", "Зарезано на мясо", "1.1.5")
        create_column(statement_husbandry, meat_column, "Bosh soni", "Количество голов", "1.1.5.1")
        create_column(statement_husbandry, meat_column, "tonna", "тонна", "1.1.5.2")

        create_column(statement_husbandry, y_sh_m_title, "Sotilgan (bosh soni)", "Продано (количество голов)", "1.1.6")
        create_column(statement_husbandry, y_sh_m_title, "Talofat va nobud bo‘lgan", "Погибло и утрачено", "1.1.7")
        create_column(statement_husbandry, y_sh_m_title, "Jami chiqim, bosh", "Общий расход, голов", "1.1.8")

        next_year_moment = create_column(statement_husbandry, y_sh_m_title, f"{date_str} yil holatiga",
                                         f"Состояние на {date_str}", "1.1.9")
        second_general_number = create_column(statement_husbandry, next_year_moment, "Jami bosh soni",
                                              "Общее количество голов", "1.1.9.1")
        create_column(statement_husbandry, second_general_number, "Reja", "План", "1.1.9.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, second_general_number, "Amalda", "Факт", "1.1.9.1.2")
        create_column(statement_husbandry, next_year_moment, "Shundan: sigirlar", "Из них: коровы", "1.1.9.2")

        # ========== Yilqichilik ilovasi ==========
        yilqichilik_app = create_column(statement_husbandry, None, "Yilqichilik ilovasi", "Приложение: Коневодство",
                                        "2")
        yilqichilik_title = create_column(
            statement_husbandry,
            yilqichilik_app,
            f"Agentlik tizimidagi o‘rmon xo‘jaliklarida {current_year} yilda Yilqichilikni rivojlantirish bo‘yicha MA’LUMOT",
            f"Информация о развитии коневодства в лесных хозяйствах системы агентства в {current_year} году",
            "2.1"
        )

        create_column(statement_husbandry, yilqichilik_title, "Tashkilot nomi", "Наименование хозяйства", "2.1.1",
                      is_organization=True)
        yil_start = create_column(statement_husbandry, yilqichilik_title, f"01.01.{current_year} yil holatiga mavjud",
                                  f"Состояние на 01.01.{current_year}", "2.1.2")
        start_general = create_column(statement_husbandry, yil_start, "Jami bosh soni", "Общее количество голов",
                                      "2.1.2.1")
        create_column(statement_husbandry, start_general, "Amalda", "Факт", "2.1.2.1.1")
        create_column(statement_husbandry, yil_start, "Shundan: biyalar", "Из них: кобылы", "2.1.2.2")

        foal = create_column(statement_husbandry, yilqichilik_title, f"{current_year} yilda qulun olish",
                             f"Получение жеребят в {current_year} году", "2.1.3")
        create_column(statement_husbandry, foal, "Reja", "План", "2.1.3.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, foal, "Amalda", "Факт", "2.1.3.2")

        yangi = create_column(statement_husbandry, yilqichilik_title, "Yangidan sotib olindi", "Вновь приобретено",
                              "2.1.4")
        create_column(statement_husbandry, yangi, "Amalda", "Факт", "2.1.4.1")

        gosht = create_column(statement_husbandry, yilqichilik_title, "Go‘shtga so‘yildi", "Зарезано на мясо", "2.1.5")
        create_column(statement_husbandry, gosht, "Bosh soni", "Количество голов", "2.1.5.1")
        create_column(statement_husbandry, gosht, "CN", "ЦН", "2.1.5.2")

        create_column(statement_husbandry, yilqichilik_title, "Sotilgan", "Продано", "2.1.6")
        create_column(statement_husbandry, yilqichilik_title, "Talofat va nobud bo‘lgan", "Погибло и утрачено", "2.1.7")
        create_column(statement_husbandry, yilqichilik_title, "Jami chiqim, bosh", "Общий расход, голов", "2.1.8")

        yil_end = create_column(statement_husbandry, yilqichilik_title, f"{date_str} yil holatiga mavjud",
                                f"Состояние на {date_str}", "2.1.9")
        end_general = create_column(statement_husbandry, yil_end, "Jami bosh soni", "Общее количество голов", "2.1.9.1")
        create_column(statement_husbandry, end_general, "Reja", "План", "2.1.9.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, end_general, "Amalda", "Факт", "2.1.9.1.2")
        create_column(statement_husbandry, yil_end, "Shundan: biyalar", "Из них: кобылы", "2.1.9.2")

        # ========== Mayda shohli mollar ilovasi ==========
        m_sh_m_app = create_column(statement_husbandry, None, "Mayda shohli mollar ilovasi", "Приложение: МРС", "3")
        m_sh_m_title = create_column(
            statement_husbandry,
            m_sh_m_app,
            f"Agentlik tizimidagi o‘rmon xo‘jaliklarida {current_year} yilda Mayda shohli mollarni rivojlantirish bo‘yicha MA’LUMOT",
            f"Информация о развитии мелкого рогатого скота в лесных хозяйствах системы агентства в {current_year} году",
            "3.1"
        )

        create_column(statement_husbandry, m_sh_m_title, "Tashkilot nomi", "Наименование хозяйства", "3.1.1",
                      is_organization=True)

        start_block = create_column(statement_husbandry, m_sh_m_title, f"01.01.{current_year} yil holatiga",
                                    f"Состояние на 01.01.{current_year}", "3.1.2")
        total_count_start = create_column(statement_husbandry, start_block, "Jami bosh soni", "Общее количество голов",
                                          "3.1.2.1")
        create_column(statement_husbandry, total_count_start, "Amalda", "Факт", "3.1.2.1.1")
        sub_sovliq = create_column(statement_husbandry, start_block, "Shundan: sovliqlar", "Из них: овцематки",
                                   "3.1.2.2")
        create_column(statement_husbandry, sub_sovliq, "Amalda", "Факт", "3.1.2.2.1")

        kuzulok_block = create_column(statement_husbandry, m_sh_m_title, f"{current_year} yilda qo‘ziquloq olish",
                                      f"Получение ягнят в {current_year} году", "3.1.3")
        create_column(statement_husbandry, kuzulok_block, "Reja", "План", "3.1.3.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, kuzulok_block, "Amalda", "Факт", "3.1.3.2")

        tashkil_block = create_column(statement_husbandry, m_sh_m_title,
                                      f"{current_year} yilda yangidan tashkil etish, dona",
                                      f"Создание новых в {current_year} году, ед.", "3.1.4")
        create_column(statement_husbandry, tashkil_block, "Amalda", "Факт", "3.1.4.1")

        create_column(statement_husbandry, m_sh_m_title, "Go‘shtga so‘yildi bosh", "Зарезан на мясо", "3.1.5")

        create_column(statement_husbandry, m_sh_m_title, "Go‘sht ishlab chiqarish (CN)", "Производство мяса (ЦН)",
                      "3.1.6")
        create_column(statement_husbandry, m_sh_m_title, "Issiq ovqatga so‘yish", "Забой на горячее питание", "3.1.7")
        create_column(statement_husbandry, m_sh_m_title, "Sotilgan", "Продано", "3.1.8")
        create_column(statement_husbandry, m_sh_m_title, "Kamomad", "Убыль", "3.1.9")
        create_column(statement_husbandry, m_sh_m_title, "Talofat va nobud bo‘lgan", "Погибло и утрачено", "3.1.10")
        create_column(statement_husbandry, m_sh_m_title, "Jami chiqim, bosh", "Общий расход, голов", "3.1.11",
                      is_user_input=False)

        hojalik_block = create_column(statement_husbandry, m_sh_m_title,
                                      f"Xo‘jaliklar tomonidan {date_str} yil holatiga",
                                      f"По состоянию на {date_str} год со стороны хозяйств", "3.1.12")
        total_hojalik = create_column(statement_husbandry, hojalik_block, "Jami bosh soni", "Общее количество голов",
                                      "3.1.12.1")
        create_column(statement_husbandry, total_hojalik, "Reja", "План", "3.1.12.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_hojalik, "Amalda", "Факт", "3.1.12.1.2")
        sovliq_hojalik = create_column(statement_husbandry, hojalik_block, "Shundan: sovliqlar", "Из них: овцематки",
                                       "3.1.12.2")
        create_column(statement_husbandry, sovliq_hojalik, "Amalda", "Факт", "3.1.12.2.1")

        sektor_block = create_column(statement_husbandry, m_sh_m_title,
                                     f"Xususiy sektorlarni jalb qilgan holda {date_str} yil holatiga",
                                     f"По состоянию на {date_str} год с привлечением частного сектора", "3.1.13")
        total_sektor = create_column(statement_husbandry, sektor_block, "Jami bosh soni", "Общее количество голов",
                                     "3.1.13.1")
        create_column(statement_husbandry, total_sektor, "Reja", "План", "3.1.13.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_sektor, "Amalda", "Факт", "3.1.13.1.2")
        sovliq_sektor = create_column(statement_husbandry, sektor_block, "Shundan: sovliqlar", "Из них: овцематки",
                                      "3.1.13.2")
        create_column(statement_husbandry, sovliq_sektor, "Amalda", "Факт", "3.1.13.2.1")

        jami_chorva = create_column(statement_husbandry, m_sh_m_title, f"Jami chorva {date_str} yil holatiga",
                                    f"Общее поголовье по состоянию на {date_str} год", "3.1.14", is_user_input=False)
        jami_total = create_column(statement_husbandry, jami_chorva, "Jami bosh soni", "Общее количество голов",
                                   "3.1.14.1", is_user_input=False)
        create_column(statement_husbandry, jami_total, "Reja", "План", "3.1.14.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK, is_user_input=False)
        create_column(statement_husbandry, jami_total, "Amalda", "Факт", "3.1.14.1.2", is_user_input=False)
        sovliq_total = create_column(statement_husbandry, jami_chorva, "Shundan: sovliqlar", "Из них: овцематки",
                                     "3.1.14.2", is_user_input=False)
        create_column(statement_husbandry, sovliq_total, "Amalda", "Факт", "3.1.14.2.1", is_user_input=False)

        # ========== Parrandachilik ilovasi ==========
        parranda_app = create_column(statement_husbandry, None, "Parrandachilik ilovasi", "Приложение: Птицеводство",
                                     "4")
        parranda_title = create_column(
            statement_husbandry,
            parranda_app,
            f"Agentlik tizimidagi o‘rmon xo‘jaliklarida {current_year} yilda parrandachilik bo‘yicha MA’LUMOT",
            f"Информация о птицеводстве в лесных хозяйствах системы агентства в {current_year} году",
            "4.1"
        )

        create_column(statement_husbandry, parranda_title, "Tashkilot nomi", "Наименование хозяйства", "4.1.1",
                      is_organization=True)

        year_parranda = create_column(statement_husbandry, parranda_title, f"{date_str} yil holatiga mavjud", # last month
                                      f"Состояние на {date_str}", "4.1.2")
        jami_parranda = create_column(statement_husbandry, year_parranda, "Jami parranda", "Общее количество птицы",
                                      "4.1.2.1")
        create_column(statement_husbandry, jami_parranda, "Amalda", "Факт", "4.1.2.1.1",
                      is_user_input=False)
        shundan_parranda = create_column(statement_husbandry, year_parranda, "Shundan", "Из них", "4.1.2.2")
        create_column(statement_husbandry, shundan_parranda, "Kurka soni", "Количество индеек", "4.1.2.2.1")
        create_column(statement_husbandry, shundan_parranda, "Jami tovuq va xo‘roz soni",
                      "Общее количество кур и петухов", "4.1.2.2.2")
        create_column(statement_husbandry, shundan_parranda, "Tuxum beradigan tovuq soni", "Количество несушек",
                      "4.1.2.2.3")

        new_tashkil_column = create_column(statement_husbandry, parranda_title, "Jami chiqim",
                                           "Общий расход", "4.1.3")
        first_kurka = create_column(statement_husbandry, new_tashkil_column, "Kurka", "Индейка", "4.1.3.1")
        create_column(statement_husbandry, first_kurka, "Amalda", "Факт", "4.1.3.1.1")
        first_chicken = create_column(statement_husbandry, new_tashkil_column, "Tovuq", "Курица", "4.1.3.2")
        create_column(statement_husbandry, first_chicken, "Amalda", "Факт", "4.1.3.2.1")

        create_column(statement_husbandry, parranda_title, "Jami chiqim, bosh", "Общий расход, голов",
                      "4.1.4", is_user_input=False)

        hojalik_parranda = create_column(statement_husbandry, parranda_title,
                                         f"Xo‘jaliklar tomonidan tashkil etildi {date_str} yil holatiga",
                                         f"Создано со стороны хозяйств по состоянию на {date_str}", "4.1.5")
        total_hojalik = create_column(statement_husbandry, hojalik_parranda, "Jami parranda", "Общее количество птицы",
                                      "4.1.5.1")
        create_column(statement_husbandry, total_hojalik, "Reja", "План", "4.1.5.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_hojalik, "Amalda", "Факт", "4.1.5.1.2", is_user_input=False)
        shundan_hojalik = create_column(statement_husbandry, hojalik_parranda, "Shundan", "Из них", "4.1.5.2")
        create_column(statement_husbandry, shundan_hojalik, "Kurka soni", "Количество индеек", "4.1.5.2.1")
        create_column(statement_husbandry, shundan_hojalik, "Jami tovuq va xo‘roz soni",
                      "Общее количество кур и петухов", "4.1.5.2.2")
        create_column(statement_husbandry, shundan_hojalik, "Tuxum beradigan tovuq soni", "Количество несушек",
                      "4.1.5.2.3")

        sektor_parranda = create_column(statement_husbandry, parranda_title,
                                        f"Xususiy sektor tomonidan tashkil etildi {date_str} yil holatiga",
                                        f"Создано со стороны частного сектора по состоянию на {date_str}", "4.1.6")
        total_sektor = create_column(statement_husbandry, sektor_parranda, "Jami parranda", "Общее количество птицы",
                                     "4.1.6.1")
        create_column(statement_husbandry, total_sektor, "Reja", "План", "4.1.6.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_sektor, "Amalda", "Факт", "4.1.6.1.2", is_user_input=False)
        shundan_sektor = create_column(statement_husbandry, sektor_parranda, "Shundan", "Из них", "4.1.6.2")
        create_column(statement_husbandry, shundan_sektor, "Kurka soni", "Количество индеек", "4.1.6.2.1")
        create_column(statement_husbandry, shundan_sektor, "Jami tovuq va xo‘roz soni",
                      "Общее количество кур и петухов", "4.1.6.2.2")
        create_column(statement_husbandry, shundan_sektor, "Tuxum beradigan tovuq soni", "Количество несушек",
                      "4.1.6.2.3")

        jami_parranda = create_column(statement_husbandry, parranda_title,
                                      f"Jami tashkil etilgan parranda {date_str} yil holatiga",
                                      f"Общее количество созданной птицы по состоянию на {date_str}", "4.1.7")
        total_jami = create_column(statement_husbandry, jami_parranda, "Jami parranda", "Общее количество птицы",
                                   "4.1.7.1")
        create_column(statement_husbandry, total_jami, "Reja", "План", "4.1.7.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK, is_user_input=False)
        create_column(statement_husbandry, total_jami, "Amalda", "Факт", "4.1.7.1.2", is_user_input=False)
        shundan_jami = create_column(statement_husbandry, jami_parranda, "Shundan", "Из них", "4.1.7.2")
        create_column(statement_husbandry, shundan_jami, "Kurka soni", "Количество индеек", "4.1.7.2.1",
                      is_user_input=False)
        create_column(statement_husbandry, shundan_jami, "Jami tovuq va xo‘roz soni", "Общее количество кур и петухов",
                      "4.1.7.2.2", is_user_input=False)
        create_column(statement_husbandry, shundan_jami, "Tuxum beradigan tovuq soni", "Количество несушек",
                      "4.1.7.2.3", is_user_input=False)

        # ========== Asalarichilik ilovasi ==========
        bees_app = create_column(statement_husbandry, None, "Asalarichilik ilovasi", "Приложение: Пчеловодство", "5")
        bees_title = create_column(
            statement_husbandry,
            bees_app,
            f"Agentlik tizimidagi o‘rmon xo‘jaliklarida {current_year} yilda asalarichilik bo‘yicha MA’LUMOT",
            f"Информация о пчеловодстве в лесных хозяйствах системы агентства в {current_year} году",
            "5.1"
        )

        create_column(statement_husbandry, bees_title, "Tashkilot nomi", "Наименование хозяйства", "5.1.1",
                      is_organization=True)
        create_column(statement_husbandry, bees_title, f"{date_str} yil holatiga mavjud asalari oilasi soni",
                      f"Состояние на {date_str} — количество пчелиных семей", "5.1.2")

        asal_kg = create_column(statement_husbandry, bees_title, "Asal ishlab chiqarish, kg", "Производство меда, кг",
                                "5.1.3")
        create_column(statement_husbandry, asal_kg, "Amalda", "Факт", "5.1.3.2")

        tovar_asal = create_column(statement_husbandry, bees_title, "Shundan: tovar asal ishlab chiqarish, kg",
                                   "Из них: товарный мед, кг", "5.1.4")
        create_column(statement_husbandry, tovar_asal, "Amalda", "Факт", "5.1.4.2")

        hoz_bee = create_column(statement_husbandry, bees_title,
                                f"{date_str} yil holatiga xo‘jalik tomonidan asalari oilasi tashkil etish",
                                f"Создание пчелиных семей со стороны хозяйств по состоянию на {date_str}", "5.1.6")
        create_column(statement_husbandry, hoz_bee, "Reja", "План", "5.1.6.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, hoz_bee, "Amalda", "Факт", "5.1.6.2")

        sektor_bee = create_column(statement_husbandry, bees_title,
                                   f"{date_str} yil holatiga xususiy sektor tomonidan asalari oilasi tashkil etish",
                                   f"Создание пчелиных семей со стороны частного сектора по состоянию на {date_str}",
                                   "5.1.7")
        create_column(statement_husbandry, sektor_bee, "Reja", "План", "5.1.7.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, sektor_bee, "Amalda", "Факт", "5.1.7.2")

        total_bee = create_column(statement_husbandry, bees_title,
                                  f"{date_str} yil holatiga jami tashkil etilgan asalari oilasi soni",
                                  f"Общее количество созданных пчелиных семей по состоянию на {date_str}", "5.1.8")
        create_column(statement_husbandry, total_bee, "Reja", "План", "5.1.8.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_bee, "Amalda", "Факт", "5.1.8.2",
                      is_user_input=False)

        # ========== Baliqchilik ilovasi ==========
        fish_app = create_column(statement_husbandry, None, "Baliqchilik ilovasi", "Приложение: Рыбоводство", "6")
        fish_title = create_column(
            statement_husbandry,
            fish_app,
            f"O‘rmon xo‘jaligi agentligi huzuridagi xo‘jaliklardagi {current_year} yilda baliq mahsulotlarini yetishtirilishi bo‘yicha MA’LUMOT",
            f"Информация о производстве рыбной продукции в хозяйствах при агентстве лесного хозяйства в {current_year} году",
            "6.1"
        )

        create_column(statement_husbandry, fish_title, "Tashkilot nomi", "Наименование хозяйства", "6.1.1",
                      is_organization=True)
        create_column(statement_husbandry, fish_title, "Jami baliq ko‘llari maydoni (ga)",
                      "Общая площадь рыбных прудов (га)", "6.1.2", is_user_input=False)
        create_column(statement_husbandry, fish_title, "Jami yetishtirilgan mahsulot (tn)",
                      "Общий объем произведенной продукции (тн)", "6.1.3", is_user_input=False)

        wundan = create_column(statement_husbandry, fish_title, "Shundan", "Из них", "6.1.4")
        create_column(statement_husbandry, wundan, "Xo‘jalik balansidagi baliq ko‘llari maydoni (ga)",
                      "Площадь прудов на балансе хозяйства (га)", "6.1.5")
        create_column(statement_husbandry, wundan, "Yetishtirilgan mahsulot (tn)", "Произведенная продукция (тн)",
                      "6.1.6")
        create_column(statement_husbandry, wundan, "Ijarachilar hisobidagi baliq ko‘llari maydoni (ga)",
                      "Площадь прудов в аренде (га)", "6.1.7")
        create_column(statement_husbandry, wundan, "Yetishtirilgan mahsulot (tn)", "Произведенная продукция (тн)",
                      "6.1.8")

        # ========== Dorivor ilovasi ==========
        medicine_app = create_column(statement_medicine, None, "Dorivor ilovasi", "Применение препарата", "1")
        medicine_title = create_column(
            statement_medicine,
            medicine_app,
            "O'rmon fondi yerlarida dorivor va oziq-ovqatbop o'simliklar xom ashyosi yetishtirish to'g'risida Ma'lumot",
            "Сведения о выращивании лекарственного и пищевого растительного сырья на землях лесного фонда",
            "1.1"
        )
        create_column(statement_medicine, medicine_title, "Tashkilot nomi", "Наименование хозяйства", "1.1.1",
                      is_organization=True)

        plantatsiya = create_column(statement_medicine, medicine_title, "Plantatsiya barpo etish, ga",
                                    "Создание плантаций, га", "1.1.2")
        create_column(statement_medicine, plantatsiya, "Reja", "План",
                      "1.1.2.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_medicine, plantatsiya, "Amalda", "Факт", "1.1.2.2")

        xomashyo = create_column(statement_medicine, medicine_title, "Xomashyosini tayyorlash, tn",
                                 "Подготовка сырья, тн", "1.1.3")
        create_column(statement_medicine, xomashyo, "Reja", "План", "1.1.3.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_medicine, xomashyo, "Amalda", "Факт", "1.1.3.2")

        # ======================  SVOD APPS AUTOMATE GENERATION REPORTS  last ===============================

        first_app = create_column(statement_husbandry, None, "Svod Chorva",
                                  "Сводная Животноводство", "7")
        first_title = create_column(
            statement_husbandry,
            first_app,
            f"Agentlik tizimidagi o‘rmon xo‘jaliklarida"
            f" {current_year}-yilda Chorvachilikni  rivojlantirish to‘g‘risida ma’lumot",
            f"Информация о развитии животноводства в лесных хозяйствах системы Агентства в {current_year} году",
            "7.1"
        )
        create_column(statement_husbandry, first_title, "Tashkilot nomi", "Наименование хозяйства",
                      "7.1.1", is_organization=True)
        create_column(statement_husbandry, first_title, "Reja", "План", "7.1.2",
                      is_user_input=False)
        create_column(statement_husbandry, first_title, f"01.01.{current_year}-yil holatiga", # last
                      "По состоянию на 01.01.2025", "7.1.3", is_user_input=False)
        create_column(statement_husbandry, first_title, f"01.{date_str} yil holatiga mavjud", # -> last with month
                      f"Имеется по состоянию на 01.{date_str} г.", "7.1.4", is_user_input=False)
        create_column(statement_husbandry, first_title, "Farqi", "разница", "7.1.5", is_user_input=False)
        create_column(statement_husbandry, first_title, "%", "%", "7.1.6", is_user_input=False)
        from_this_2 = create_column(statement_husbandry, first_title, "Shundan", "из этого",
                                    "7.1.7", is_user_input=False)
        create_column(statement_husbandry, from_this_2, "Yirik shoxli jami", "Всего крупнорогих",
                      "7.1.7.1", is_user_input=False)
        create_column(statement_husbandry, from_this_2, "shundan, buzoq", "отсюда, телёнок",
                      "7.1.7.2", is_user_input=False)
        create_column(statement_husbandry, from_this_2, "ot", "лошадь", "7.1.7.3", is_user_input=False)
        create_column(statement_husbandry, from_this_2, "shundan, toy-qulun", "шундан, той-қулун",
                      "7.1.7.4", is_user_input=False)
        create_column(statement_husbandry, from_this_2, "mayda, shoxli jami",
                      "Совокупность мелкороговых", "7.1.7.5", is_user_input=False)
        create_column(statement_husbandry, from_this_2, "shundan qo`zi uloq",
                      "из них ягнёнок, козлёнок", "7.1.7.6", is_user_input=False)


        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Chorvachilik hisobi' Statement and Columns."))
        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Dorivor hisobi' Statement and Columns."))
