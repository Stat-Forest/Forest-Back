from django.core.management import BaseCommand

from apps.reports.models import StatementColumn, Statement


class Command(BaseCommand):
    def handle(self, *args, **options):
        def create_column(statement, parent, title, ordering, is_organization=False, status_plan=None):
            return StatementColumn.objects.create(
                statement=statement,
                parent=parent,
                title=title,
                ordering=ordering,
                is_organization=is_organization,
                status_plan=status_plan
            )

        forest_statement = Statement.objects.get(name="O`rmonlardan qo`shimcha foydalanish")
        statement_husbandry = Statement.objects.create(parent=forest_statement, name="Chorvachilik")

        # ========== Й.Щ.М ilovasi ==========

        y_sh_m_ilova = create_column(statement_husbandry, None, "Й.Щ.М-ilovasi", "1")

        y_sh_m_title = create_column(
            statement_husbandry,
            y_sh_m_ilova,
            "Агентлик тизимидаги ўрмон хўжаликларида 2025 йилда Йирик шоҳли молларни ривожлантириш бўйича МАЪЛУМОТ",
            "1.1"
        )

        create_column(statement_husbandry, y_sh_m_title, "Хужаликлар номи", "1.1.1", is_organization=True)
        year_moment = create_column(statement_husbandry, y_sh_m_title, "01.01.2025 йил холатига", "1.1.2")
        general_number = create_column(statement_husbandry, year_moment, "Жами бош сони", "1.1.2.1")
        create_column(statement_husbandry, general_number, "Амалда", "1.1.2.1.1")
        create_column(statement_husbandry, year_moment, "Шундан; сигирлар", "1.1.2.2")

        get_buzoq = create_column(statement_husbandry, y_sh_m_title, "2025 йилда бузоқ олиш", "1.1.3")
        create_column(statement_husbandry, get_buzoq, "Режа", "1.1.3.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, get_buzoq, "Амалда", "1.1.3.2")

        new_column = create_column(statement_husbandry, y_sh_m_title, "Янгидан ташкил қилиш, бош", "1.1.4")
        create_column(statement_husbandry, new_column, "Режа", "1.1.4.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, new_column, "Амалда", "1.1.4.2")

        meat_column = create_column(statement_husbandry, y_sh_m_title, "Гўштга сўйилди", "1.1.5")
        create_column(statement_husbandry, meat_column, "Бош сони", "1.1.5.1")
        create_column(statement_husbandry, meat_column, "ЦН", "1.1.5.2")

        create_column(statement_husbandry, y_sh_m_title, "сотилган", "1.1.6")
        create_column(statement_husbandry, y_sh_m_title, "талофат ва нобуд бўлган", "1.1.7")
        create_column(statement_husbandry, y_sh_m_title, "Жами чиқим, бош", "1.1.8")

        next_year_moment = create_column(statement_husbandry, y_sh_m_title, "01.04.25 йил холатига", "1.1.9")
        second_general_number = create_column(statement_husbandry, next_year_moment, "Жами бош сони", "1.1.9.1")
        create_column(statement_husbandry, second_general_number, "Режа", "1.1.9.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, second_general_number, "Амалда", "1.1.9.1.2")
        create_column(statement_husbandry, next_year_moment, "Шундан; сигирлар", "1.1.9.2")

        # ========== Yilqichilik ilovasi ==========

        yilqichilik_app = create_column(statement_husbandry, None, "Йилқичилик-ilovasi", "1")
        yilqichilik_title = create_column(
            statement_husbandry,
            yilqichilik_app,
            "Агентлик тизимидаги ўрмон хўжаликларида 2025 йилда Йилқичиликни ривожлантириш бўйича МАЪЛУМОТ",
            "1.1"
        )

        create_column(statement_husbandry, yilqichilik_title, "Хужаликлар номи", "1.1.1", is_organization=True)
        yil_start = create_column(statement_husbandry, yilqichilik_title, "01.01.2025 йил ҳолатига мавжуд", "1.1.2")
        start_general = create_column(statement_husbandry, yil_start, "Жами бош сони", "1.1.2.1")
        create_column(statement_husbandry, start_general, "Амалда", "1.1.2.1.1")
        create_column(statement_husbandry, yil_start, "шундан; Бийалар", "1.1.2.2")

        foal = create_column(statement_husbandry, yilqichilik_title, "2025 йилда қулун олиш", "1.1.3")
        create_column(statement_husbandry, foal, "Режа", "1.1.3.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, foal, "Амалда", "1.1.3.2")

        yangi = create_column(statement_husbandry, yilqichilik_title, "Янгидан ташкил қилиш", "1.1.4")
        create_column(statement_husbandry, yangi, "Режа", "1.1.4.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, yangi, "Амалда", "1.1.4.2")

        gosht = create_column(statement_husbandry, yilqichilik_title, "Гўштга сўйилди", "1.1.5")
        create_column(statement_husbandry, gosht, "Бош сони", "1.1.5.1")
        create_column(statement_husbandry, gosht, "ЦН", "1.1.5.2")

        create_column(statement_husbandry, yilqichilik_title, "сотилган", "1.1.6")
        create_column(statement_husbandry, yilqichilik_title, "талофат ва нобуд бўлган", "1.1.7")
        create_column(statement_husbandry, yilqichilik_title, "Жами чиқим, бош", "1.1.8")

        yil_end = create_column(statement_husbandry, yilqichilik_title, "01.04.25 йил ҳолатига мавжуд", "1.1.9")
        end_general = create_column(statement_husbandry, yil_end, "Жами бош сони", "1.1.9.1")
        create_column(statement_husbandry, end_general, "Режа", "1.1.9.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, end_general, "Амалда", "1.1.9.1.2")
        create_column(statement_husbandry, yil_end, "шундан; Бийалар", "1.1.9.2")

        # ========== М.Ш.М. ilovasi ==========

        m_sh_m_app = create_column(statement_husbandry, None, "М.Ш.М-ilovasi", "1")
        m_sh_m_title = create_column(
            statement_husbandry,
            m_sh_m_app,
            "Агентлик тизимидаги ўрмон хўжаликларида 2025 йилда Майда шоҳли молларни ривожлантириш бўйича МАЪЛУМОТ",
            "1"
        )

        create_column(statement_husbandry, m_sh_m_title, "Хужаликлар номи", "1.1.1", is_organization=True)

        start_block = create_column(statement_husbandry, m_sh_m_title, "01.01.2025 йил ҳолатига", "1.1.2")
        total_count_start = create_column(statement_husbandry, start_block, "Жами бош сони", "1.1.2.1")
        create_column(statement_husbandry, total_count_start, "Амалда", "1.1.2.1.1")
        sub_sovliq = create_column(statement_husbandry, start_block, "шундан Совлиқлар", "1.1.2.2")
        create_column(statement_husbandry, sub_sovliq, "Амалда", "1.1.2.2.1")

        kuzulok_block = create_column(statement_husbandry, m_sh_m_title, "2025 йилда қўзиқўлак олиш", "1.1.3")
        create_column(statement_husbandry, kuzulok_block, "Режа", "1.1.3.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, kuzulok_block, "Амалда", "1.1.3.2")

        tashkil_block = create_column(statement_husbandry, m_sh_m_title, "2025 йилда янгидан ташкил этиш, дона",
                                      "1.1.4")
        create_column(statement_husbandry, tashkil_block, "Режа", "1.1.4.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, tashkil_block, "Амалда", "1.1.4.2")

        gosht_block = create_column(statement_husbandry, m_sh_m_title, "Гўштга сўйилди", "1.1.5")
        create_column(statement_husbandry, gosht_block, "бош", "1.1.5.1")

        create_column(statement_husbandry, m_sh_m_title, "Гўшт ишлаб чиқариш (ЦН)", "1.1.6")
        create_column(statement_husbandry, m_sh_m_title, "ИССИҚ овқатга сўйиш", "1.1.7")
        create_column(statement_husbandry, m_sh_m_title, "Сотилган", "1.1.8")
        create_column(statement_husbandry, m_sh_m_title, "камомад", "1.1.9")
        create_column(statement_husbandry, m_sh_m_title, "талофат ва нобуд бўлган", "1.1.10")
        create_column(statement_husbandry, m_sh_m_title, "Жами чиқим, бош", "1.1.11")

        # Хўжаликлар томонидан _____ йил ҳолатига
        hojalik_block = create_column(statement_husbandry, m_sh_m_title, "Хўжаликлар томонидан _____ йил ҳолатига",
                                      "1.1.12")
        total_hojalik = create_column(statement_husbandry, hojalik_block, "Жами бош сони", "1.1.12.1")
        create_column(statement_husbandry, total_hojalik, "Режа", "1.1.12.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_hojalik, "Амалда", "1.1.12.1.2")
        sovliq_hojalik = create_column(statement_husbandry, hojalik_block, "шундан Совлиқлар", "1.1.12.2")
        create_column(statement_husbandry, sovliq_hojalik, "Амалда", "1.1.12.2.1")

        # Хусусий секторларни жалб қилган ҳолда _____ йил ҳолатига
        sektor_block = create_column(statement_husbandry, m_sh_m_title,
                                     "Хусусий секторларни жалб қилган ҳолда _____ йил ҳолатига", "1.1.13")
        total_sektor = create_column(statement_husbandry, sektor_block, "Жами бош сони", "1.1.13.1")
        create_column(statement_husbandry, total_sektor, "Режа", "1.1.13.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_sektor, "Амалда", "1.1.13.1.2")
        sovliq_sektor = create_column(statement_husbandry, sektor_block, "шундан Совлиқлар", "1.1.13.2")
        create_column(statement_husbandry, sovliq_sektor, "Амалда", "1.1.13.2.1")

        # Жами чорва ________ йил ҳолатига
        jami_chorva = create_column(statement_husbandry, m_sh_m_title, "Жами чорва ________ йил ҳолатига", "1.1.14")
        jami_total = create_column(statement_husbandry, jami_chorva, "Жами бош сони", "1.1.14.1")
        create_column(statement_husbandry, jami_total, "Режа", "1.1.14.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, jami_total, "Амалда", "1.1.14.1.2")
        sovliq_total = create_column(statement_husbandry, jami_chorva, "шундан Совлиқлар", "1.1.14.2")
        create_column(statement_husbandry, sovliq_total, "Амалда", "1.1.14.2.1")

        # ========== Парранда ilovasi ==========

        parranda_app = create_column(statement_husbandry, None, "Парранда-ilovasi", "1")
        parranda_title = create_column(
            statement_husbandry,
            parranda_app,
            "Агентлик тизимидаги ўрмон хўжаликларида 2025 йилда Паррандачилик бўйича МАЪЛУМОТ",
            "1.1"
        )

        create_column(statement_husbandry, parranda_title, "Хўжаликлари номи", "1.1.1", is_organization=True)

        year_parranda = create_column(statement_husbandry, parranda_title, "01.01.25 йил холатига мавжуд", "1.1.2")
        jami_parranda = create_column(statement_husbandry, year_parranda, "Жами парранда", "1.1.2.1")
        create_column(statement_husbandry, jami_parranda, "Амалда", "1.1.2.1.1")
        shundan_parranda = create_column(statement_husbandry, year_parranda, "шундан", "1.1.2.2")
        create_column(statement_husbandry, shundan_parranda, "Курка сони", "1.1.2.2.1")
        create_column(statement_husbandry, shundan_parranda, "Жами товуқ ва хўроз сони", "1.1.2.2.2")
        create_column(statement_husbandry, shundan_parranda, "Тухум берадиган товуқ сони", "1.1.2.2.3")

        # Янги ташкил этилади
        new_tashkil_column = create_column(statement_husbandry, parranda_title, "Янги ташкил этилади", "1.1.3")
        first_kurka = create_column(statement_husbandry, new_tashkil_column, "Курка", "1.1.3.1")
        create_column(statement_husbandry, first_kurka, "Режа", "1.1.3.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, first_kurka, "Амалда", "1.1.3.1.2")
        first_chicken = create_column(statement_husbandry, new_tashkil_column, "Товуқ", "1.1.3.2")
        create_column(statement_husbandry, first_chicken, "Режа", "1.1.3.2.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, first_chicken, "Амалда", "1.1.3.2.2")

        # Гўштга сўйилди (25%)
        meat_25 = create_column(statement_husbandry, parranda_title, "Гўштга сўйилди (25%)", "1.1.4")
        second_kurka = create_column(statement_husbandry, meat_25, "Курка", "1.1.4.1")
        create_column(statement_husbandry, second_kurka, "Режа", "1.1.4.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, second_kurka, "Амалда", "1.1.4.1.2")
        second_chicken = create_column(statement_husbandry, meat_25, "Товуқ", "1.1.4.2")
        create_column(statement_husbandry, second_chicken, "Режа", "1.1.4.2.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, second_chicken, "Амалда", "1.1.4.2.2")

        # Гўшт ишлаб чиқариш (кг)
        gosht_kg = create_column(
            statement_husbandry,
            parranda_title,
            "Гўшт ишлаб чиқариш товуқларда (1100 гр) 1,1 кг, куркаларда (2800 гр) 2,8 кг",
            "1.1.5"
        )
        kurka_kg = create_column(statement_husbandry, gosht_kg, "Курка", "1.1.5.1")
        create_column(statement_husbandry, kurka_kg, "Режа", "1.1.5.1.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, kurka_kg, "Амалда", "1.1.5.1.2")
        tovuq_kg = create_column(statement_husbandry, gosht_kg, "Товуқ", "1.1.5.2")
        create_column(statement_husbandry, tovuq_kg, "Режа", "1.1.5.2.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, tovuq_kg, "Амалда", "1.1.5.2.2")

        # Тухум ишлаб чиқариш
        egg_block = create_column(
            statement_husbandry,
            parranda_title,
            "Тухум ишлаб чиқариш (1 та товуқ 110 та тухум) минг дона",
            "1.1.6"
        )

        kurka_egg = create_column(statement_husbandry, egg_block, "Курка", "1.1.6.1")
        create_column(statement_husbandry, kurka_egg, "Режа", "1.1.6.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, kurka_egg, "Амалда", "1.1.6.1.2")

        tovuq_egg = create_column(statement_husbandry, egg_block, "Товуқ", "1.1.6.2")
        create_column(statement_husbandry, tovuq_egg, "Режа", "1.1.6.2.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, tovuq_egg, "Амалда", "1.1.6.2.2")

        # Жами чиқим
        create_column(statement_husbandry, parranda_title, "Жами чиқим, бош", "1.1.7")

        # Хўжаликлар томонидан ташкил этилди
        hojalik_parranda = create_column(statement_husbandry, parranda_title,
                                         "Хўжаликлар томонидан ташкил этилди 01.04.25 йил ҳолати", "1.1.8")
        total_hojalik = create_column(statement_husbandry, hojalik_parranda, "Жами парранда", "1.1.8.1")
        create_column(statement_husbandry, total_hojalik, "Режа", "1.1.8.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_hojalik, "Амалда", "1.1.8.1.2")
        shundan_hojalik = create_column(statement_husbandry, hojalik_parranda, "шундан", "1.1.8.2")
        create_column(statement_husbandry, shundan_hojalik, "Курка сони", "1.1.8.2.1")
        create_column(statement_husbandry, shundan_hojalik, "Жами товуқ ва хўроз сони", "1.1.8.2.2")
        create_column(statement_husbandry, shundan_hojalik, "Тухум берадиган товуқ сони", "1.1.8.2.3")

        # Хусусий сектор
        sektor_parranda = create_column(statement_husbandry, parranda_title,
                                        "Хусусий сектор томонидан ташкил этилди 01.04.25 йил ҳолати", "1.1.9")
        total_sektor = create_column(statement_husbandry, sektor_parranda, "Жами парранда", "1.1.9.1")
        create_column(statement_husbandry, total_sektor, "Режа", "1.1.9.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_sektor, "Амалда", "1.1.9.1.2")
        shundan_sektor = create_column(statement_husbandry, sektor_parranda, "шундан", "1.1.9.2")
        create_column(statement_husbandry, shundan_sektor, "Курка сони", "1.1.9.2.1")
        create_column(statement_husbandry, shundan_sektor, "Жами товуқ ва хўроз сони", "1.1.9.2.2")
        create_column(statement_husbandry, shundan_sektor, "Тухум берадиган товуқ сони", "1.1.9.2.3")

        # Жами ташкил этилган паррандалар
        jami_parranda = create_column(statement_husbandry, parranda_title,
                                      "Жами ташкил этилган паррандалар 01.04.25 йил ҳолати", "1.1.10")
        total_jami = create_column(statement_husbandry, jami_parranda, "Жами парранда", "1.1.10.1")
        create_column(statement_husbandry, total_jami, "Режа", "1.1.10.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_jami, "Амалда", "1.1.10.1.2")
        shundan_jami = create_column(statement_husbandry, jami_parranda, "шундан", "1.1.10.2")
        create_column(statement_husbandry, shundan_jami, "Курка сони", "1.1.10.2.1")
        create_column(statement_husbandry, shundan_jami, "Жами товуқ ва хўроз сони", "1.1.10.2.2")
        create_column(statement_husbandry, shundan_jami, "Тухум берадиган товуқ сони", "1.1.10.2.3")

        # ========== Асалари ilovasi ==========

        bees_app = create_column(statement_husbandry, None, "Асалари-ilovasi", "1")
        bees_title = create_column(
            statement_husbandry,
            bees_app,
            "Агентлик тизимидаги ўрмон хўжаликларида 2025 йилда Асаларичилик бўйича МАЪЛУМОТ",
            "1.1"
        )

        create_column(statement_husbandry, bees_title, "Хўжаликлар номи", "1.1.1", is_organization=True)

        create_column(statement_husbandry, bees_title, "01.01.25 йил ҳолатига мавжуд асалари оиласи сони ", "1.1.2")

        # Асал ишлаб чиқариш, кг
        asal_kg = create_column(statement_husbandry, bees_title, "Асал ишлаб чиқариш, кг", "1.1.3")
        create_column(statement_husbandry, asal_kg, "Режа", "1.1.3.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, asal_kg, "Амалда", "1.1.3.2")

        # Шундан, товар асал ишлаб чиқариш, кг
        tovar_asal = create_column(statement_husbandry, bees_title, "Шундан, товар асал ишлаб чиқариш, кг", "1.1.4")
        create_column(statement_husbandry, tovar_asal, "Режа", "1.1.4.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, tovar_asal, "Амалда", "1.1.4.2")

        # 2025 йилда янгидан асалари оиласи ташкил этиш
        new_bee_2025 = create_column(statement_husbandry, bees_title, "2025 йилда янгида асалари оиласи ташкил этиш",
                                     "1.1.5")
        create_column(statement_husbandry, new_bee_2025, "Режа", "1.1.5.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, new_bee_2025, "Амалда", "1.1.5.2")

        # 01.04.25 ҳолатига хўжалик томонидан асалари оиласи ташкил этиш
        hoz_bee = create_column(statement_husbandry, bees_title,
                                "01.04.25 йил ҳолатига хўжалик томонидан асалари оиласи ташкил этиш", "1.1.6")
        create_column(statement_husbandry, hoz_bee, "Режа", "1.1.6.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, hoz_bee, "Амалда", "1.1.6.2")

        # 01.04.25 ҳолатига Хусусий сектор томонидан асалари оиласи ташкил этиш
        sektor_bee = create_column(statement_husbandry, bees_title,
                                   "01.04.25 йил ҳолатига Хусусий сектор томонидан асалари оиласи ташкил этиш", "1.1.7")
        create_column(statement_husbandry, sektor_bee, "Режа", "1.1.7.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, sektor_bee, "Амалда", "1.1.7.2")

        # 01.04.25 ҳолатига жами ташкил этилган асалари оиласи сони
        total_bee = create_column(statement_husbandry, bees_title,
                                  "01.04.25 йил ҳолатига жами ташкил этилган асалари оиласи сони", "1.1.8")
        create_column(statement_husbandry, total_bee, "Режа", "1.1.8.1", status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(statement_husbandry, total_bee, "Амалда", "1.1.8.2")

        # ========== Балиқчилик ilovasi ==========

        fish_app = create_column(statement_husbandry, None, "Балиқчилик-ilovasi", "1")
        fish_title = create_column(
            statement_husbandry,
            fish_app,
            "Ўрмон хўжалиги агентлиги хузуридаги хўжаликлардаги 2025 йилда Балиқ махсулотларини етитиштирилиши бўйича маълумоти",
            "1.1"
        )

        create_column(statement_husbandry, fish_title, "Хўжаликлар номи", "1.1.1", is_organization=True)
        create_column(statement_husbandry, fish_title, "Жами балиқ кўллари майдони (га) ", "1.1.2")
        create_column(statement_husbandry, fish_title, "Жами етиштирилган махсулот (тн)", "1.1.3")

        wundan = create_column(statement_husbandry, fish_title, "Шундан", "1.1.4")
        create_column(statement_husbandry, wundan, "Хўжалик балансидаги балиқ кўллари майдони (га)", "1.1.5")
        create_column(statement_husbandry, wundan, "Етиштирилган махсулот (тн)", "1.1.6")
        create_column(statement_husbandry, wundan, "Ижарачилар ҳисобидаги балиқ кўллар майдони (га)", "1.1.7")
        create_column(statement_husbandry, wundan, "Етиштирилган махсулот (тн)", "1.1.8")

        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Chorvachilik hisobi' Statement and Columns."))
