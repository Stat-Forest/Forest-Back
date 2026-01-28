from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn


class Command(BaseCommand):
    def handle(self, *args, **options):
        def create_column(statement, parent, title_uz, title_ru, ordering,
                          is_organization=False, status_plan=None, is_user_input=False):
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

        main_information_statement, _ = Statement.objects.get_or_create(
            name_uz="Axborot-tahlil, ijro intizomi",
            defaults={
                "name_ru": "Информационно-аналитическая, управленческая дисциплина",
            }
        )
        forest_area_statement = Statement.objects.create(
            parent=main_information_statement,
            name_uz="O'rmonlar kesimida",
            name_ru="В лесном отделе",
        )

        # =============== O'rmonlar kesimida ==================
        information_forest_app = create_column(forest_area_statement, None, "O'rmonlar kesimida ilovasi",
                                               "Приложение к разделу о лесах", "1")
        information_forest_title = create_column(
            forest_area_statement,
            information_forest_app,
            "O‘rmon agentligiga yuklatilgan muhim vazifalar ijrosi to‘g‘isida MA’LUMOT",
            "Об исполнении важных задач, возложенных на Агентство лесного хозяйства СВЕДЕНИЯ", "1.1")

        create_column(forest_area_statement, information_forest_title, "Hududlar va o‘rmon xo‘jaliklari nomi",
                      "Наименование территорий и лесных хозяйств", "1.1.1", is_organization=True)
        create_column(forest_area_statement, information_forest_title,
                      "O‘rmon bilan qoplangan yer maydonlari (mln ga)",
                      "Площади земель, покрытые лесом (млн га)", "1.1.2")
        forest_land = create_column(
            forest_area_statement,
            information_forest_title,
            "O‘rmon yerlarini o‘zlashtirib, foydalanishga kiritish (ga)",
        "Освоение и введение в пользование лесных земель (га)",
        "1.1.3")
        create_column(forest_area_statement, forest_land, "Reja", "План", "1.1.3.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)

        create_column(forest_area_statement, forest_land,"Amalda","Факт","1.1.3.2",)
        create_column(forest_area_statement, forest_land, "%", "%", "1.1.3.3",
            is_user_input=False,
        )
        create_column(forest_area_statement, forest_land,"(+,-)","(+,-)","1.1.3.4",
        )

        forest_land_2 = create_column(
            forest_area_statement,
            information_forest_title,
            "O‘rmonlar (yashil qoplamalar) barpo etish va qayta tiklash (ga)",
        "Создание и восстановление лесов (зеленых насаждений) (га)", "1.1.4")
        create_column(forest_area_statement, forest_land_2, "Reja", "План", "1.1.4.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)

        create_column(forest_area_statement, forest_land_2, "Amalda", "Факт", "1.1.4.2")
        create_column(forest_area_statement, forest_land_2, "%", "%", "1.1.4.3")
        create_column(forest_area_statement, forest_land_2, "(+,-)", "(+,-)", "1.1.4.4")

        forest_land_3 = create_column(
            forest_area_statement,
            information_forest_title,
            "Orolbo‘yi mintaqasi va boshqa cho‘l hududlarida yashil qoplama barpo etish. (ming ga)",
            "Создание зеленого покрова в Приаралье и других пустынных районах. (тыс. га)",
            "1.1.5"
        )
        create_column(forest_area_statement, forest_land_3, "Reja", "План", "1.1.5.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)

        create_column(forest_area_statement, forest_land_3, "Amalda", "Факт", "1.1.5.2")
        create_column(forest_area_statement, forest_land_3, "%", "%", "1.1.5.3")
        create_column(forest_area_statement, forest_land_3, "(+,-)", "(+,-)", "1.1.5.4")

        forest_land_4 = create_column(
            forest_area_statement,
            information_forest_title,
            "Orol dengizining qurigan tubida yashil qoplamalar barpo etish. (ga)",
            "Создание зеленых насаждений на высохшем дне Аральского моря. (га)",
            "1.1.6"
        )
        create_column(forest_area_statement, forest_land_4, "Reja", "План", "1.1.6.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)

        create_column(forest_area_statement, forest_land_4, "Amalda", "Факт", "1.1.6.2")
        create_column(forest_area_statement, forest_land_4, "%", "%", "1.1.6.3")
        create_column(forest_area_statement, forest_land_4, "(+,-)", "(+,-)", "1.1.6.4")

        forest_land_5 = create_column(
            forest_area_statement,
            information_forest_title,
            "Himoya o‘rmonzorlarini (ihota) barpo etish (ga)",
            "Создание защитных лесных насаждений (га)",
            "1.1.7"
        )
        create_column(forest_area_statement, forest_land_5, "Reja", "План", "1.1.7.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)

        create_column(forest_area_statement, forest_land_5, "Amalda", "Факт", "1.1.7.2")
        create_column(forest_area_statement, forest_land_5, "%", "%", "1.1.7.3")
        create_column(forest_area_statement, forest_land_5, "(+,-)", "(+,-)", "1.1.7.4")

        forest_land_6 = create_column(
            forest_area_statement,
            information_forest_title,
            "Terassa uslubida o‘rmonlar barpo etish (ga)",
            "Террасное лесоразведение (га)",
            "1.1.8"
        )
        create_column(forest_area_statement, forest_land_6, "Reja", "План", "1.1.8.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)

        create_column(forest_area_statement, forest_land_6, "Amalda", "Факт", "1.1.8.2")
        create_column(forest_area_statement, forest_land_6, "%", "%", "1.1.8.3")
        create_column(forest_area_statement, forest_land_6, "(+,-)", "(+,-)", "1.1.8.4")

        teras_column = create_column(
            forest_area_statement,
            information_forest_title,
            "100 gektar maydonda 30 ming dona brussonetiya daraxtini yetishtirish (ga)",
            "Выращивание 30 тыс. штук бруссонетии на площади 100 га (га)",
            "1.1.9"
        )
        land_in = create_column(
            forest_area_statement,
            teras_column,
            "Maydon (ga)",
            "Площадь (га)",
            "1.1.9.1"
        )
        create_column(forest_area_statement, land_in, "Reja", "План", "1.1.9.1.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)

        create_column(forest_area_statement, land_in, "Amalda", "Факт", "1.1.9.1.2")
        create_column(forest_area_statement, land_in, "%", "%", "1.1.9.1.3")
        create_column(forest_area_statement, land_in, "(+,-)", "(+,-)", "1.1.9.1.4")

        plant_in = create_column(
            forest_area_statement,
            teras_column,
            "Ko‘chatlar soni (dona)",
            "Количество саженцев (шт.)",
            "1.1.9.2"
        )
        create_column(forest_area_statement, plant_in, "Reja", "План", "1.1.9.2.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)

        create_column(forest_area_statement, plant_in, "Amalda", "Факт", "1.1.9.2.2")
        create_column(forest_area_statement, plant_in, "%", "%", "1.1.9.2.3")
        create_column(forest_area_statement, plant_in, "(+,-)", "(+,-)", "1.1.9.2.4")

        tree_column = create_column(
            forest_area_statement,
            information_forest_title,
            "Daraxt va butalarning urug‘larini jamg‘arish (tn)",
            "Сбор семян деревьев и кустарников (тн)",
            "1.1.10"
        )
        create_column(forest_area_statement, tree_column, "Reja", "План", "1.1.10.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)

        create_column(forest_area_statement, tree_column, "Amalda", "Факт", "1.1.10.2")
        create_column(forest_area_statement, tree_column, "%", "%", "1.1.10.3")
        create_column(forest_area_statement, tree_column, "(+,-)", "(+,-)", "1.1.10.4")

        sprout_column = create_column(
            forest_area_statement,
            information_forest_title,
            "Niholxona va ko‘chatxonalar tashkil etish gektar (ga)",
            "Создание питомников и саженцев гектар (га)",
            "1.1.11"
        )
        create_column(forest_area_statement, sprout_column, "Reja", "План", "1.1.11.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, sprout_column, "Amalda", "Факт", "1.1.11.2")
        create_column(forest_area_statement, sprout_column, "%", "%", "1.1.11.3")
        create_column(forest_area_statement, sprout_column, "(+,-)", "(+,-)", "1.1.11.4")

        plant_column = create_column(
            forest_area_statement,
            information_forest_title,
            "Ko‘chat va nihollar yetishtirish (ming. dona)",
            "Выращивание саженцев и рассады (тыс. шт.)",
            "1.1.12"
        )
        create_column(forest_area_statement, plant_column, "Reja", "План", "1.1.12.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, plant_column, "Amalda", "Факт", "1.1.12.2")
        create_column(forest_area_statement, plant_column, "%", "%", "1.1.12.3")
        create_column(forest_area_statement, plant_column, "(+,-)", "(+,-)", "1.1.12.4")

        including_column = create_column(
            forest_area_statement,
            information_forest_title,
            "Jumladan, tut ko‘chatlari yetishtirish. (ming. dona)",
            "В частности, выращивание саженцев шелковицы. (тыс. шт.)",
            "1.1.13"
        )
        create_column(forest_area_statement, including_column, "Reja", "План", "1.1.13.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, including_column, "Amalda", "Факт", "1.1.13.2")
        create_column(forest_area_statement, including_column, "%", "%", "1.1.13.3")
        create_column(forest_area_statement, including_column, "(+,-)", "(+,-)", "1.1.13.4")

        street_column = create_column(
            forest_area_statement,
            information_forest_title,
            "1024 ta mahallalarga 1 mln tup mevali va manzarali daraxt ko‘chatlarini yetkazib berish (tup)",
            "Поставка 1 млн саженцев фруктовых и декоративных деревьев в 1024 махалли (группа)",
            "1.1.14"
        )
        create_column(forest_area_statement, street_column, "Reja", "План", "1.1.14.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, street_column, "Amalda", "Факт", "1.1.14.2")
        create_column(forest_area_statement, street_column, "%", "%", "1.1.14.3")
        create_column(forest_area_statement, street_column, "(+,-)", "(+,-)", "1.1.14.4")

        health_column = create_column(
            forest_area_statement,
            information_forest_title,
            "Sog‘liqni saqlash muasssasalariga mevali va manzarali daraxt ko‘chatlarini yetkazib berish (tup)",
            "Поставка саженцев фруктовых и декоративных деревьев учреждениям здравоохранения (группа)",
            "1.1.15"
        )
        create_column(forest_area_statement, health_column, "Reja", "План", "1.1.15.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, health_column, "Amalda", "Факт", "1.1.15.2")
        create_column(forest_area_statement, health_column, "%", "%", "1.1.15.3")
        create_column(forest_area_statement, health_column, "(+,-)", "(+,-)", "1.1.15.4")

        people_column = create_column(
            forest_area_statement,
            information_forest_title,
            "Xalq ta’limi muassasalariga mevali va manzarali daraxt ko‘chatlarini yetkazib berish (tup)",
            "Поставка саженцев фруктовых и декоративных деревьев учреждениям народного образования (группа)",
            "1.1.16"
        )
        create_column(forest_area_statement, people_column, "Reja", "План", "1.1.16.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, people_column, "Amalda", "Факт", "1.1.16.2")
        create_column(forest_area_statement, people_column, "%", "%", "1.1.16.3")
        create_column(forest_area_statement, people_column, "(+,-)", "(+,-)", "1.1.16.4")

        medical_column = create_column(
            forest_area_statement,
            information_forest_title,
            "Dorivor o‘simliklar plantatsiyalarini barpo etish (ga)",
            "Создание плантаций лекарственных растений (га)",
            "1.1.17"
        )
        create_column(forest_area_statement, medical_column, "Reja", "План", "1.1.17.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, medical_column, "Amalda", "Факт", "1.1.17.2")
        create_column(forest_area_statement, medical_column, "%", "%", "1.1.17.3")
        create_column(forest_area_statement, medical_column, "(+,-)", "(+,-)", "1.1.17.4")

        medical_column_2 = create_column(
            forest_area_statement,
            information_forest_title,
            "Dorivor o‘simliklar xomashyosini tayyorlash (tn)",
            "Заготовка лекарственного растительного сырья (тн)",
            "1.1.18"
        )
        create_column(forest_area_statement, medical_column_2, "Reja", "План", "1.1.18.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, medical_column_2, "Amalda", "Факт", "1.1.18.2")
        create_column(forest_area_statement, medical_column_2, "%", "%", "1.1.18.3")
        create_column(forest_area_statement, medical_column_2, "(+,-)", "(+,-)", "1.1.18.4")

        private_column = create_column(
            forest_area_statement,
            information_forest_title,
            "Xususiy sektor subyektlari bilan birgalikda asalarichilikni rivojlantirish (ming oila)",
            "Развитие пчеловодства совместно с субъектами частного сектора (тыс. семей)",
            "1.1.19"
        )
        create_column(forest_area_statement, private_column, "Reja", "План", "1.1.19.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, private_column, "Amalda", "Факт", "1.1.19.2")
        create_column(forest_area_statement, private_column, "%", "%", "1.1.19.3")
        create_column(forest_area_statement, private_column, "(+,-)", "(+,-)", "1.1.19.4")

        village_column = create_column(
            forest_area_statement,
            information_forest_title,
            "Qishloq xo‘jalik mahsulotlari yetishtirish (tn)",
            "Производство сельскохозяйственной продукции (тн)",
            "1.1.20"
        )
        create_column(forest_area_statement, village_column, "Reja", "План", "1.1.20.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, village_column, "Amalda", "Факт", "1.1.20.2")
        create_column(forest_area_statement, village_column, "%", "%", "1.1.20.3")
        create_column(forest_area_statement, village_column, "(+,-)", "(+,-)", "1.1.20.4")

        private_column_2 = create_column(
            forest_area_statement,
            information_forest_title,
            "Xususiy sektor subyektlari bilan birgalikda mayda shoxli chorvachilikni rivojlantirish",
            "Развитие мелкого рогатого скота совместно с субъектами частного сектора",
            "1.1.21"
        )
        create_column(forest_area_statement, private_column_2, "Reja", "План", "1.1.21.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, private_column_2, "Amalda", "Факт", "1.1.21.2")
        create_column(forest_area_statement, private_column_2, "%", "%", "1.1.21.3")
        create_column(forest_area_statement, private_column_2, "(+,-)", "(+,-)", "1.1.21.4")

        private_column_3 = create_column(
            forest_area_statement,
            information_forest_title,
            "Xususiy sektor subyektlari bilan birgalikda parrandachilikni rivojlantirish",
            "Развитие птицеводства совместно с субъектами частного сектора",
            "1.1.22"
        )
        create_column(forest_area_statement, private_column_3, "Reja", "План", "1.1.22.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, private_column_3, "Amalda", "Факт", "1.1.22.2")
        create_column(forest_area_statement, private_column_3, "%", "%", "1.1.22.3")
        create_column(forest_area_statement, private_column_3, "(+,-)", "(+,-)", "1.1.22.4")

        enterprise_column = create_column(
            forest_area_statement,
            information_forest_title,
            "Korxonalar daromadlari (mlrd so‘m)",
            "Доходы предприятий (млрд сум)",
            "1.1.23"
        )
        create_column(forest_area_statement, enterprise_column, "Reja", "План", "1.1.23.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, enterprise_column, "Amalda", "Факт", "1.1.23.2")
        create_column(forest_area_statement, enterprise_column, "%", "%", "1.1.23.3")
        create_column(forest_area_statement, enterprise_column, "(+,-)", "(+,-)", "1.1.23.4")

        holophyte_column = create_column(
            forest_area_statement,
            information_forest_title,
            "Galofit bog‘lar barpo etish (ga)",
            "Создание галофитных садо (га)",
            "1.1.24"
        )
        create_column(forest_area_statement, holophyte_column, "Reja", "План", "1.1.24.1",
                      status_plan=StatementColumn.PlanStatus.YILLIK)
        create_column(forest_area_statement, holophyte_column, "Amalda", "Факт", "1.1.24.2")
        create_column(forest_area_statement, holophyte_column, "%", "%", "1.1.24.3")
        create_column(forest_area_statement, holophyte_column, "(+,-)", "(+,-)", "1.1.24.4")

        return self.stdout.write(self.style.SUCCESS("✅ Axborot-tahlil, ijro intizomi created!!!"))