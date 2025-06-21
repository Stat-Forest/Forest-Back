from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    help = "Create Statement Forest Establishment"

    def handle(self, *args, **options):

        first_statement = Statement.objects.create(
            parent=None,
            name="O`rmon barpo qilish"
        )
        first_of_second_statement = Statement.objects.create(
            parent=first_statement,
            name="Yopiq ildiz yirik hajmli",
            period=PeriodChoices.YILLIK
        )

        app_column = StatementColumn.objects.create(
            statement=first_of_second_statement,
            parent=None,
            title="1-ilova",
            ordering="1"
        )

        title_column = StatementColumn.objects.create(
            statement=first_of_second_statement,
            parent=app_column,
            title=(
                "O`rmon xo`jaligi agentligi tizimidagi o`rmon xo`jaliklari tomonidan "
                "2025 yildan yirik hajmli yopiq ko`chatlarini yetishtirish to`g`risida "
                "tezkor ma`lumot."
            ),
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=first_of_second_statement,
            parent=title_column,
            title="Xududlar nomi",
            ordering="1.1.1",
            is_organization=True
        )

        rows = [
            ("Yirik hajmli yopiq ildizli ko`chatlar yetishtirish miqdori", True, "YILLIK_TOTAL"),
            ("Tyanshan qoraqarag`ay", True, "YILLIK"),
            ("Tyanshan qarag`ayi", True, "YILLIK"),
            ("Vergin archa", True, "YILLIK"),
            ("Sharq tuya", True, "YILLIK"),
            ("Eldor qarag`ay", True, "YILLIK"),
            ("Krim qarag`ayi", True, "YILLIK"),
            ("Tuya sharq", True, "YILLIK"),
            ("Kiparis", True, "YILLIK"),
            ("Qayrag`och", True, "YILLIK"),
            ("Shumtol", True, "YILLIK"),
            ("Zarang", True, "YILLIK"),
            ("Sadaqayrog`och", True, "YILLIK"),
            ("Yapon saforasi", True, "YILLIK"),
            ("Akatsiya", True, "YILLIK"),
            ("Ipak Akatsiya", True, "YILLIK"),
            ("Aylant", True, "YILLIK"),
            ("Katalpa", True, "YILLIK"),
            ("Pavloniya", True, "YILLIK"),
            ("Chinor", True, "YILLIK"),
            ("Kashtan", True, "YILLIK"),
            ("Pisardi", True, "YILLIK"),
            ("Bag`ryannik", True, "YILLIK"),
            ("Chappa tut", True, "YILLIK"),
            ("Yapon tut", True, "YILLIK"),
            ("Eman", True, "YILLIK"),
            ("Oqqayni", True, "YILLIK"),
            ("Boshqa turlar", True, "YILLIK"),
            ("Atirgul", True, "YILLIK"),
        ]

        for index, (title, has_children, plan_status) in enumerate(rows, start=2):
            parent_ordering = f"1.1.{index}"
            parent = StatementColumn.objects.create(
                statement=first_of_second_statement,
                parent=title_column,
                title=title,
                ordering=parent_ordering
            )
            for i, child in enumerate(["Reja", "Amalda"], start=1):
                status_plan = None
                if child == "Reja":
                    status_plan = StatementColumn.PlanStatus[plan_status]

                StatementColumn.objects.create(
                    statement=first_of_second_statement,
                    parent=parent,
                    title=child,
                    ordering=f"{parent_ordering}.{i}",
                    status_plan=status_plan
                )

        # ================================================================ Yopiq ildiz yirik hajmli

        second_statement_of_forest = Statement.objects.create(
            parent=first_statement,
            name="O`rmon barpo qilish bo`limi",
            period=PeriodChoices.YILLIK
        )

        # 2-ilova sarlavhasi (StatementColumn)
        second_app_column = StatementColumn.objects.create(
            statement=second_statement_of_forest,
            parent=None,
            title="2-ilova",
            ordering="1"
        )

        second_ilova_title = StatementColumn.objects.create(
            statement=second_statement_of_forest,
            parent=second_app_column,
            title="O`rmon xo`jaliklari tomonidan joriy yilda o`rmon barpo etilishi to`g`risida ma`lumot",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=second_statement_of_forest,
            parent=second_ilova_title,
            title="O`rmon xo`jaliklar nomi",
            ordering="1.1.1",
            is_organization=True
        )

        rows = [
            ("Jami", True),
            ("Cho‘l", True),
            ("Jami Yong‘oq Mevalar", True),
            ("Shundan", False),  # Yong‘oq, Pista, Bodom
            ("Jami tez o‘suvchilar", True),
            ("Shundan", False),  # Terak, Pavloniya...
            ("Tabiiy tiklanishga ko‘maklashish va boshqa daraxt turlaridan ekish", False),
        ]

        ordering_base = "1.1"

        for i, (title, has_subcolumns) in enumerate(rows, start=2):
            parent_col = StatementColumn.objects.create(
                statement=second_statement_of_forest,
                parent=second_ilova_title,
                title=title,
                ordering=f"{ordering_base}.{i}"
            )

            if title == "Shundan":
                if i == 5:  # Yong‘oq mevalar
                    children = ["Yong‘oq", "Pista", "Bodom"]
                else:  # Daraxt turlari
                    children = [
                        "Terak", "Pavloniya", "Qayrog‘och", "Shumtol",
                        "Chinor", "Akatsiya", "Boshqa turlar"
                    ]
                for j, child in enumerate(children, start=1):
                    StatementColumn.objects.create(
                        statement=second_statement_of_forest,
                        parent=parent_col,
                        title=child,
                        ordering=f"{ordering_base}.{i}.{j}"
                    )
            elif has_subcolumns:
                for j, sub in enumerate(["Reja", "Amalda", "Foiz"], start=1):
                    status_plan = None
                    if sub == "Reja":
                        if title == "Jami":
                            status_plan = StatementColumn.PlanStatus.YILLIK_TOTAL
                        else:
                            status_plan = StatementColumn.PlanStatus.YILLIK

                    StatementColumn.objects.create(
                        statement=second_statement_of_forest,
                        parent=parent_col,
                        title=sub,
                        ordering=f"{ordering_base}.{i}.{j}",
                        status_plan=status_plan
                    )

        # ================================================================ O`rmon barpo qilish

        third_statement = Statement.objects.create(
            parent=first_statement,
            name="Urug` Xarakati",
            period=PeriodChoices.YILLIK
        )

        third_app_column = StatementColumn.objects.create(
            statement=third_statement,
            title="3-ilova",
            ordering="1"
        )

        third_ilova_title = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_app_column,
            title="O`rmon xo`jaligida 2025 yilda tayyorlangan o`rmon daraxt va buta urug`larning xarakati to`g`risida",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title="Daraxt va buta urug`lari turlari",
            ordering="1.1.1"
        )

        parent = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title="Urug` jamg`arish miqdori",
            ordering="1.1.2"
        )
        for i, title in enumerate(["Reja", "Amalda", "Foiz"], start=1):

            StatementColumn.objects.create(
                statement=third_statement,
                parent=parent,
                title=title,
                ordering=f"1.1.2.{i}",
                status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL if title == "Reja" else None
            )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title="Yil boshiga qoldiq",
            ordering="1.1.3"
        )

        hisobot = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title="Hisobot davrida tayyorlandi va sotib olindi",
            ordering="1.1.4"
        )
        child1 = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot,
            title="Xo`jalik tomonidan tayyorlandi",
            ordering="1.1.4.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=child1,
            title="Jami",
            ordering="1.1.4.1.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=child1,
            title="Sh.J urug`lik uchaskadan",
            ordering="1.1.4.1.2"
        )

        child2 = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot,
            title="Boshqa tashkilotdan sotib olindi",
            ordering="1.1.4.2"
        )
        for i, title in enumerate(["Miqdori", "Sarflangan summa"], start=1):
            StatementColumn.objects.create(
                statement=third_statement,
                parent=child2,
                title=title,
                ordering=f"1.1.4.2.{i}"
            )

        sarflandi = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title="Hisobot davrida sarflandi",
            ordering="1.1.5"
        )
        subtitles = [
            ("Ko`chatzorlar barpo etish uchun", ["Miqdori (KG)", "Ish hajmi (KG)"]),
            ("O`rmonzorlar barpo etish uchun", ["Miqdori (KG)", "Ish Hajmi (KG)"]),
            ("O`rmonlarni hatosini to`ldirish uchun", ["Miqdori (KG)", "Ish hajmi (KG)"]),
            ("Boshqa tashkilotlarga berildi", ["kg"]),
            ("Hisobdan chiqarildi", ["kg"])
        ]

        for i, (title, children) in enumerate(subtitles, start=1):
            parent = StatementColumn.objects.create(
                statement=third_statement,
                parent=sarflandi,
                title=title,
                ordering=f"1.1.5.{i}"
            )
            for j, child_title in enumerate(children, start=1):
                StatementColumn.objects.create(
                    statement=third_statement,
                    parent=parent,
                    title=child_title,
                    ordering=f"1.1.5.{i}.{j}"
                )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title="Hisobot ohiriga qolgan qoldiq (kg)",
            ordering="1.1.6"
        )

        # ================================================================ Urug` Xarakati

        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Yopiq ildiz yirik hajmli' Statement and Columns."))
        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'O`rmon barpo qilish' Statement and Columns."))
        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Urug` Xarakati' Statement and Columns."))