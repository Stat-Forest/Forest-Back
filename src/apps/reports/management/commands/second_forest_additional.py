from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn


class Command(BaseCommand):
    def handle(self, *args, **options):
        def create_column(statement, parent, title, ordering, is_organization=False):
            return StatementColumn.objects.create(
                statement=statement,
                parent=parent,
                title=title,
                ordering=ordering,
                is_organization=is_organization
            )

        forest_add = Statement.objects.get(name="O`rmonlardan qo`shimcha foydalanish")
        statement_mechanization = Statement.objects.create(parent=forest_add, name="Mexanizatsiya hisobi")

        # ========== NeftBaza ilovasi ==========
        neftbaza_ilova = create_column(statement_mechanization, None, "Neftbaza-ilovasi", "1")

        neftbaza_title = create_column(
            statement_mechanization,
            neftbaza_ilova,
            "Ўрмон хўжаликларида 2025 йил 1 январга қадар олинган ЁММ миқдори тўғрисида  маълумот",
            "1.1"
        )

        create_column(statement_mechanization, neftbaza_title, "Ташкилот номи", "1.1.1", is_organization=True)
        create_column(statement_mechanization, neftbaza_title, "Нефтбаза номи", "1.1.2")

        nakladnoy = create_column(statement_mechanization, neftbaza_title, "Накладной", "1.1.3")
        create_column(statement_mechanization, nakladnoy, "рақами", "1.1.3.1")
        create_column(statement_mechanization, nakladnoy, "санаси", "1.1.3.2")

        create_column(statement_mechanization, neftbaza_title, "Ёқилғи тури", "1.1.4")
        create_column(statement_mechanization, neftbaza_title, "Миқдори, кг", "1.1.5")
        create_column(statement_mechanization, neftbaza_title, "Суммаси, минг сўм", "1.1.6")
        create_column(statement_mechanization, neftbaza_title, "Молиялаш-тириш манбаи (бюджет/хўжалик ҳисоби)", "1.1.7")

        # ========== Avto ilovasi ==========
        avto_ilova = create_column(statement_mechanization, None, "Авто-ilovasi", "1")

        avto_title = create_column(
            statement_mechanization,
            avto_ilova,
            "Ўрмон хўжалигида мавжуд автомашиналар (01.01.25й. ҳолатига)  ва уларнинг ҳолати тўғрисида маълумотлар",
            "2.1"
        )

        create_column(statement_mechanization, avto_title, "Ташкилот номи", "1.1.1", is_organization=True)
        create_column(statement_mechanization, avto_title, "тури", "1.1.2")
        create_column(statement_mechanization, avto_title, "Русуми", "1.1.3")
        create_column(statement_mechanization, avto_title, "Давлат рақами белгиси", "1.1.4")
        create_column(statement_mechanization, avto_title, "Ишлаб чиқарилган йили", "1.1.5")

        agregatlar = create_column(statement_mechanization, avto_title, "Агрегатлар рақами", "1.1.6")
        create_column(statement_mechanization, agregatlar, "завод (инвентар)", "1.1.6.1")
        create_column(statement_mechanization, agregatlar, "двигатель", "1.1.6.2")
        create_column(statement_mechanization, agregatlar, "кузов", "1.1.6.3")
        create_column(statement_mechanization, agregatlar, "шасси (рама)", "1.1.6.4")

        yonilgilar = create_column(statement_mechanization, avto_title, "Ёнилғи тури", "1.1.7")
        create_column(statement_mechanization, yonilgilar, "(Бензин, дизель ёнилғиси, сиқилган табиий газ ёки суюлтирилган газ)", "1.1.7.1")

        create_column(statement_mechanization, avto_title, "Техник ҳолати соз/носоз/яроқсиз", "1.1.8")
        create_column(statement_mechanization, avto_title, "Молия манбаси (хўжалик ёки бюджет)", "1.1.9")

        asosiy_qiymat = create_column(statement_mechanization, avto_title, "Асосий воситанинг қиймати (минг сўм ҳисобида)", "1.1.10")
        create_column(statement_mechanization, asosiy_qiymat, "Бошланғич қиймати", "1.1.10.1")
        create_column(statement_mechanization, asosiy_qiymat, "Эскириш қиймати", "1.1.10.2")
        create_column(statement_mechanization, asosiy_qiymat, "Қолдиқ қиймати", "1.1.10.3")

        # ========== K-X Texnikasi ilovasi ==========

        texnika_ilova = create_column(statement_mechanization, None, "К-Х техникаси", "1")
        texnika_title = create_column(
            statement_mechanization,
            texnika_ilova,
            "Ўрмон хўжалигида мавжуд узиюрар техникалар (01.01.25й. ҳолатига)"
            "  ва уларнинг ҳолати тўғрисида маълумотлар ", "1.1")

        create_column(statement_mechanization, texnika_title, "Ташкилот номи", "1.1.1", is_organization=True)
        create_column(statement_mechanization, texnika_title, "Техниканинг номи", "1.1.2")
        create_column(statement_mechanization, texnika_title, "Русуми", "1.1.3")
        create_column(statement_mechanization, texnika_title, "Давлат рақами белгиси", "1.1.4")
        create_column(statement_mechanization, texnika_title, "Ишлаб чиқарилган йили", "1.1.5")

        agregatlar_raqami = create_column(statement_mechanization, texnika_title, "Агрегатлар рақами", "1.1.6")
        create_column(statement_mechanization, agregatlar_raqami, "завод (инвентар) ", "1.1.6.1")
        create_column(statement_mechanization, agregatlar_raqami, "двигатель", "1.1.6.2")
        create_column(statement_mechanization, agregatlar_raqami, "кузов", "1.1.6.3")
        create_column(statement_mechanization, agregatlar_raqami, "шасси (рама)", "1.1.6.4")

        fire_type = create_column(statement_mechanization, texnika_title, "Ёнилғи тури", "1.1.7")
        create_column(statement_mechanization, fire_type, "(Бензин, дизель ёнилғиси, сиқилган табиий"
                                                          " газ ёки суюлтирилган газ)", "1.1.7.1")

        create_column(statement_mechanization, texnika_title, "Техник ҳолати соз/носоз/яроқсиз", "1.1.8")
        create_column(statement_mechanization, texnika_title, "Молия манбаси (хўжалик ёки бюджет)", "1.1.9")

        main_vosita = create_column(statement_mechanization, texnika_title, "Асосий воситанинг қиймати (минг сўм ҳисобида)", "1.1.10")
        create_column(statement_mechanization, main_vosita, "Бошланғич қиймати", "1.1.10.1")
        create_column(statement_mechanization, main_vosita, "Эскириш қиймати", "1.1.10.2")
        create_column(statement_mechanization, main_vosita, "Қолдиқ қиймати", "1.1.10.3")

        # ========== Agregatlari ilovasi ==========

        aggregate_app = create_column(statement_mechanization, None, "Agregatlari-ilovasi", "1")
        aggregate_title = create_column(
            statement_mechanization,
            aggregate_app,
            "Ўрмон хўжалигида мавжуд Кишлок хужалиги агрегатлари (01.01.25й. ҳолатига)"
            "  ва уларнинг ҳолати тўғрисида маълумотлар ", "1.1")
        create_column(statement_mechanization, aggregate_title, "Ташкилот номи", "1.1.1", is_organization=True)
        create_column(statement_mechanization, aggregate_title, "Техниканинг номи", "1.1.2")
        create_column(statement_mechanization, aggregate_title, "Русуми", "1.1.3")
        create_column(statement_mechanization, aggregate_title, "Ишлаб чиқарилган йили", "1.1.4")

        aggregate_numbers = create_column(statement_mechanization, aggregate_title, "Агрегатлар рақами", "1.1.5")
        create_column(statement_mechanization, aggregate_numbers, "завод (инвентар) ", "1.1.5.1")
        create_column(statement_mechanization, aggregate_numbers, "Тех. Хужжат раками", "1.1.5.2")

        create_column(statement_mechanization, aggregate_title, "Техник ҳолати соз/носоз /яроқсиз", "1.1.6")
        create_column(statement_mechanization, aggregate_title, "Молия манбаси (хўжалик ёки бюджет)", "1.1.7")
        main_tools = create_column(statement_mechanization, aggregate_title, "Асосий воситанинг қиймати (минг сўм ҳисобида)", "1.1.8")
        create_column(statement_mechanization, main_tools, "Бошланғич қиймати", "1.1.8.1")
        create_column(statement_mechanization, main_tools, "Эскириш қиймати", "1.1.8.2")
        create_column(statement_mechanization, main_tools, "Қолдиқ қиймати", "1.1.8.3")

        # ========== Yongin Avto ilovasi ==========
        fire_app = create_column(statement_mechanization, None, "Енгил авто", "1")
        fire_title = create_column(
            statement_mechanization,
            fire_app,
            "Ўрмон хўжалигида мавжуд енгил хизмат автомашиналарининг 01.01.25 йил ҳолатига маъулмот",
            "1.1"
        )
        create_column(statement_mechanization, fire_title, "Ташкилот номи", "1.1.1")
        create_column(statement_mechanization, fire_title, "Авттранспорт русуми", "1.1.2")
        create_column(statement_mechanization, fire_title, "Ишлаб чиқарилган йили", "1.1.3")
        create_column(statement_mechanization, fire_title, "Давлат рақам", "1.1.4")

        balance = create_column(statement_mechanization, fire_title, "Баланс қиймати (минг сўм)", "1.1.5")
        create_column(statement_mechanization, balance, "Бошлангич киймати", "1.1.5.1")
        create_column(statement_mechanization, balance, "Колдик киймати", "1.1.5.2")

        create_column(statement_mechanization, fire_title, "Авттранспорт ҳолати (соз ёки носоз)", "1.1.6")
        create_column(statement_mechanization, fire_title, "Босиб ўтган масофа (км)", "1.1.7")
        create_column(statement_mechanization, fire_title, "Бириктирилган бўлим ёки ходим (ф.и.о.)", "1.1.8")

        # ========== Yoqilg`i ilovasi ==========

        fire_limit_app = create_column(statement_mechanization, None, "Ёкилги лимит-ilovasi", "1")
        fire_limit_title = create_column(
            statement_mechanization,
            fire_limit_app,
            "Ўрмон хўжаликларида 2025 йилда Ёқилғи мойлаш материаллари сарфи тўғрисида маълумот",
            "1.1"
        )
        create_column(statement_mechanization, fire_limit_title, "Ташкилот номи", "1.1.1", is_organization=True)
        create_column(statement_mechanization, fire_limit_title, "хисобот даври", "1.1.2")

        smeta = create_column(statement_mechanization, fire_limit_title, "Смета бўйича тасдиқланган (минг сўм)", "1.1.3")
        create_column(statement_mechanization, smeta, "Бюджет ҳисобидан", "1.1.3.1")
        create_column(statement_mechanization, smeta, "Хўжалик ҳисобидан", "1.1.3.2")
        byudjet = create_column(statement_mechanization, fire_limit_title, "Бюджет ҳисобидан", "1.1.4")
        benzin = create_column(statement_mechanization, byudjet, "Бензин", "1.1.4.1")
        create_column(statement_mechanization, benzin, "тонна", "1.1.4.1.1")
        create_column(statement_mechanization, benzin, "сумма ", "1.1.4.1.2")
        dizel = create_column(statement_mechanization, byudjet, "Дизел", "1.1.4.2")
        create_column(statement_mechanization, dizel, "тонна", "1.1.4.2.1")
        create_column(statement_mechanization, dizel, "сумма ", "1.1.4.2.2")
        metan_gas = create_column(statement_mechanization, byudjet, "Метан газ", "1.1.4.3")
        create_column(statement_mechanization, metan_gas, "М3", "1.1.4.3.1")
        create_column(statement_mechanization, metan_gas, "сумма ", "1.1.4.3.2")
        propan_gas = create_column(statement_mechanization, byudjet, "Пропан газ", "1.1.4.4")
        create_column(statement_mechanization, propan_gas, "М3", "1.1.4.4.1")
        create_column(statement_mechanization, propan_gas, "сумма ", "1.1.4.4.2")

        xojalik = create_column(statement_mechanization, fire_limit_title, "Хўжалик ҳисобидан", "1.1.5")
        second_benzin = create_column(statement_mechanization, xojalik, "Бензин", "1.1.5.1")
        create_column(statement_mechanization, second_benzin, "тонна", "1.1.5.1.1")
        create_column(statement_mechanization, second_benzin, "сумма ", "1.1.5.1.2")
        second_dizel = create_column(statement_mechanization, byudjet, "Дизел", "1.1.5.2")
        create_column(statement_mechanization, second_dizel, "тонна", "1.1.5.2.1")
        create_column(statement_mechanization, second_dizel, "сумма ", "1.1.5.2.2")
        second_metan_gas = create_column(statement_mechanization, byudjet, "Метан газ", "1.1.5.3")
        create_column(statement_mechanization, second_metan_gas, "М3", "1.1.5.3.1")
        create_column(statement_mechanization, second_metan_gas, "сумма ", "1.1.5.3.2")
        second_propan_gas = create_column(statement_mechanization, byudjet, "Пропан газ", "1.1.5.4")
        create_column(statement_mechanization, second_propan_gas, "М3", "1.1.5.4.1")
        create_column(statement_mechanization, second_propan_gas, "сумма ", "1.1.5.4.2")

        # ========== Metallalom ilovasi ==========

        metal_app = create_column(statement_mechanization, None, "Металлолом", "1")
        metal_title = create_column(
            statement_mechanization,
            metal_app,
            "Ўрмон хўжалиги томонидан қора металл парчалари йиғиб топшириш бўйича маълумот",
            "3.1"
        )
        create_column(statement_mechanization, metal_title, "Ташкилот номи", "1.1.1", is_organization=True)

        for i in range(1, 5):
            chorak = create_column(statement_mechanization, metal_title, f"{i}-чорак", f"1.1.{i + 2}")
            create_column(statement_mechanization, chorak, "Амалда", f"1.1.{i + 2}.1")
            create_column(statement_mechanization, chorak, "%", f"1.1.{i + 2}.2")
            hujjat = create_column(statement_mechanization, chorak,
                                   "Металл парчалари топширилганлиги  тўғрисида ҳужжат", f"1.1.{i + 2}.3")
            create_column(statement_mechanization, hujjat, "Санаси", f"1.1.{i + 2}.3.1")
            create_column(statement_mechanization, hujjat, "Квит. рақами", f"1.1.{i + 2}.3.2")
            create_column(statement_mechanization, hujjat, "Миқдори, тонна", f"1.1.{i + 2}.3.3")

        # ========== Pichan ilovasi ==========

        pichan_statement = Statement.objects.create(parent=forest_add, name="Pichan o`rish")
        hay_app = create_column(statement_mechanization, None, "пичан ўриш", "1")
        hay_title = create_column(
            statement_mechanization,
            hay_app,
            "Ўрмон хўжалиги агентлиги тизимидаги хўжаликларда ўрмон фонди ерларида пичан ўриш учун берилган"
            " ер  ҳисоби  бўйича ________ йил ҳолатига МАЪЛУМОТ",
            "1.1"
        )
        create_column(pichan_statement, hay_title, "Ташкилот номи", "1.1.1", is_organization=True)
        create_column(pichan_statement, hay_title, "____ йил прогноз кўрсаткичлари, минг сўм (режа)", "1.1.2")
        create_column(pichan_statement, hay_title, "Жами пичан ўриш мумкин бўлган майдон (га)", "1.1.3")
        create_column(pichan_statement, hay_title, "Пичан ўриладиган яроқли майдон (га)", "1.1.4")
        create_column(pichan_statement, hay_title, "шундан, пичан ўриладиган майдон, (га)", "1.1.5")
        create_column(pichan_statement, hay_title, "Фойдаланувчилар сони, (дона)", "1.1.6")
        create_column(pichan_statement, hay_title, "Пичан ўриш учун келиб тушган аризалар сони", "1.1.7")
        create_column(pichan_statement, hay_title, "шундан пичан ўриш учун берилган рухсатнома суммаcи, (минг сўм) (амалда)", "1.1.8")
        create_column(pichan_statement, hay_title, "Тўланган сумма, (минг сўм)", "1.1.9")
        create_column(pichan_statement, hay_title, "Қолган қисми, минг сўм", "1.1.10")
        create_column(pichan_statement, hay_title, "Жамғармаларга ўтказилган маблағ, минг сўм", "1.1.11")

        # ========== Yaylov ilovasi ==========

        yaylov_statement = Statement.objects.create(parent=forest_add, name="Yaylov hisoboti")

        pasture_app = create_column(yaylov_statement, None, "Яйлов-ilovasi", "1")
        pasture_title = create_column(
            yaylov_statement,
            pasture_app,
            "Ўрмон хўжалиги агентлиги тизимидаги хўжаликларда ўрмон фонди яйлов ҳудудларига чорва молларини"
            " жойлаштириш бўйича ________ йил ҳолатига ",
            "1.1"
        )

        create_column(yaylov_statement, pasture_title, "Ташкилот номи", "1.1.1", is_organization=True)
        create_column(yaylov_statement, pasture_title, "_____йил прогноз кўрсаткичлари, минг сўм (режа)",
                      "1.1.2")
        create_column(yaylov_statement, pasture_title, "Жами Яйлов майдони га", "1.1.3")
        create_column(yaylov_statement, pasture_title, "Мол боқишга яроқли майдон, (га)", "1.1.4")
        create_column(yaylov_statement, pasture_title, "шундан, чорва моллари боқилаётган майдони, (га)",
                      "1.1.5")
        create_column(yaylov_statement, pasture_title, "Фойда-ланувчилар сони, (дона)", "1.1.6")
        create_column(yaylov_statement, pasture_title, "Яйловга жойлаштирилган чорва моллари жами сони, (бош)",
                      "1.1.7")

        chorva_turi = create_column(yaylov_statement, pasture_title,
                                    "Шундан чорва молларининг тури, сони, сўммаси, минг сўм", "1.1.8")
        create_column(yaylov_statement, chorva_turi, "Майда шохли моллар", "1.1.8.1")
        create_column(yaylov_statement, chorva_turi, "Эчкилар", "1.1.8.2")
        create_column(yaylov_statement, chorva_turi,
                      "Майда шохли моллар ва эчкилар учун тўланадиган сўм, минг сўм", "1.1.8.3")
        create_column(yaylov_statement, chorva_turi, "6 ойгача МШМ (қўзи улоқ)", "1.1.8.4")
        create_column(yaylov_statement, chorva_turi,
                      "6 ойгача бўлган қўзи - улоқ учун тўланадиган сўм, минг сўм", "1.1.8.5")
        create_column(yaylov_statement, chorva_turi, "Йирик шохли моллар", "1.1.8.6")
        create_column(yaylov_statement, chorva_turi, "Йилқилар, туялар", "1.1.8.7")
        create_column(yaylov_statement, chorva_turi, "Эшаклар", "1.1.8.8")
        create_column(yaylov_statement, chorva_turi,
                      "Йирик шохли моллар, йилқилар, туялар ва эшаклар учун тўланадиган сўммаси, минг сўм", "1.1.8.9")
        create_column(yaylov_statement, chorva_turi, "2 ёшгача ЙШМ", "1.1.8.10")
        create_column(yaylov_statement, chorva_turi, "2 ёшгача ЙШМлар учун тўланадиган сўммаси, минг сўм",
                      "1.1.8.11")

        create_column(yaylov_statement, pasture_title,
                      "Яйлов учун тузилган шартнома суммаси,  (минг сўм) (амалда)", "1.1.9")
        create_column(yaylov_statement, pasture_title, "Тўланган сумма,  (минг сўм)", "1.1.10")
        create_column(yaylov_statement, pasture_title, "Қолган қисми, минг сўм", "1.1.11")
        create_column(yaylov_statement, pasture_title, "Жамғармага ўтказилган маблағ, минг сўм", "1.1.12")

        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Mexanizatsiya hisobi' Statement and Columns."))
        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Pichan Urish hisobi' Statement and Columns."))
        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Yaylov hisobi' Statement and Columns."))