from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    help = "Создание заявления об учреждении леса"

    def handle(self, *args, **options):

        first_statement = Statement.objects.create(
            parent=None,
            name_uz="O'rmon barpo qilish",
            name_ru="Создание леса",
            period=PeriodChoices.YILLIK
        )
        first_of_second_statement = Statement.objects.create(
            parent=first_statement,
            name_uz="Yopiq ildiz yirik hajmli",
            name_ru="Закрытый корень крупногабаритный",
            period=PeriodChoices.YILLIK
        )

        app_column = StatementColumn.objects.create(
            statement=first_of_second_statement,
            parent=None,
            title_uz="1-ilova",
            title_ru="Приложение 1",
            ordering="1"
        )

        title_column = StatementColumn.objects.create(
            statement=first_of_second_statement,
            parent=app_column,
            title_uz=(
                "O'rmon xo'jaligi agentligi tizimidagi o'rmon xo'jaliklari tomonidan "
                "2025 yildan yirik hajmli yopiq ko'chatlarni yetishtirish to'g'risida "
                "tezkor ma'lumot."
            ),
            title_ru=(
                "Срочная информация о выращивании крупногабаритных закрытых саженцев "
                "лесничествами в системе Агентства лесного хозяйства с 2025 года."
            ),
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=first_of_second_statement,
            parent=title_column,
            title_uz="Tashkilot nomi",
            title_ru="Названия регионов",
            ordering="1.1.1",
            is_organization=True
        )

        rows = [
            ("Yirik hajmli yopiq ildizli ko'chatlar yetishtirish miqdori",
             "Количество выращивания крупногабаритных саженцев с закрытым корнем", True, "YILLIK_TOTAL"),
            ("Tyanshan qoraqarag'ay", "Тяньшанский черный карагач", True, "YILLIK"),
            ("Tyanshan qarag'ayi", "Тяньшанский карагач", True, "YILLIK"),
            ("Virdjiniya archa", "Верджинская арча", True, "YILLIK"),
            ("Sharq tuya", "Восточная туя", True, "YILLIK"),
            ("Eldor qarag'ay", "Елдорский карагач", True, "YILLIK"),
            ("Qrim qarag'ayi", "Крымский карагач", True, "YILLIK"),
            ("Tuya sharq", "Туя восточная", True, "YILLIK"),
            ("Kiparis", "Кипарис", True, "YILLIK"),
            ("Qayrag'och", "Кайрагач", True, "YILLIK"),
            ("Shumtol", "Шумтол", True, "YILLIK"),
            ("Zarang", "Заранг", True, "YILLIK"),
            ("Sadaqayrag'och", "Садакайраггач", True, "YILLIK"),
            ("Yapon saforasi", "Японский кипарис", True, "YILLIK"),
            ("Akatsiya", "Акация", True, "YILLIK"),
            ("Ipak akatsiya", "Шелковая акация", True, "YILLIK"),
            ("Aylant", "Айлант", True, "YILLIK"),
            ("Katalpa", "Катальпа", True, "YILLIK"),
            ("Pavloniya", "Павлония", True, "YILLIK"),
            ("Chinar", "Тополь", True, "YILLIK"),
            ("Kashtan", "Каштан", True, "YILLIK"),
            ("Pisardi", "Писарди", True, "YILLIK"),
            ("Bag'rik", "Багрянник", True, "YILLIK"),
            ("Qora tut", "Шелковица черная", True, "YILLIK"),
            ("Yapon tut", "Японская шелковица", True, "YILLIK"),
            ("Eman", "Еман", True, "YILLIK"),
            ("Oqqayin", "Белая акация", True, "YILLIK"),
            ("Boshqa turlar", "Другие виды", True, "YILLIK"),
            ("Atirgul", "Роза", True, "YILLIK")
        ]

        for index, (title_uz, title_ru, has_children, plan_status) in enumerate(rows, start=2):
            parent_ordering = f"1.1.{index}"
            parent = StatementColumn.objects.create(
                statement=first_of_second_statement,
                parent=title_column,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=parent_ordering
            )

            if index == 2:
                children = ["Reja", "Amalda", "%"]
                for i, child in enumerate(children, start=1):
                    status_plan = None
                    if child == "Reja":
                        status_plan = StatementColumn.PlanStatus.YILLIK_TOTAL
                    StatementColumn.objects.create(
                        statement=first_of_second_statement,
                        parent=parent,
                        title_uz=child,
                        title_ru={"Reja": "План", "Amalda": "Факт", "%": "%"}[child],
                        ordering=f"{parent_ordering}.{i}",
                        status_plan=status_plan
                    )

            else:
                for i, child in enumerate(["Reja", "Amalda"], start=1):
                    status_plan = None
                    if child == "Reja":
                        status_plan = StatementColumn.PlanStatus.YILLIK
                    StatementColumn.objects.create(
                        statement=first_of_second_statement,
                        parent=parent,
                        title_uz=child,
                        title_ru={"Reja": "План", "Amalda": "Факт"}[child],
                        ordering=f"{parent_ordering}.{i}",
                        status_plan=status_plan
                    )

        # ================================================================ Закрытый корень крупногабаритный

        # =========================== 2-Ilova =============================
        second_statement_of_forest = Statement.objects.create(
            parent=first_statement,
            name_uz="O'rmon barpo qilish bo'limi",
            name_ru="Отдел создания леса",
            period=PeriodChoices.YILLIK
        )

        second_app_column = StatementColumn.objects.create(
            statement=second_statement_of_forest,
            parent=None,
            title_uz="2-ilova",
            title_ru="Приложение 2",
            ordering="1"
        )

        second_ilova_title = StatementColumn.objects.create(
            statement=second_statement_of_forest,
            parent=second_app_column,
            title_uz="O'rmon xo'jaliklari tomonidan joriy yilda o'rmon barpo etilishi to'g'risida ma'lumot",
            title_ru="Информация о создании лесов лесничествами в текущем году",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=second_statement_of_forest,
            parent=second_ilova_title,
            title_uz="Tashkilot nomi",
            title_ru="Названия лесничеств",
            ordering="1.1.1",
            is_organization=True
        )

        rows = [
            ("Jami", "Итого", True),
            ("Cho'l", "Пустыня", True),
            ("Jami yong'oq mevalar", "Итого ореховые плоды", True),
            ("Shundan", "Из них", False),
            ("Jami tez o'suvchilar", "Итого быстрорастущие", True),
            ("Shundan", "Из них", False),
            ("Tabiiy tiklanishga ko'maklashish va boshqa daraxt turlaridan ekish",
             "Помощь в естественном восстановлении и посадка других видов деревьев", False)
        ]

        ordering_base = "1.1"

        for i, (title_uz, title_ru, has_subcolumns) in enumerate(rows, start=2):
            parent_col = StatementColumn.objects.create(
                statement=second_statement_of_forest,
                parent=second_ilova_title,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=f"{ordering_base}.{i}"
            )

            if title_uz == "Shundan":
                if i == 5:
                    children = ["Yong'oq", "Pista", "Bodom"]
                    children_ru = ["Орех", "Писташка", "Миндаль"]
                else:
                    children = ["Terak", "Pavloniya", "Qayrag'och", "Shumtol", "Chinar", "Akatsiya", "Boshqa turlar"]
                    children_ru = ["Тополь", "Павлония", "Кайрагач", "Шумтол", "Тополь", "Акация", "Другие виды"]
                for j, (child_uz, child_ru) in enumerate(zip(children, children_ru), start=1):
                    StatementColumn.objects.create(
                        statement=second_statement_of_forest,
                        parent=parent_col,
                        title_uz=child_uz,
                        title_ru=child_ru,
                        ordering=f"{ordering_base}.{i}.{j}"
                    )
            elif has_subcolumns:
                for j, sub in enumerate(["Reja", "Amalda", "Foiz"], start=1):
                    status_plan = None
                    if sub == "Reja":
                        if title_uz == "Jami":
                            status_plan = StatementColumn.PlanStatus.YILLIK_TOTAL
                        else:
                            status_plan = StatementColumn.PlanStatus.YILLIK

                    StatementColumn.objects.create(
                        statement=second_statement_of_forest,
                        parent=parent_col,
                        title_uz=sub,
                        title_ru={"Reja": "План", "Amalda": "Факт", "Foiz": "Процент"}[sub],
                        ordering=f"{ordering_base}.{i}.{j}",
                        status_plan=status_plan
                    )

        # =========================== 3-Ilova =============================
        third_statement = Statement.objects.create(
            parent=first_statement,
            name_uz="Urug' harakati",
            name_ru="Движение семян",
            period=PeriodChoices.YILLIK
        )

        third_app_column = StatementColumn.objects.create(
            statement=third_statement,
            title_uz="3-ilova",
            title_ru="Приложение 3",
            ordering="1"
        )

        third_ilova_title = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_app_column,
            title_uz="O'rmon xo'jaligida 2025 yilda tayyorlangan o'rmon daraxt va buta urug'larining harakati to'g'risida",
            title_ru="О движении семян лесных деревьев и кустарников, подготовленных в лесном хозяйстве в 2025 году",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title_uz="Tashkilot nomi",
            title_ru="Название организации",
            ordering="1.1.1",
            is_organization=True
        )

        parent = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title_uz="Urug' jamg'arish miqdori",
            title_ru="Объем сбора семян",
            ordering="1.1.2"
        )
        for i, title in enumerate(["Reja", "Amalda", "Foiz"], start=1):
            StatementColumn.objects.create(
                statement=third_statement,
                parent=parent,
                title_uz=title,
                title_ru={"Reja": "План", "Amalda": "Факт", "Foiz": "Процент"}[title],
                ordering=f"1.1.2.{i}",
                status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL if title == "Reja" else None
            )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title_uz="Yil boshiga qolgan qoldiq",
            title_ru="Остаток на начало года",
            ordering="1.1.3"
        )

        hisobot = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title_uz="Hisobot davrida tayyorlandi va sotib olindi",
            title_ru="Подготовлено и приобретено в отчетный период",
            ordering="1.1.4"
        )

        child1 = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot,
            title_uz="Xo'jalik tomonidan tayyorlandi",
            title_ru="Подготовлено хозяйством",
            ordering="1.1.4.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=child1,
            title_uz="Jami",
            title_ru="Итого",
            ordering="1.1.4.1.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=child1,
            title_uz="Sh.J urug'lik uchastkadan",
            title_ru="Из семенных участков Ш.Ж",
            ordering="1.1.4.1.2"
        )

        child2 = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot,
            title_uz="Boshqa tashkilotdan sotib olindi",
            title_ru="Приобретено у других организаций",
            ordering="1.1.4.2"
        )
        for i, title in enumerate(["Miqdori", "Sarflangan summa"], start=1):
            StatementColumn.objects.create(
                statement=third_statement,
                parent=child2,
                title_uz=title,
                title_ru={"Miqdori": "Количество", "Sarflangan summa": "Сумма затрат"}[title],
                ordering=f"1.1.4.2.{i}"
            )

        sarflandi = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title_uz="Hisobot davrida sarflandi",
            title_ru="Израсходовано в отчетный период",
            ordering="1.1.5"
        )

        subtitles = [
            ("Ko'chatzorlar barpo etish uchun", ["Miqdori (kg)", "Ish hajmi (kg)"], "Для создания питомников",
             ["Количество (кг)", "Объем работ (кг)"]),
            ("O'rmonzorlar barpo etish uchun", ["Miqdori (kg)", "Ish hajmi (kg)"], "Для создания лесных насаждений",
             ["Количество (кг)", "Объем работ (кг)"]),
            ("O'rmonlarni yo'qotilganini tiklash uchun", ["Miqdori (kg)", "Ish hajmi (kg)"],
             "Для восполнения потерь лесов", ["Количество (кг)", "Объем работ (кг)"]),
            ("Boshqa tashkilotlarga berildi", ["kg"], "Передано другим организациям", ["кг"]),
            ("Hisobdan chiqarildi", ["kg"], "Списано", ["кг"])
        ]

        for i, (title_uz, children_uz, title_ru, children_ru) in enumerate(subtitles, start=1):
            parent = StatementColumn.objects.create(
                statement=third_statement,
                parent=sarflandi,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=f"1.1.5.{i}"
            )
            for j, (child_uz, child_ru) in enumerate(zip(children_uz, children_ru), start=1):
                StatementColumn.objects.create(
                    statement=third_statement,
                    parent=parent,
                    title_uz=child_uz,
                    title_ru=child_ru,
                    ordering=f"1.1.5.{i}.{j}"
                )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title_uz="Hisobot oxiriga qolgan qoldiq (kg)",
            title_ru="Остаток на конец отчетного периода (кг)",
            ordering="1.1.6"
        )

        # ============================ YAKUNIY ============================
        self.stdout.write(
            self.style.SUCCESS("✅ 'Yopiq ildiz yirik hajmli' Statement va Columns muvaffaqiyatli yaratildi."))
        self.stdout.write(
            self.style.SUCCESS("✅ 'O'rmon barpo qilish bo'limi' Statement va Columns muvaffaqiyatli yaratildi."))
        self.stdout.write(self.style.SUCCESS("✅ 'Urug' harakati' Statement va Columns muvaffaqiyatli yaratildi."))