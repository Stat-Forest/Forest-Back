from django.core.management.base import BaseCommand
from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices


def create_column(statement, parent, title_uz, title_ru, ordering, is_organization=False, status_plan=None, is_user_input=True):
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


class Command(BaseCommand):
    help = "Create structure for 'Shakl 8-O‘X' report"

    def handle(self, *args, **options):
        # Parent statement
        forest_statement = Statement.objects.get(
            name_uz="O'rmon barpo qilish",
            name_ru="Создание леса",
            period=PeriodChoices.YILLIK
        )

        # ====================================== SHAKL -8

        # Creating Shakl 8-O'X Statement
        statement_form_8 = Statement.objects.create(
            parent=forest_statement,
            name_uz="Shakl 8-O'X",
            name_ru="Форма 8-Ох",
            period=PeriodChoices.YILLIK
        )

        # Top level
        ilova_form_8 = create_column(statement_form_8, None, "Shakl-8 ilovasi", "Приложение Форма-8", "1")

        form_title = create_column(
            statement_form_8,
            ilova_form_8,
            "O‘rmon xo‘jaligida niholxona va ko‘chatxonalarda kuzgi sanoq natijasida aniqlangan va yetishtirilgan nihol va ko‘chatlar to‘g‘risida ma’lumot",
            "Информация о всходах и саженцах, выявленных и выращенных в результате осеннего подсчета в питомниках",
            "1.1"
        )

        create_column(statement_form_8, form_title, "Tashkilot nomi", "Наименование организации",
                      "1.1.1", is_organization=True)

        # 2. Bir yoshlik nihollar
        one_year = create_column(statement_form_8, form_title, "Bir yoshli nihollar (qalamcha va urug'idan unib chiqqan)",
                                 "Однолетние саженцы (выращенные из черенков и семян)", "1.1.2")
        jami_form = create_column(statement_form_8, one_year, "jami (gektar)", "всего (га)", "1.1.2.1")
        create_column(statement_form_8, jami_form, "gektar", "гектар", "1.1.2.1.1")
        create_column(statement_form_8, jami_form, "ming dona", "тысяча штук", "1.1.2.1.2")
        create_column(statement_form_8, one_year, "shundan ekishga yaroqligi (ming dona)",
                      "из которых пригодность для посадки (тысячи штук)", "1.1.2.2")

        # 3. Ikki yoshlik va undan katta nihollar
        two_years = create_column(statement_form_8, form_title, "Ikki yoshli va undan katta nihollar",
                                  "Саженцы в возрасте двух лет и старше", "1.1.3")
        jami_form_2 = create_column(statement_form_8, two_years, "jami (gektar)", "всего (га)",
                                    "1.1.3.1")
        create_column(statement_form_8, jami_form_2, "gektar", "гектар", "1.1.3.1.1")
        create_column(statement_form_8, jami_form_2, "ming dona", "тысяча штук", "1.1.3.1.2")
        create_column(statement_form_8, two_years, "shundan ekishga yaroqligi (ming dona)",
                      "из которых пригодность для посадки (тысячи штук)", "1.1.3.2")

        # 4. Ko‘chatlar va ildiz olgan ko‘chatlar
        seedlings = create_column(statement_form_8, form_title, "Ko‘chatlar va ildiz olgan ko‘chatlar",
                                  "Саженцы и укоренившиеся черенки", "1.1.4")
        jami_form_3 = create_column(statement_form_8, seedlings, "jami (gektar)", "всего (га)",
                                    "1.1.4.1")
        create_column(statement_form_8, jami_form_3, "gektar", "гектар", "1.1.4.1.1")
        create_column(statement_form_8, jami_form_3, "ming dona", "тысяча штук", "1.1.4.1.2")
        create_column(statement_form_8, seedlings, "shundan ekishga yaroqligi (ming dona)",
                      "из которых пригодность для посадки (тысячи штук)", "1.1.4.2")

        # 5. Nobud bo‘lgan urug‘, nihol yoki kalamchalar
        dead = create_column(statement_form_8, form_title, "Nobud bo‘lgan urug‘, nihol yoki qalamchalar",
                             "Погибшие семена, всходы или черенки", "1.1.5")
        create_column(statement_form_8, dead, "Urug‘ (kg/ga)", "Семена (кг/га)", "1.1.5.1")
        create_column(statement_form_8, dead, "Kalamcha (ming dona/gektar)", "Черенки (тысячь шт/га)", "1.1.5.2")
        create_column(statement_form_8, dead, "Nihol (ming dona/gektar)", "Всходы (тысячь шт/га)", "1.1.5.3")

        # 6. Urug‘ yoki kalamcha o‘tkazilgan ochiq plantatsiyalar
        create_column(statement_form_8, form_title,
                              "Urug‘ yoki kalamcha olinadigon onalik plantatsiyalar maydon, gektar",
                              "Площадь материнских плантаций, с которых получают семена или рассаду, гектары",
                              "1.1.6")

        # ====================================== SHAKL -9

        statement_form_9 = Statement.objects.create(
            parent=forest_statement,
            name_uz="Shakl 9-O‘X",
            name_ru="Форма 9-Ох",
            period=PeriodChoices.YILLIK
        )

        # === Top Level
        ilova = create_column(statement_form_9, None, "Shakl-9 ilovasi", "Приложение Форма-9", "1")

        form_title = create_column(
            statement_form_9,
            ilova,
            "O‘rmon xo‘jaligi tomonidan barpo etilgan madaniy o‘rmonlarni joriy yilgi kuzgi inventarizatsiyadan keyingi holati va ko‘karuvchanligi to‘g‘risida ma’lumot",
            "Сведения о состоянии и приживаемости культурных лесов, созданных лесным хозяйством, после осенней инвентаризации текущего года",
            "1.1"
        )

        # === Columns
        create_column(statement_form_9, form_title, "Tashkilot nomi", "Наименование хозяйства",
                      "1.1.1", is_organization=True)

        create_column(statement_form_9, form_title, "Daraxt va butalar turlari", "Породы деревьев и кустарников",
                      "1.1.2")

        # Ekillgan maydon
        ekilgan = create_column(statement_form_9, form_title, "Ekilgan maydon, ga", "Посаженная площадь, га", "1.1.3")
        create_column(statement_form_9, ekilgan, "jami", "всего", "1.1.3.1")
        create_column(statement_form_9, ekilgan, "shundan: urug‘dan", "из них: семенами", "1.1.3.2")
        create_column(statement_form_9, ekilgan, "shundan: ko‘chatdan", "из них: саженцами", "1.1.3.3")

        # Kuzgi sanoq bo‘yicha
        sanoq = create_column(statement_form_9, form_title, "Kuzgi sanoq (inventarizatsiya) bo‘yicha, ga",
                              "Осенний подсчет (инвентаризация), га", "1.1.4")
        create_column(statement_form_9, sanoq, "jami", "всего", "1.1.4.1")
        create_column(statement_form_9, sanoq, "shundan: urug‘dan", "из них: семенами", "1.1.4.2")
        create_column(statement_form_9, sanoq, "shundan: ko‘chatdan", "из них: саженцами", "1.1.4.3")

        # Ko‘karuvchanligi
        madaniy_column = create_column(statement_form_9, form_title, "Madaniy o‘rmonlarning ko‘karuvchanligi",
                      "Приживаемость культурных лесов", "1.1.5")
        create_column(statement_form_9, madaniy_column, "gektarda", "в гектар", "1.1.5.1")
        create_column(statement_form_9, madaniy_column, "foizda", "в процентах", "1.1.5.2")

        # Nobud bo‘lgan
        death_plants = create_column(statement_form_9, form_title, "Nobud bo‘lgan maydon (gektar)", "Погибшая площадь (га)", "1.1.6")
        create_column(statement_form_9, death_plants, "gektar", "гектар", "1.1.6.1")

        # Xatoga ekish talab qilinadigan maydon
        error_plant = create_column(statement_form_9, form_title, "Xatoga ekish talab qilinadigan maydon (gektar)",
                      "Площадь, требующая пересадки (га)", "1.1.7")
        create_column(statement_form_9, error_plant, "gektar", "гектар", "1.1.7.1")

        # ====================================== SHAKL -10

        statement_form_10 = Statement.objects.create(
            parent=forest_statement,
            name_uz="Shakl 10-O‘X",
            name_ru="Форма 10-Ох",
            period=PeriodChoices.YILLIK
        )

        # === Top level
        ilova_10 = create_column(
            statement_form_10,
            None,
            "Shakl-10 ilovasi",
            "Приложение Форма-10",
            "1"
        )

        form_title_10 = create_column(
            statement_form_10,
            ilova_10,
            "O‘rmon barpo qilish, o‘rmonlarni kuzgi inventarizatsiyadan o‘tkazish to‘g‘risida ma’lumot",
            "Сведения о создании лесов и проведении осенней инвентаризации лесов",
            "1.1"
        )

        # === Columns

        # 1. Tashkilot
        create_column(
            statement_form_10,
            form_title_10,
            "Tashkilot nomi",
            "Наименование организации",
            "1.1.1",
            is_organization=True
        )

        # 3. Barpo etilgan madaniy o‘rmonlar maydoni
        create_column(
            statement_form_10,
            form_title_10,
            "Barpo etilgan madaniy o‘rmonlar maydoni",
            "Площадь созданных культурных лесов",
            "1.1.2"
        )

        # 4. Davlat o‘rmon fondiga qabul qilingan maydon
        create_column(
            statement_form_10,
            form_title_10,
            "Davlat o‘rmon fondiga qabul qilingan maydon",
            "Площадь, принятая в государственный лесной фонд",
            "1.1.3"
        )

        # 5. Davlat o‘rmon fondidan chiqarilgan maydon
        create_column(
            statement_form_10,
            form_title_10,
            "Davlat o‘rmon fondidan chiqarilgan maydon",
            "Площадь, исключённая из государственного лесного фонда",
            "1.1.4"
        )

        # 6. Kapital qo‘yilma hisobidan barpo etilgan bog‘ va uzumzorlar
        create_column(
            statement_form_10,
            form_title_10,
            "Kapital qo‘yilma hisobidan barpo etilgan bog‘ va uzumzorlar maydoni",
            "Площадь садов и виноградников, созданных за счёт капитальных вложений",
            "1.1.5"
        )

        # 7. O‘rmon bilan qoplangan maydon (inventarizatsiya)
        covered_area = create_column(
            statement_form_10,
            form_title_10,
            "O‘rmon bilan qoplangan maydonga o'tkazilgan maydon",
            "Площадь, перенесённая на лесистую площадь",
            "1.1.6"
        )

        create_column(
            statement_form_10,
            covered_area,
            "jami",
            "всего",
            "1.1.6.1"
        )

        create_column(
            statement_form_10,
            covered_area,
            "shundan joriy yilda",
            "из них в текущем году",
            "1.1.6.2"
        )

        # 8. Hisobdan chiqarilgan madaniy o‘rmonlar
        create_column(
            statement_form_10,
            form_title_10,
            "Hisobdan chiqarilgan madaniy o‘rmonlar maydoni",
            "Площадь культурных лесов, исключённых из учета",
            "1.1.7"
        )

        # 9. Buyruqqa asosan kesilgan maydon
        create_column(
            statement_form_10,
            form_title_10,
            "Buyruqqa asosan kesilgan maydon",
            "Площадь, вырубленная по приказу",
            "1.1.8"
        )

        # 10. Inventarizatsiyadan o‘tmagan o‘rmonlar
        not_inventory = create_column(
            statement_form_10,
            form_title_10,
            "O‘rmon bilan qoplangan maydonga o‘tkazilmagan yosh madaniy o‘rmonlar maydoni",
            "Площадь молодых культурных лесов, не переведенная на площадь, покрытую лесом",
            "1.1.9"
        )

        create_column(
            statement_form_10,
            not_inventory,
            "jami",
            "всего",
            "1.1.9.1"
        )

        create_column(
            statement_form_10,
            not_inventory,
            "shu jumladan muddati o‘tgan yoki nobud bo‘lgan",
            "в том числе с истекшим сроком или погибшие",
            "1.1.9.2"
        )

        # ====================================== SHAKL -11

        statement_form_11 = Statement.objects.create(
            parent=forest_statement,
            name_uz="Shakl 11-O‘X",
            name_ru="Форма 11-Ох",
            period=PeriodChoices.YILLIK
        )

        # === Top level
        ilova_11 = create_column(
            statement_form_11,
            None,
            "Shakl-11 ilovasi",
            "Приложение Форма-11",
            "1"
        )

        form_title_11 = create_column(
            statement_form_11,
            ilova_11,
            "O‘rmon erlarida tabiiy tiklanishga ko‘maklashish tadbirlari o‘tkazilganligi "
            "va joriy yil kuzgi inventarizatsiyada aniqlangan maydonlar to‘g‘risida ma’lumot",
            "Сведения о проведении мероприятий по содействию естественному возобновлению "
            "на лесных землях и площадях, выявленных осенней инвентаризацией текущего года",
            "1.1"
        )

        # === Columns

        # 1. Tashkilot
        create_column(
            statement_form_11,
            form_title_11,
            "Tashkilot nomi",
            "Наименование организации",
            "1.1.1",
            is_organization=True
        )

        # 3. Tabiiy tiklanishga ko‘maklashish tadbiri o‘tkazilgan maydon
        create_column(
            statement_form_11,
            form_title_11,
            "Tabiiy tiklanishga ko‘maklashish tadbiri o‘tkazilgan maydon (gektar)",
            "Площадь проведения мероприятий по содействию естественному возобновлению (га)",
            "1.1.2"
        )

        # === Shu jumladan block
        shu_jumladan = create_column(
            statement_form_11,
            form_title_11,
            "Shu jumladan",
            "В том числе",
            "1.1.3"
        )

        # 4.1 Asosiy daraxt turi
        asosiy_daraxt = create_column(
            statement_form_11,
            shu_jumladan,
            "Asosiy daraxt turi",
            "Основная древесная порода",
            "1.1.3.1"
        )

        create_column(
            statement_form_11,
            asosiy_daraxt,
            "jami maydon",
            "общая площадь",
            "1.1.3.1.1"
        )

        create_column(
            statement_form_11,
            asosiy_daraxt,
            "shundan ignabarglilar",
            "в том числе хвойные",
            "1.1.3.1.2"
        )

        # 4.2 Tabiiy tiklanish holati
        create_column(
            statement_form_11,
            shu_jumladan,
            "Tabiiy tiklanish holati (yaxshi, qoniqarli, qoniqarsiz)",
            "Состояние естественного возобновления (хорошее, удовлетворительное, неудовлетворительное)",
            "1.1.3.2"
        )

        # 5. O‘rmon barpo etish yoki qayta tiklashga kiritilgan maydon
        create_column(
            statement_form_11,
            form_title_11,
            "O‘rmon barpo etish yoki qayta tiklash hajmiga kiritildi, (gektar)",
            "Площадь, включенная в лесовосстановление или лесоразведение (га)",
            "1.1.3.3"
        )

        self.stdout.write(self.style.SUCCESS("✅ Shakl 11-O‘X structure created successfully."))
        self.stdout.write(self.style.SUCCESS("✅ Shakl 10-O‘X structure created successfully."))
        self.stdout.write(self.style.SUCCESS("✅ Shakl 9-O‘X structure created successfully."))
        self.stdout.write(self.style.SUCCESS("✅ Shakl 8-O‘X structure created successfully."))
